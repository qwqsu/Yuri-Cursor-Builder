#!/usr/bin/env python3
"""Validate CUR/ANI files and installer artifacts in a generated cursor pack."""
from __future__ import annotations

import argparse
import json
import struct
from io import BytesIO
from pathlib import Path

from PIL import Image


REQUIRED = {"Arrow", "Help", "No", "IBeam", "Crosshair", "SizeNS", "SizeWE", "SizeNESW", "SizeNWSE"}


def validate_cur(path: Path) -> list[str]:
    errors: list[str] = []
    data = path.read_bytes()
    if len(data) < 22 or struct.unpack_from("<HHH", data)[:2] != (0, 2):
        return [f"{path.name}: invalid CUR header"]
    count = struct.unpack_from("<H", data, 4)[0]
    if count < 1 or len(data) < 6 + count * 16:
        return [f"{path.name}: invalid image directory"]
    dimensions = []
    for i in range(count):
        width, height, _, _, hx, hy, size, offset = struct.unpack_from("<BBBBHHII", data, 6 + i * 16)
        width = width or 256
        height = height or 256
        dimensions.append((width, height))
        if hx >= width or hy >= height:
            errors.append(f"{path.name}: hotspot ({hx},{hy}) outside {width}×{height}")
        if offset + size > len(data):
            errors.append(f"{path.name}: image payload exceeds file length")
            continue
        try:
            payload = data[offset:offset + size]
            with Image.open(BytesIO(payload)) as im:
                if im.size != (width, height):
                    errors.append(f"{path.name}: directory says {width}×{height}, image is {im.size}")
                if im.convert("RGBA").getchannel("A").getbbox() is None:
                    errors.append(f"{path.name}: image is fully transparent")
        except Exception as exc:
            errors.append(f"{path.name}: cannot decode image {i}: {exc}")
    if len(dimensions) < 2 or (32, 32) not in dimensions or (48, 48) not in dimensions:
        errors.append(f"{path.name}: expected 32×32 and 48×48 entries; got {dimensions}")
    return errors


def parse_chunks(data: bytes, start: int, end: int) -> list[tuple[bytes, bytes]]:
    chunks = []
    pos = start
    while pos + 8 <= end:
        tag = data[pos:pos + 4]
        size = struct.unpack_from("<I", data, pos + 4)[0]
        payload_start, payload_end = pos + 8, pos + 8 + size
        if payload_end > end:
            raise ValueError(f"chunk {tag!r} exceeds its parent")
        chunks.append((tag, data[payload_start:payload_end]))
        pos = payload_end + (size & 1)
    if pos != end:
        raise ValueError("trailing data in RIFF chunk list")
    return chunks


def validate_ani(path: Path) -> list[str]:
    errors: list[str] = []
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"ACON":
        return [f"{path.name}: invalid RIFF ACON header"]
    declared = struct.unpack_from("<I", data, 4)[0]
    if declared != len(data) - 8:
        errors.append(f"{path.name}: RIFF size mismatch")
    try:
        chunks = parse_chunks(data, 12, len(data))
        header = next(payload for tag, payload in chunks if tag == b"anih")
        frames_declared = struct.unpack_from("<I", header, 4)[0]
        frame_list = next(payload for tag, payload in chunks if tag == b"LIST" and payload[:4] == b"fram")
        frames = parse_chunks(frame_list, 4, len(frame_list))
        icons = [payload for tag, payload in frames if tag == b"icon"]
        if frames_declared < 2 or len(icons) < 2:
            errors.append(f"{path.name}: animated cursor must contain at least two icon frames")
        if frames_declared != len(icons):
            errors.append(f"{path.name}: header declares {frames_declared} frames but contains {len(icons)}")
        for i, icon in enumerate(icons):
            if len(icon) < 22 or struct.unpack_from("<HHH", icon)[:2] != (0, 2):
                errors.append(f"{path.name}: frame {i + 1} is not a CUR image")
    except Exception as exc:
        errors.append(f"{path.name}: malformed ANI: {exc}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pack", type=Path)
    args = ap.parse_args()
    root = args.pack
    problems: list[str] = []
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        ap.error("manifest.json not found in pack")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    roles = manifest.get("roles", {})
    if not REQUIRED.issubset(roles):
        problems.append(f"manifest misses roles: {sorted(REQUIRED - set(roles))}")
    for role, filename in roles.items():
        path = root / "Cursors" / filename
        if not path.is_file():
            problems.append(f"manifest role {role} points to missing file {filename}")
        elif path.suffix.lower() == ".cur":
            problems.extend(validate_cur(path))
        elif path.suffix.lower() == ".ani":
            problems.extend(validate_ani(path))
        else:
            problems.append(f"unsupported cursor file type: {filename}")
    for name in ("install.cmd", "install.ps1", "uninstall.cmd", "uninstall.ps1", "INSTALL.txt", "preview.png"):
        if not (root / name).is_file():
            problems.append(f"missing pack deliverable: {name}")
    theme_files = list(root.glob("*.theme"))
    if not theme_files:
        problems.append("missing Windows .theme file")
    for theme_path in theme_files:
        theme_text = theme_path.read_text(encoding="utf-16")
        if "[Control Panel\\Cursors]" not in theme_text:
            problems.append(f"{theme_path.name}: missing [Control Panel\\Cursors] section")
    for script in ("install.ps1", "uninstall.ps1"):
        path = root / script
        if path.is_file():
            content = path.read_text(encoding="utf-8-sig")
            if "HKCU:\\Control Panel\\Cursors" not in content:
                problems.append(f"{script}: expected per-user cursor registry path")
            if "'Schemes'" not in content:
                problems.append(f"{script}: expected named per-user scheme registry handling")
            if script == "install.ps1" and "$cursorRegistry.SetValue('', $schemeName" not in content:
                problems.append("install.ps1: expected to save the selected scheme name in the Cursors key")
            if "HKLM:" in content:
                problems.append(f"{script}: must not write machine-wide registry settings")
    if problems:
        print("VALIDATION FAILED")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"VALID: {len(roles)} cursor roles, CUR/ANI payloads, and installer files in {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
