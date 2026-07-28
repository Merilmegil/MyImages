#!/usr/bin/env python3
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".vscode"}


def normalize_name(name: str) -> str:
    name = name.strip().replace(" ", "_")
    normalized = unicodedata.normalize("NFKD", name)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^A-Za-z0-9._-]", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.strip("._-")
    return normalized or "file"


def unique_target(path: Path, desired_name: str) -> Path:
    target = path.with_name(desired_name)
    if not target.exists() or target.resolve() == path.resolve():
        return target

    stem, suffix = os.path.splitext(desired_name)
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def rename_path(path: Path) -> Path:
    if path.name in SKIP_DIRS:
        return path

    new_name = normalize_name(path.name)
    if new_name == path.name:
        return path

    target = unique_target(path, new_name)
    if target != path:
        path.rename(target)
        print(f"Renamed: {path} -> {target}")
        return target
    return path


def process_directory(path: Path) -> None:
    if not path.exists():
        return

    for child in sorted(path.iterdir(), key=lambda item: item.name):
        if child.name in SKIP_DIRS:
            continue
        if child.is_dir():
            process_directory(child)
        elif child.is_file() or child.is_symlink():
            rename_path(child)

    rename_path(path)


def main() -> int:
    if not ROOT.exists():
        print(f"Repository root not found: {ROOT}", file=sys.stderr)
        return 1

    process_directory(ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
