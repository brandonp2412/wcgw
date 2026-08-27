import logging
import os
from importlib import metadata
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl

from wcgw.client.modes import KTS
from wcgw.client.tool_prompts import TOOL_PROMPTS

from ...types_ import (
    BashCommand,
    FileWriteOrEdit,
    Initialize,
)
from ..bash_state.bash_state import CONFIG, BashState, get_tmpdir
from ..tools import (
    TOOLS,
    Context,
    get_tool_output,
    parse_tool_by_name,
    which_tool_name,
)

server: Server[Any] = Server("wcgw")

# Log only time stamp
logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
logger = logging.getLogger("wcgw")


class Console:
    def print(self, msg: str, *args: Any, **kwargs: Any) -> None:
        logger.info(msg)

    def log(self, msg: str, *args: Any, **kwargs: Any) -> None:
        logger.info(msg)


@server.list_resources()  # type: ignore
async def handle_list_resources() -> list[types.Resource]:
    return []


@server.read_resource()  # type: ignore
async def handle_read_resource(uri: AnyUrl) -> str:
    raise ValueError("No resources available")


PROMPTS = {
    "KnowledgeTransfer": (
        types.Prompt(
            name="KnowledgeTransfer",
            description="Prompt for invoking ContextSave tool in order to do a comprehensive knowledge transfer of a coding task. Prompts to save detailed error log and instructions.",
        ),
        KTS,
    )
}


@server.list_prompts()  # type: ignore
async def handle_list_prompts() -> list[types.Prompt]:
    return [x[0] for x in PROMPTS.values()]


@server.get_prompt()  # type: ignore
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    assert BASH_STATE
    messages = [
        types.PromptMessage(
            role="user",
            content=types.TextContent(
                type="text", text=PROMPTS[name][1][BASH_STATE.mode]
            ),
        )
    ]
    return types.GetPromptResult(messages=messages)


@server.list_tools()  # type: ignore
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """

    return TOOL_PROMPTS


@server.call_tool()  # type: ignore
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    global BASH_STATE
    if not arguments:
        raise ValueError("Missing arguments")

    tool_type = which_tool_name(name)
    tool_call = parse_tool_by_name(name, arguments)
    state = state_for_tool(tool_call)
    BASH_STATE = state

    try:
        output_or_dones, _ = get_tool_output(
            Context(state, state.console),
            tool_call,
            0.0,
            lambda x, y: ("", 0),
            24000,  # coding_max_tokens
            8000,  # noncoding_max_tokens
        )
        BASH_STATES[state.current_thread_id] = state

    except Exception as e:
        output_or_dones = [f"GOT EXCEPTION while calling tool. Error: {e}"]

    content: list[types.TextContent | types.ImageContent | types.EmbeddedResource] = []
    for output_or_done in output_or_dones:
        if isinstance(output_or_done, str):
            if issubclass(tool_type, Initialize):
                # Prepare the original hardcoded message
                original_message = """
- Additional important note: as soon as you encounter "The user has chosen to disallow the tool call.", immediately stop doing everything and ask user for the reason.

Initialize call done.
    """

                # If custom instructions exist, prepend them to the original message
                if CUSTOM_INSTRUCTIONS:
                    output_or_done += f"\n{CUSTOM_INSTRUCTIONS}\n{original_message}"
                else:
                    output_or_done += original_message

            content.append(types.TextContent(type="text", text=output_or_done))
        else:
            content.append(
                types.ImageContent(
                    type="image",
                    data=output_or_done.data,
                    mimeType=output_or_done.media_type,
                )
            )

    return content


BASH_STATE: BashState | None = None
BASH_STATES: dict[str, BashState] = {}
CUSTOM_INSTRUCTIONS = None


def new_state(thread_id: str | None) -> BashState:
    template = BASH_STATE
    working_dir = (
        template.cwd
        if template is not None
        else os.path.join(get_tmpdir(), "claude_playground")
    )
    use_screen = template.over_screen if template is not None else True
    shell_path = template.shell_path if template is not None else os.environ.get(
        "SHELL", "/bin/bash"
    )
    return BashState(
        Console(),
        working_dir,
        None,
        None,
        None,
        None,
        use_screen,
        None,
        thread_id,
        shell_path,
    )


def tool_thread_id(tool_call: TOOLS) -> str:
    if isinstance(tool_call, BashCommand):
        return tool_call.action_json.thread_id
    if isinstance(tool_call, (Initialize, FileWriteOrEdit)):
        return tool_call.thread_id
    return ""


def restored_state(thread_id: str) -> BashState | None:
    state = new_state(None)
    if state.load_state_from_thread_id(thread_id):
        return state
    state.cleanup()
    return None


def state_for_tool(tool_call: TOOLS) -> BashState:
    if isinstance(tool_call, Initialize) and tool_call.type == "first_call":
        return new_state(None)

    thread_id = tool_thread_id(tool_call)
    if thread_id:
        state = BASH_STATES.get(thread_id)
        if state is not None:
            return state
        state = restored_state(thread_id)
        if state is not None:
            BASH_STATES[thread_id] = state
            return state

    assert BASH_STATE
    return BASH_STATE


async def main(shell_path: str = "") -> None:
    global BASH_STATE, CUSTOM_INSTRUCTIONS
    CONFIG.update(3, 55, 5)
    version = str(metadata.version("wcgw"))

    # Read custom instructions from environment variable
    CUSTOM_INSTRUCTIONS = os.getenv("WCGW_SERVER_INSTRUCTIONS")

    # starting_dir is inside tmp dir
    tmp_dir = get_tmpdir()
    starting_dir = os.path.join(tmp_dir, "claude_playground")

    BASH_STATE = BashState(
        Console(),
        starting_dir,
        None,
        None,
        None,
        None,
        True,
        None,
        None,
        shell_path or None,
    )
    BASH_STATE.console.log("wcgw version: " + version)
    try:
        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="wcgw",
                    server_version=version,
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
                raise_exceptions=False,
            )
    finally:
        states = {
            id(state): state
            for state in [BASH_STATE, *BASH_STATES.values()]
            if state is not None
        }
        for state in states.values():
            try:
                state.cleanup()
            except Exception:
                logger.exception("failed to clean up WCGW shell state")
