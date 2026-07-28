#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".vscode", "node_modules"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

MAX_WIDTH = int(os.environ.get("IMAGE_MAX_WIDTH", "1600"))
MAX_HEIGHT = int(os.environ.get("IMAGE_MAX_HEIGHT", "1200"))
QUALITY = int(os.environ.get("IMAGE_QUALITY", "85"))
OUTPUT_FORMAT = os.environ.get("IMAGE_OUTPUT_FORMAT", "").strip().upper()
TRIM_MARGIN = int(os.environ.get("IMAGE_TRIM_MARGIN", "10"))


def iter_images(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def normalize_format(path: Path) -> str:
    if OUTPUT_FORMAT:
        return OUTPUT_FORMAT
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "JPEG"
    if suffix == ".png":
        return "PNG"
    if suffix == ".webp":
        return "WEBP"
    if suffix in {".bmp"}:
        return "BMP"
    if suffix in {".tif", ".tiff"}:
        return "TIFF"
    return "JPEG"


def is_blank_pixel(pixel: tuple[int, ...]) -> bool:
    if len(pixel) >= 4 and pixel[3] == 0:
        return True
    if len(pixel) >= 3:
        r, g, b = pixel[:3]
        return r >= 250 and g >= 250 and b >= 250
    return False


def is_very_blank_strip(img: Image.Image, start: int, end: int, axis: str) -> bool:
    if axis == "horizontal":
        for y in range(start, end):
            row = img.crop((0, y, img.width, y + 1)).getdata()
            if not all(is_blank_pixel(pixel) for pixel in row):
                return False
        return True

    for x in range(start, end):
        column = img.crop((x, 0, x + 1, img.height)).getdata()
        if not all(is_blank_pixel(pixel) for pixel in column):
            return False
    return True


def crop_blank_borders(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    width, height = rgba.size

    top = 0
    bottom = height
    left = 0
    right = width

    while top < height and is_very_blank_strip(rgba, top, top + 1, "horizontal"):
        top += 1

    while bottom > top and is_very_blank_strip(rgba, bottom - 1, bottom, "horizontal"):
        bottom -= 1

    while left < width and is_very_blank_strip(rgba, left, left + 1, "vertical"):
        left += 1

    while right > left and is_very_blank_strip(rgba, right - 1, right, "vertical"):
        right -= 1

    if top <= TRIM_MARGIN:
        top = 0
    else:
        top = max(0, top - TRIM_MARGIN)

    if bottom >= height - TRIM_MARGIN:
        bottom = height
    else:
        bottom = min(height, bottom + TRIM_MARGIN)

    if left <= TRIM_MARGIN:
        left = 0
    else:
        left = max(0, left - TRIM_MARGIN)

    if right >= width - TRIM_MARGIN:
        right = width
    else:
        right = min(width, right + TRIM_MARGIN)

    if left == 0 and top == 0 and right == width and bottom == height:
        return img

    return rgba.crop((left, top, right, bottom))


def process_image(path: Path) -> None:
    try:
        with Image.open(path) as img:
            img.load()
            original = img.copy()
            processed = img

            if img.mode in {"RGBA", "LA", "P"}:
                processed = crop_blank_borders(img)

            width, height = processed.size
            resized = processed

            if width > MAX_WIDTH or height > MAX_HEIGHT:
                ratio = min(MAX_WIDTH / width, MAX_HEIGHT / height)
                new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
                resized = processed.resize(new_size, Image.Resampling.LANCZOS)

            format_name = normalize_format(path)
            if format_name == "JPEG" and resized.mode in {"RGBA", "LA", "P"}:
                resized = resized.convert("RGB")

            if resized.size == original.size and resized.mode == original.mode and format_name == normalize_format(path):
                return

            tmp_path = path.with_suffix(path.suffix + ".tmp")
            if format_name in {"JPEG", "WEBP"}:
                resized.save(tmp_path, format=format_name, quality=QUALITY, optimize=True)
            elif format_name == "PNG":
                resized.save(tmp_path, format=format_name, optimize=True)
            else:
                resized.save(tmp_path, format=format_name)

            tmp_path.replace(path)
            print(f"Processed: {path}")
    except (UnidentifiedImageError, OSError) as exc:
        print(f"Skipped {path}: {exc}", file=sys.stderr)


def main() -> int:
    if not ROOT.exists():
        print(f"Repository root not found: {ROOT}", file=sys.stderr)
        return 1

    for image_path in iter_images(ROOT):
        process_image(image_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
