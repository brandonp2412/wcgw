import os
import tempfile

from wcgw.types_ import ReadFiles


def test_readfiles_line_number_parsing():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
        tmp_path = tmp.name

    try:
        read_files = ReadFiles(file_paths=[tmp_path], thread_id="test")
        assert read_files.file_paths == [tmp_path]
        assert read_files.start_line_nums == [None]
        assert read_files.end_line_nums == [None]

        read_files = ReadFiles(file_paths=[f"{tmp_path}:2"], thread_id="test")
        assert read_files.file_paths == [tmp_path]
        assert read_files.start_line_nums == [2]
        assert read_files.end_line_nums == [None]

        read_files = ReadFiles(file_paths=[f"{tmp_path}:-3"], thread_id="test")
        assert read_files.file_paths == [tmp_path]
        assert read_files.start_line_nums == [None]
        assert read_files.end_line_nums == [3]

        read_files = ReadFiles(file_paths=[f"{tmp_path}:2-4"], thread_id="test")
        assert read_files.file_paths == [tmp_path]
        assert read_files.start_line_nums == [2]
        assert read_files.end_line_nums == [4]

        read_files = ReadFiles(file_paths=[f"{tmp_path}:5-"], thread_id="test")
        assert read_files.file_paths == [tmp_path]
        assert read_files.start_line_nums == [5]
        assert read_files.end_line_nums == [None]

        read_files = ReadFiles(
            file_paths=[tmp_path, f"{tmp_path}:2-3", f"{tmp_path}:1-"],
            thread_id="test",
        )
        assert read_files.file_paths == [tmp_path, tmp_path, tmp_path]
        assert read_files.start_line_nums == [None, 2, 1]
        assert read_files.end_line_nums == [None, 3, None]

        read_files = ReadFiles(
            file_paths=[f"{tmp_path}:invalid-line"], thread_id="test"
        )
        assert read_files.file_paths == [f"{tmp_path}:invalid-line"]
        assert read_files.start_line_nums == [None]
        assert read_files.end_line_nums == [None]

        filename_with_colon = f"{tmp_path}:colon_in_name"
        read_files = ReadFiles(file_paths=[filename_with_colon], thread_id="test")
        assert read_files.file_paths == [filename_with_colon]
        assert read_files.start_line_nums == [None]
        assert read_files.end_line_nums == [None]

        url_path = "/path/to/http://example.com/file.txt"
        read_files = ReadFiles(file_paths=[url_path], thread_id="test")
        assert read_files.file_paths == [url_path]
        assert read_files.start_line_nums == [None]
        assert read_files.end_line_nums == [None]

        url_path_with_line = "/path/to/http://example.com/file.txt:10-20"
        read_files = ReadFiles(file_paths=[url_path_with_line], thread_id="test")
        assert read_files.file_paths == ["/path/to/http://example.com/file.txt"]
        assert read_files.start_line_nums == [10]
        assert read_files.end_line_nums == [20]

    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    test_readfiles_line_number_parsing()
    print("All tests passed!")
