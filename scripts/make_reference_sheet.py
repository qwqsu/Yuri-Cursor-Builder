#!/usr/bin/env python3
"""Create a labeled contact sheet from 8+ character reference images."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--columns", type=int, default=4)
    ap.add_argument("--tile", type=int, default=320, help="thumbnail side length")
    ap.add_argument("images", nargs="+", type=Path)
    args = ap.parse_args()
    if len(args.images) < 8:
        ap.error(f"at least 8 reference images are required; got {len(args.images)}")
    if args.columns < 1 or args.tile < 64:
        ap.error("columns must be positive and tile must be at least 64")

    cols = args.columns
    rows = (len(args.images) + cols - 1) // cols
    tile, label_h, margin = args.tile, 28, 12
    canvas = Image.new("RGB", (cols * tile, rows * (tile + label_h)), "#f4f1ea")
    draw = ImageDraw.Draw(canvas)
    for i, path in enumerate(args.images):
        if not path.is_file():
            ap.error(f"image does not exist: {path}")
        try:
            image = Image.open(path)
            image.seek(0)
            image = ImageOps.exif_transpose(image).convert("RGBA")
        except Exception as exc:
            ap.error(f"cannot read image {path}: {exc}")
        image.thumbnail((tile - 2 * margin, tile - 2 * margin), Image.Resampling.NEAREST)
        x0, y0 = (i % cols) * tile, (i // cols) * (tile + label_h)
        matte = Image.new("RGBA", image.size, "white")
        matte.alpha_composite(image)
        canvas.paste(matte.convert("RGB"), (x0 + (tile - image.width) // 2, y0 + (tile - image.height) // 2))
        draw.text((x0 + margin, y0 + tile + 4), f"Reference {i + 1}: {path.name[:34]}", fill="#222222")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output)
    print(f"Wrote {len(args.images)} references to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
