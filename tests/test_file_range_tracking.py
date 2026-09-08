import os
import tempfile
from typing import Dict, List, Tuple

import pytest

from wcgw.client.bash_state.bash_state import BashState, FileWhitelistData
from wcgw.client.tools import Context, read_file, read_files


class MockConsole:
    def print(self, msg: str, *args, **kwargs) -> None:
        pass

    def log(self, msg: str, *args, **kwargs) -> None:
        pass


@pytest.fixture
def test_file():
    """Create a temporary file with 20 lines of content."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
        for i in range(1, 21):
            f.write(f"Line {i}\n")
        path = f.name

    yield path

    os.unlink(path)


@pytest.fixture
def context():
    """Create a context with BashState for testing."""
    with BashState(
        console=MockConsole(),
        working_dir="",
        bash_command_mode=None,
        file_edit_mode=None,
        write_if_empty_mode=None,
        mode=None,
        use_screen=False,
    ) as bash_state:
        return Context(bash_state=bash_state, console=MockConsole())


def test_read_file_tracks_line_ranges(test_file, context):
    """Test that read_file correctly returns line ranges."""
    _, _, _, path, line_range = read_file(
        test_file, coding_max_tokens=None, noncoding_max_tokens=None, context=context, start_line_num=5, end_line_num=10
    )

    assert line_range == (5, 10)


def test_read_files_tracks_multiple_ranges(test_file, context):
    """Test that read_files correctly collects line ranges for multiple reads."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
        for i in range(1, 31):
            f.write(f"Another line {i}\n")
        second_file = f.name

    try:
        _, file_ranges, _ = read_files(
            file_paths=[test_file, second_file],
            coding_max_tokens=None,
            noncoding_max_tokens=None,
            context=context,
            start_line_nums=[5, 10],
            end_line_nums=[10, 20],
        )

        assert len(file_ranges) == 2
        assert test_file in file_ranges
        assert second_file in file_ranges
        assert file_ranges[test_file] == [(5, 10)]
        assert file_ranges[second_file] == [(10, 20)]
    finally:
        os.unlink(second_file)


def test_whitelist_data_tracking(test_file):
    """Test that FileWhitelistData correctly tracks line ranges."""
    whitelist_data = FileWhitelistData(
        file_hash="abc123", line_ranges_read=[(1, 5), (10, 15)], total_lines=20
    )

    whitelist_data.add_range(7, 9)
    percentage = whitelist_data.get_percentage_read()

    assert percentage == 70.0

    assert not whitelist_data.is_read_enough()

    unread_ranges = whitelist_data.get_unread_ranges()
    assert len(unread_ranges) == 2
    assert (6, 6) in unread_ranges
    assert (16, 20) in unread_ranges

    whitelist_data.add_range(6, 6)
    whitelist_data.add_range(16, 20)

    assert whitelist_data.is_read_enough()
    assert len(whitelist_data.get_unread_ranges()) == 0


def test_bash_state_whitelist_for_overwrite(context, test_file):
    """Test that BashState correctly tracks file whitelist data."""
    file_paths_with_ranges: Dict[str, List[Tuple[int, int]]] = {test_file: [(1, 10)]}
    context.bash_state.add_to_whitelist_for_overwrite(file_paths_with_ranges)

    assert test_file in context.bash_state.whitelist_for_overwrite
    whitelist_data = context.bash_state.whitelist_for_overwrite[test_file]
    assert whitelist_data.line_ranges_read[0] == (1, 10)

    context.bash_state.add_to_whitelist_for_overwrite({test_file: [(15, 20)]})

    whitelist_data = context.bash_state.whitelist_for_overwrite[test_file]
    assert len(whitelist_data.line_ranges_read) == 2
    assert (15, 20) in whitelist_data.line_ranges_read
