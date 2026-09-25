import glob
from pathlib import Path


class FileHelper:
    @staticmethod
    def resolve_files(path: str) -> list[str] | None:
        if FileHelper._is_glob_pattern(path):
            return sorted(glob.glob(path, recursive=True))
        if Path(path).is_dir():
            return FileHelper._find_json_files_recursively(path)
        if Path(path).is_file():
            return [path]
        return None

    def _find_json_files_recursively(dir: str) -> list[str]:
        return [str(json_file) for json_file in Path(dir).rglob("*.json")]

    def _is_glob_pattern(path: str) -> bool:
        return any(char in path for char in ("*", "?", "["))
