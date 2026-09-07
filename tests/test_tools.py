import os
import subprocess
import tempfile
from typing import Generator

import pytest

from wcgw.client.bash_state.bash_state import BashState
from wcgw.client.tools import (
    BashCommand,
    Context,
    ContextSave,
    Initialize,
    ReadFiles,
    ReadImage,
    get_tool_output,
    which_tool_name,
)
from wcgw.types_ import (
    Command,
    Console,
    FileWriteOrEdit,
    SendAscii,
    SendSpecials,
    SendText,
    StatusCheck,
)


class TestConsole(Console):
    def __init__(self):
        self.logs = []
        self.prints = []

    def log(self, msg: str) -> None:
        self.logs.append(msg)

    def print(self, msg: str) -> None:
        self.prints.append(msg)


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Provides a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def context(temp_dir: str) -> Generator[Context, None, None]:
    """Provides a test context with temporary directory and handles cleanup."""
    console = TestConsole()
    bash_state = BashState(
        console=console,
        working_dir=temp_dir,
        bash_command_mode=None,
        file_edit_mode=None,
        write_if_empty_mode=None,
        mode=None,
        use_screen=True,
    )
    ctx = Context(
        bash_state=bash_state,
        console=console,
    )
    yield ctx
    try:
        bash_state.sendintr()  # Send Ctrl-C to any running process
        bash_state.reset_shell()  # Reset shell state
        bash_state.cleanup()  # Cleanup final shell
    except Exception as e:
        print(f"Error during cleanup: {e}")


def test_initialize(context: Context, temp_dir: str) -> None:
    """Test the Initialize tool with various configurations."""
    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )

    outputs, _ = get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert isinstance(outputs[0], str)
    assert temp_dir in outputs[0]
    assert "System:" in outputs[0]

    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="architect",
        thread_id="",
    )

    outputs, _ = get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert isinstance(outputs[0], str)

    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="code_writer",
        allowed_commands=["ls", "pwd", "cat"],
        allowed_globs=["*.py", "*.txt"],
        thread_id="",
    )

    outputs, _ = get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert isinstance(outputs[0], str)

    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    save_args = ContextSave(
        id="test_task_123",
        project_root_path=temp_dir,
        description="Test context",
        relevant_file_globs=["*.txt"],
        thread_id=context.bash_state.current_thread_id,
    )
    get_tool_output(
        context, save_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[test_file],
        task_id_to_resume="test_task_123",
        mode_name="wcgw",
        thread_id="",
    )

    outputs, _ = get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert isinstance(outputs[0], str)
    assert test_file in outputs[0]
    assert "Following is the retrieved" in outputs[0]

    new_test_file = os.path.join(temp_dir, "test2.txt")
    with open(new_test_file, "w") as f:
        f.write("test content 2")

    save_args = ContextSave(
        id="test_task_mode_switch",
        project_root_path=temp_dir,
        description="Test context with mode switch",
        relevant_file_globs=["*.txt"],
        thread_id=context.bash_state.current_thread_id,
    )
    get_tool_output(
        context, save_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[new_test_file],
        task_id_to_resume="test_task_mode_switch",
        mode_name="architect",
        thread_id="",
    )

    outputs, _ = get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert isinstance(outputs[0], str)
    assert new_test_file in outputs[0]
    assert "Following is the retrieved" in outputs[0]
    assert 'running in "architect" mode' in outputs[0].lower()

    init_args = Initialize(
        type="first_call",
        any_workspace_path="",
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )

    outputs, _ = get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert isinstance(outputs[0], str)

    nonexistent_path = os.path.join(temp_dir, "does_not_exist")
    init_args = Initialize(
        type="first_call",
        any_workspace_path=nonexistent_path,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )

    outputs, _ = get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert isinstance(outputs[0], str)
    assert "does_not_exist" in outputs[0]

    file_as_workspace = os.path.join(temp_dir, "workspace.txt")
    with open(file_as_workspace, "w") as f:
        f.write("test content")

    init_args = Initialize(
        type="first_call",
        any_workspace_path=file_as_workspace,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )

    outputs, _ = get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert isinstance(outputs[0], str)
    assert file_as_workspace in outputs[0]


def test_bash_command(context: Context, temp_dir: str) -> None:
    """Test the BashCommand tool."""
    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )
    get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    cmd = BashCommand(
        action_json=StatusCheck(
            status_check=True, thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "No running command to check status of" in outputs[0]

    cmd = BashCommand(
        action_json=Command(
            command="sleep 1",
            wait_for_seconds=0.1,
            thread_id=context.bash_state._current_thread_id,
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "status = still running" in outputs[0]

    status_check = BashCommand(
        action_json=StatusCheck(
            status_check=True, thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, status_check, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "status = process exited" in outputs[0]

    cmd = BashCommand(
        action_json=Command(
            command="echo 'hello world'", thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert isinstance(outputs[0], str)
    assert "hello world" in outputs[0]

    cmd = BashCommand(
        action_json=Command(
            command="echo 'hello \nworld'",
            thread_id=context.bash_state._current_thread_id,
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert isinstance(outputs[0], str)
    assert "hello\nworld" in outputs[0]

    cmd = BashCommand(
        action_json=Command(
            command="echo 'hello'\necho world'",
            thread_id=context.bash_state._current_thread_id,
        )
    )
    with pytest.raises(ValueError, match="Error: Command contains multiple statements"):
        get_tool_output(context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000)


def test_interaction_commands(context: Context, temp_dir: str) -> None:
    """Test the various interaction command types."""
    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )
    get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    cmd = BashCommand(
        action_json=SendText(
            send_text="hello", thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert isinstance(outputs[0], str)

    cmd = BashCommand(
        action_json=SendSpecials(
            send_specials=["Enter"], thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert isinstance(outputs[0], str)
    assert "status = process exited" in outputs[0]

    cmd = BashCommand(
        action_json=SendAscii(
            send_ascii=[3], thread_id=context.bash_state._current_thread_id
        )
    )  # Ctrl-C
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert isinstance(outputs[0], str)
    assert "status = process exited" in outputs[0]

    cmd = BashCommand(
        action_json=Command(
            command="sleep 1",
            wait_for_seconds=0.1,
            thread_id=context.bash_state._current_thread_id,
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "status = still running" in outputs[0]

    cmd = BashCommand(
        action_json=SendSpecials(
            send_specials=["Enter"], thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "status = process exited" in outputs[0]

    cmd = BashCommand(
        action_json=Command(
            command="sleep 1",
            wait_for_seconds=0.1,
            thread_id=context.bash_state._current_thread_id,
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "status = still running" in outputs[0]

    # Send Ctrl-C
    cmd = BashCommand(
        action_json=SendSpecials(
            send_specials=["Ctrl-c"], thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "status = process exited" in outputs[0]


def test_write_and_read_file(context: Context, temp_dir: str) -> None:
    """Test WriteIfEmpty and ReadFiles tools."""
    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )
    get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    test_file = os.path.join(temp_dir, "test.txt")
    write_args = FileWriteOrEdit(
        file_path=test_file,
        percentage_to_change=100,
        text_or_search_replace_blocks="test content\n",
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, write_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert "Success" in outputs[0]

    read_args = ReadFiles(
        file_paths=[test_file], thread_id=context.bash_state.current_thread_id
    )
    outputs, _ = get_tool_output(
        context, read_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert "test content" in outputs[0]

    with open(test_file, "w") as f:
        f.write("modified content\n")

    write_args = FileWriteOrEdit(
        file_path=test_file,
        percentage_to_change=100,
        text_or_search_replace_blocks="new content\n",
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, write_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert "Error: the file has changed since last read." in outputs[0]

    test_file2 = os.path.join(temp_dir, "test2.txt")
    with open(test_file2, "w") as f:
        f.write("existing content\n")
    write_args = FileWriteOrEdit(
        file_path=test_file2,
        percentage_to_change=100,
        text_or_search_replace_blocks="new content\n",
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, write_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "Error: you need to read existing " in outputs[0]

    read_args = ReadFiles(
        file_paths=[test_file2], thread_id=context.bash_state.current_thread_id
    )
    outputs, _ = get_tool_output(
        context, read_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    write_args = FileWriteOrEdit(
        file_path=test_file2,
        percentage_to_change=100,
        text_or_search_replace_blocks="new content after read\n",
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, write_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "Success" in outputs[0]

    read_args = ReadFiles(
        file_paths=[test_file2], thread_id=context.bash_state.current_thread_id
    )
    outputs, _ = get_tool_output(
        context, read_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "new content after read" in outputs[0]


def test_context_save(context: Context, temp_dir: str) -> None:
    """Test the ContextSave tool."""
    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )
    get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    test_file1 = os.path.join(temp_dir, "test1.txt")
    test_file2 = os.path.join(temp_dir, "test2.txt")

    with open(test_file1, "w") as f:
        f.write("test content 1")
    with open(test_file2, "w") as f:
        f.write("test content 2")

    save_args = ContextSave(
        id="test_save",
        project_root_path=temp_dir,
        description="Test save",
        relevant_file_globs=["*.txt"],
        thread_id=context.bash_state.current_thread_id,
    )

    outputs, _ = get_tool_output(
        context, save_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert isinstance(outputs[0], str)
    assert outputs[0].endswith(".txt")


def test_reinitialize(context: Context, temp_dir: str) -> None:
    """Test the tool with various mode changes."""
    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )
    get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    reset_args = Initialize(
        type="user_asked_mode_change",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, reset_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert "Reset successful" in outputs[0]
    assert "mode change" not in outputs[0].lower()

    reset_args = Initialize(
        type="user_asked_mode_change",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="architect",
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, reset_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert "Reset successful with mode change to architect" in outputs[0]

    reset_args = Initialize(
        type="user_asked_mode_change",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="code_writer",
        allowed_commands=[],
        allowed_globs=["*.py"],
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, reset_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert "Reset successful with mode change to code_writer" in outputs[0]
    assert context.bash_state._write_if_empty_mode.allowed_globs == [
        temp_dir + "/" + "*.py"
    ]
    assert context.bash_state.file_edit_mode.allowed_globs == [temp_dir + "/" + "*.py"]

    cmd = BashCommand(
        action_json=Command(
            command="touch test.txt", thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "Error: BashCommand not allowed in current mode" in str(outputs[0])

    reset_args = Initialize(
        type="user_asked_change_workspace",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="shouldnot_proceed",
        mode_name="architect",
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, reset_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert "Warning: task can only be resumed in a new conversation" in outputs[0]
    assert '"architect" mode' in outputs[0]

    reset_args = Initialize(
        type="user_asked_change_workspace",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="architect",
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, reset_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert "architect mode" not in outputs[0]


def _test_init(context: Context, temp_dir: str) -> None:
    """Initialize test environment."""
    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )
    get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    context.bash_state.reset_shell()


def test_file_io(context: Context, temp_dir: str) -> None:
    """Test reading from a file with cat."""
    _test_init(context, temp_dir)

    test_file = os.path.join(temp_dir, "input.txt")
    with open(test_file, "w") as f:
        f.write("hello world")

    cmd = BashCommand(
        action_json=Command(
            command=f"cat {test_file}", thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "hello world" in outputs[0]
    assert "status = process exited" in outputs[0]


def test_command_interrupt(context: Context, temp_dir: str) -> None:
    """Test Ctrl-C interruption."""
    _test_init(context, temp_dir)

    cmd = BashCommand(
        action_json=Command(
            command="sleep 5",
            wait_for_seconds=0.1,
            thread_id=context.bash_state._current_thread_id,
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "status = still running" in outputs[0]

    cmd = BashCommand(
        action_json=SendSpecials(
            send_specials=["Ctrl-c"], thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "status = process exited" in outputs[0]


def test_command_suspend(context: Context, temp_dir: str) -> None:
    """Test Ctrl-Z suspension."""
    _test_init(context, temp_dir)

    cmd = BashCommand(
        action_json=Command(
            command="sleep 5",
            wait_for_seconds=0.1,
            thread_id=context.bash_state._current_thread_id,
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "status = still running" in outputs[0]


def test_text_input(context: Context, temp_dir: str) -> None:
    """Test sending text to a program."""
    _test_init(context, temp_dir)

    cmd = BashCommand(
        action_json=Command(
            command="cat", thread_id=context.bash_state._current_thread_id
        )
    )
    get_tool_output(context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000)

    cmd = BashCommand(
        action_json=SendText(
            send_text="hello", thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "hello" in str(outputs[0])

    cmd = BashCommand(
        action_json=SendSpecials(
            send_specials=["Ctrl-d"], thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "status = process exited" in str(outputs[0])


def test_ascii_input(context: Context, temp_dir: str) -> None:
    """Test sending ASCII codes."""
    _test_init(context, temp_dir)

    cmd = BashCommand(
        action_json=Command(
            command="cat", thread_id=context.bash_state._current_thread_id
        )
    )
    get_tool_output(context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000)

    cmd = BashCommand(
        action_json=SendAscii(
            send_ascii=[65, 66, 67], thread_id=context.bash_state._current_thread_id
        )
    )  # ABC
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "ABC" in str(outputs[0])

    cmd = BashCommand(
        action_json=SendAscii(
            send_ascii=[3], thread_id=context.bash_state._current_thread_id
        )
    )  # Ctrl-C
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert "status = process exited" in str(outputs[0])


def test_read_image(context: Context, temp_dir: str) -> None:
    """Test the ReadImage tool."""
    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )
    get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    test_image = os.path.join(temp_dir, "test.png")
    with open(test_image, "wb") as f:
        # Write a minimal valid PNG file
        f.write(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63640000000600005c0010ef0000000049454e44ae426082"
            )
        )

    read_args = ReadImage(
        file_path=test_image, thread_id=context.bash_state.current_thread_id
    )
    outputs, _ = get_tool_output(
        context, read_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert hasattr(outputs[0], "media_type")
    assert outputs[0].media_type == "image/png"
    assert hasattr(outputs[0], "data")


def test_which_tool_name() -> None:
    """Test the which_tool_name function."""
    assert which_tool_name("BashCommand") == BashCommand
    assert which_tool_name("FileWriteOrEdit") == FileWriteOrEdit
    assert which_tool_name("ReadImage") == ReadImage
    assert which_tool_name("ReadFiles") == ReadFiles
    assert which_tool_name("Initialize") == Initialize
    assert which_tool_name("ContextSave") == ContextSave

    with pytest.raises(ValueError) as exc_info:
        which_tool_name("UnknownTool")
    assert "Unknown tool name: UnknownTool" in str(exc_info.value)


def test_git_recent_files(context: Context, temp_dir: str) -> None:
    """Test git repository recent files feature with 100 files in batches of 20."""
    os.chdir(temp_dir)
    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], check=True)

    all_files = []
    for batch in range(20):
        batch_files = []
        for i in range(5):
            file_num = batch * 5 + i + 1
            file_name = f"file{file_num:03d}.txt"
            batch_files.append(file_name)
            with open(os.path.join(temp_dir, file_name), "w") as f:
                f.write(f"Content for {file_name}")
            subprocess.run(["git", "add", file_name], check=True)

        subprocess.run(["git", "commit", "-m", f"Add batch {batch + 1}"], check=True)
        all_files.extend(batch_files)

    recent_files = all_files[-10:]

    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )

    outputs, _ = get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    assert len(outputs) == 1
    assert isinstance(outputs[0], str)

    repo_structure = outputs[0]
    for file in recent_files:
        assert file in repo_structure


def test_write_empty_file_and_read(context: Context, temp_dir: str) -> None:
    """Test writing an empty file and reading it."""
    _test_init(context, temp_dir)

    test_file = os.path.join(temp_dir, "empty.txt")
    write_args = FileWriteOrEdit(
        file_path=test_file,
        percentage_to_change=100,
        text_or_search_replace_blocks="",
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, write_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "Success" in outputs[0]

    read_args = ReadFiles(
        file_paths=[test_file], thread_id=context.bash_state.current_thread_id
    )
    outputs, _ = get_tool_output(
        context, read_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1


def test_error_cases(context: Context, temp_dir: str) -> None:
    """Test various error cases."""
    init_args = Initialize(
        type="first_call",
        any_workspace_path=temp_dir,
        initial_files_to_read=[],
        task_id_to_resume="",
        mode_name="wcgw",
        thread_id="",
    )
    get_tool_output(
        context, init_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )

    read_args = ReadFiles(
        file_paths=[os.path.join(temp_dir, "nonexistent.txt")],
        thread_id=context.bash_state.current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, read_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "Error" in outputs[0]

    write_args = FileWriteOrEdit(
        file_path=os.path.join(temp_dir, "nonexistent", "test.txt"),
        text_or_search_replace_blocks="test",
        percentage_to_change=100,
        thread_id=context.bash_state._current_thread_id,
    )
    outputs, _ = get_tool_output(
        context, write_args, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "Success" in outputs[0]  # Should succeed as it creates directories

    cmd = BashCommand(
        action_json=Command(
            command="nonexistentcommand", thread_id=context.bash_state._current_thread_id
        )
    )
    outputs, _ = get_tool_output(
        context, cmd, 1.0, lambda x, y: ("", 0.0), 8000, 4000
    )
    assert len(outputs) == 1
    assert "not found" in str(outputs[0]).lower()
