from runner.file_helper import FileHelper


def test_resolve_files_searches_directory_recursively(tmp_path) -> None:
    nested_directory = tmp_path / "nested"
    nested_directory.mkdir()
    first_json = tmp_path / "first.json"
    second_json = nested_directory / "second.json"
    ignored_file = nested_directory / "ignored.txt"
    first_json.write_text("{}", encoding="utf-8")
    second_json.write_text("{}", encoding="utf-8")
    ignored_file.write_text("not json", encoding="utf-8")

    result = FileHelper.resolve_files(str(tmp_path))

    assert set(result) == {str(first_json), str(second_json)}
