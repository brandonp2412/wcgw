import asyncio
import os
import re
import shutil

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def result_text(result) -> str:
    return "\n".join(getattr(item, "text", "") for item in result.content)


@pytest.mark.asyncio
async def test_stdio_transport_keeps_conversation_shells_concurrent(tmp_path) -> None:
    executable = shutil.which("wcgw_mcp")
    assert executable is not None
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["SHELL"] = "/bin/bash"
    env["XDG_STATE_HOME"] = str(tmp_path / "state")

    params = StdioServerParameters(
        command=executable,
        args=["--shell", "/bin/bash"],
        env=env,
        cwd=str(tmp_path),
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            init_args = {
                "type": "first_call",
                "any_workspace_path": "",
                "initial_files_to_read": [],
                "task_id_to_resume": "",
                "mode_name": "wcgw",
                "thread_id": "",
            }
            first_init, second_init = await asyncio.gather(
                session.call_tool("Initialize", init_args),
                session.call_tool("Initialize", init_args),
            )
            first_match = re.search(r"Use thread_id=(\w+)", result_text(first_init))
            second_match = re.search(r"Use thread_id=(\w+)", result_text(second_init))
            assert first_match is not None
            assert second_match is not None
            first_thread = first_match.group(1)
            second_thread = second_match.group(1)
            assert first_thread != second_thread

            # Warm both shells so shell startup time is not part of the concurrency assertion.
            await asyncio.gather(
                session.call_tool(
                    "BashCommand",
                    {
                        "type": "command",
                        "command": "pwd",
                        "thread_id": first_thread,
                        "wait_for_seconds": 0.5,
                    },
                ),
                session.call_tool(
                    "BashCommand",
                    {
                        "type": "command",
                        "command": "pwd",
                        "thread_id": second_thread,
                        "wait_for_seconds": 0.5,
                    },
                ),
            )

            long_call = asyncio.create_task(
                session.call_tool(
                    "BashCommand",
                    {
                        "type": "command",
                        "command": "sleep 1",
                        "thread_id": first_thread,
                        "wait_for_seconds": 2,
                    },
                )
            )
            await asyncio.sleep(0.02)
            short_call = asyncio.create_task(
                session.call_tool(
                    "BashCommand",
                    {
                        "type": "command",
                        "command": "pwd",
                        "thread_id": second_thread,
                        "wait_for_seconds": 0.5,
                    },
                )
            )
            short_result = await asyncio.wait_for(short_call, timeout=2)
            assert "status = process exited" in result_text(short_result)
            assert not long_call.done()

            long_result = await asyncio.wait_for(long_call, timeout=2)
            assert "status = process exited" in result_text(long_result)
