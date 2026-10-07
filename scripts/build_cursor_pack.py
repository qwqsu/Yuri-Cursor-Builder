#!/usr/bin/env python3
"""Split a 3x3 transparent cursor concept sheet and build a Windows cursor pack."""
from __future__ import annotations

import argparse
import json
import math
import re
import struct
import textwrap
import zlib
from pathlib import Path
from typing import Iterable

from PIL import Image


CELLS = [
    ("Arrow", "Default arrow pointer"),
    ("Help", "Help pointer"),
    ("No", "Unavailable/error pointer"),
    ("IBeam", "Text select"),
    ("Crosshair", "Precision select"),
    ("SizeNS", "Vertical resize"),
    ("SizeWE", "Horizontal resize"),
    ("SizeNESW", "Southwest-northeast resize"),
    ("SizeNWSE", "Northwest-southeast resize"),
]
WINDOW_ROLES = [
    "Arrow", "Help", "AppStarting", "Wait", "Crosshair", "IBeam", "NWPen", "No",
    "SizeNS", "SizeWE", "SizeNWSE", "SizeNESW", "SizeAll", "UpArrow", "Hand",
]
CENTER_HOTSPOT = {"IBeam", "Crosshair", "SizeNS", "SizeWE", "SizeNESW", "SizeNWSE"}


def safe_name(value: str) -> str:
    value = re.sub(r"[^\w.-]+", "_", value.strip(), flags=re.UNICODE).strip("._")
    return value or "CharacterCursor"


def png_bytes(image: Image.Image) -> bytes:
    from io import BytesIO
    out = BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def cur_bytes(images: list[Image.Image], hotspot: tuple[int, int]) -> bytes:
    """Write PNG-backed CUR with 32/48 px entries and per-image hotspot."""
    payloads = [png_bytes(im.convert("RGBA")) for im in images]
    header = struct.pack("<HHH", 0, 2, len(images))
    offset = 6 + 16 * len(images)
    entries = bytearray()
    for im, payload in zip(images, payloads):
        w, h = im.size
        hx = min(max(round(hotspot[0] * w / 32), 0), w - 1)
        hy = min(max(round(hotspot[1] * h / 32), 0), h - 1)
        entries.extend(struct.pack("<BBBBHHII", w & 255, h & 255, 0, 0, hx, hy, len(payload), offset))
        offset += len(payload)
    return header + bytes(entries) + b"".join(payloads)


def fit_pixel_art(source: Image.Image, size: int, inset: int = 2) -> Image.Image:
    source = source.convert("RGBA")
    alpha = source.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        raise ValueError("a cursor cell is fully transparent")
    source = source.crop(bbox)
    max_side = size - 2 * inset
    factor = min(max_side / source.width, max_side / source.height)
    out_w = max(1, round(source.width * factor))
    out_h = max(1, round(source.height * factor))
    source = source.resize((out_w, out_h), Image.Resampling.NEAREST)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(source, ((size - out_w) // 2, (size - out_h) // 2))
    return out


def riff_chunk(tag: bytes, payload: bytes) -> bytes:
    chunk = tag + struct.pack("<I", len(payload)) + payload
    return chunk + (b"\0" if len(payload) % 2 else b"")


def build_ani(frame_cursors: list[bytes], rate_jiffies: int = 8) -> bytes:
    if len(frame_cursors) < 2:
        raise ValueError("an animated cursor needs at least two distinct frames")
    n = len(frame_cursors)
    # ANIHEADER: cbSize, cFrames, cSteps, cx, cy, cBitCount, cPlanes, jifRate, flags.
    anih = struct.pack("<9I", 36, n, n, 0, 0, 0, 0, rate_jiffies, 1)
    seq = struct.pack("<" + "I" * n, *range(n))
    rate = struct.pack("<" + "I" * n, *([rate_jiffies] * n))
    frames = b"".join(riff_chunk(b"icon", frame) for frame in frame_cursors)
    body = b"ACON" + riff_chunk(b"anih", anih) + riff_chunk(b"seq ", seq) + riff_chunk(b"rate", rate)
    body += riff_chunk(b"LIST", b"fram" + frames)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_installers(out: Path, pack_name: str, safe: str, role_files: dict[str, str]) -> None:
    (out / "manifest.json").write_text(json.dumps({
        "name": pack_name,
        "safeName": safe,
        "roles": role_files,
        "files": sorted(p.name for p in (out / "Cursors").glob("*") if p.is_file()),
        "windowsRoleOrder": WINDOW_ROLES,
        "missingRoles": [r for r in WINDOW_ROLES if r not in role_files],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    install = r'''$ErrorActionPreference = 'Stop'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$schemeName = [string]$manifest.name
$safeName = [string]$manifest.safeName
$cursorKey = 'HKCU:\Control Panel\Cursors'
$schemesKey = Join-Path $cursorKey 'Schemes'
$installRoot = Join-Path $env:LOCALAPPDATA ($safeName + '-CursorPack')
$target = Join-Path $installRoot 'Cursors'
$stateFile = Join-Path $installRoot 'backup.json'
if (Test-Path -LiteralPath $installRoot) {
  $marker = Join-Path $installRoot 'manifest.json'
  if (-not (Test-Path -LiteralPath $marker)) { throw "Install folder already exists and is not owned by this cursor pack: $installRoot" }
  $installed = Get-Content -LiteralPath $marker -Raw -Encoding UTF8 | ConvertFrom-Json
  if ([string]$installed.safeName -ne $safeName) { throw 'Install folder belongs to another cursor pack.' }
} else {
  New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
}
New-Item -ItemType Directory -Path $target -Force | Out-Null
Copy-Item -Path (Join-Path $PSScriptRoot 'Cursors\*') -Destination $target -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') -Destination (Join-Path $installRoot 'manifest.json') -Force
New-Item -Path $schemesKey -Force | Out-Null

$roleNames = @('Arrow','Help','AppStarting','Wait','Crosshair','IBeam','NWPen','No','SizeNS','SizeWE','SizeNWSE','SizeNESW','SizeAll','UpArrow','Hand')
$current = Get-ItemProperty -LiteralPath $cursorKey
$backup = [ordered]@{}
foreach ($role in ($roleNames + @('Scheme Source'))) {
  $prop = $current.PSObject.Properties[$role]
  if ($null -ne $prop) { $backup[$role] = @{ exists = $true; value = $prop.Value; type = if ($role -eq 'Scheme Source') {'DWord'} else {'String'} } }
  else { $backup[$role] = @{ exists = $false; value = $null; type = 'String' } }
}
$cursorRegistry = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Control Panel\Cursors', $true)
$hasSchemeName = $cursorRegistry.GetValueNames() -contains ''
if ($hasSchemeName) {
  $backup['_cursorSchemeName'] = @{ exists = $true; value = [string]$cursorRegistry.GetValue('', $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames); type = $cursorRegistry.GetValueKind('').ToString() }
} else {
  $backup['_cursorSchemeName'] = @{ exists = $false; value = ''; type = 'String' }
}
$cursorRegistry.Close()
if (-not (Test-Path -LiteralPath $stateFile)) {
  $oldScheme = (Get-ItemProperty -LiteralPath $schemesKey).PSObject.Properties[$schemeName]
  if ($null -ne $oldScheme) { $backup['_schemeEntry'] = @{ exists = $true; value = [string]$oldScheme.Value } }
  else { $backup['_schemeEntry'] = @{ exists = $false; value = '' } }
  $backup | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $stateFile -Encoding UTF8
}

$roleFiles = @{}
foreach ($property in $manifest.roles.PSObject.Properties) { $roleFiles[$property.Name] = [string]$property.Value }
$parts = foreach ($role in $roleNames) {
  if ($roleFiles.ContainsKey($role)) {
    Join-Path $target $roleFiles[$role]
  } else {
    $existing = $current.PSObject.Properties[$role]
    if ($null -ne $existing) { [string]$existing.Value } else { '' }
  }
}
$schemeValue = $parts -join ','
New-ItemProperty -LiteralPath $schemesKey -Name $schemeName -Value $schemeValue -PropertyType String -Force | Out-Null
foreach ($role in $roleFiles.Keys) {
  Set-ItemProperty -LiteralPath $cursorKey -Name $role -Value (Join-Path $target $roleFiles[$role])
}
New-ItemProperty -LiteralPath $cursorKey -Name 'Scheme Source' -Value 2 -PropertyType DWord -Force | Out-Null
$cursorRegistry = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Control Panel\Cursors', $true)
$cursorRegistry.SetValue('', $schemeName, [Microsoft.Win32.RegistryValueKind]::String)
$cursorRegistry.Close()

$theme = @('[Theme]', ('DisplayName=' + $schemeName), '', '[Control Panel\Cursors]')
foreach ($role in $roleNames) {
  if ($roleFiles.ContainsKey($role)) { $theme += ($role + '=' + (Join-Path $target $roleFiles[$role])) }
}
$theme += 'DefaultValue=Windows default'
[IO.File]::WriteAllLines((Join-Path $installRoot ($safeName + '.theme')), $theme, [Text.Encoding]::Unicode)

if (-not ('YuriCursorUser32' -as [type])) {
  Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class YuriCursorUser32 { [DllImport("user32.dll", SetLastError=true)] public static extern bool SystemParametersInfo(uint action, uint param, IntPtr value, uint flags); }'
}
[void][YuriCursorUser32]::SystemParametersInfo(0x0057, 0, [IntPtr]::Zero, 0x0003)
Write-Host ("Installed and registered mouse scheme: " + $schemeName)
Write-Host ("Files: " + $target)
'''
    uninstall = r'''$ErrorActionPreference = 'Stop'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$schemeName = [string]$manifest.name
$safeName = [string]$manifest.safeName
$cursorKey = 'HKCU:\Control Panel\Cursors'
$schemesKey = Join-Path $cursorKey 'Schemes'
$installRoot = Join-Path $env:LOCALAPPDATA ($safeName + '-CursorPack')
$target = Join-Path $installRoot 'Cursors'
$stateFile = Join-Path $installRoot 'backup.json'
if (Test-Path -LiteralPath $stateFile) {
  $backup = Get-Content -LiteralPath $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json
  $schemeEntry = $backup.PSObject.Properties['_schemeEntry'].Value
  if (Test-Path -LiteralPath $schemesKey) {
    if ($schemeEntry.exists) { New-ItemProperty -LiteralPath $schemesKey -Name $schemeName -Value $schemeEntry.value -PropertyType String -Force | Out-Null }
    else { Remove-ItemProperty -LiteralPath $schemesKey -Name $schemeName -ErrorAction SilentlyContinue }
  }
  foreach ($property in $backup.PSObject.Properties) {
    $role = $property.Name; $entry = $property.Value
    if ($role -in @('_schemeEntry','_cursorSchemeName')) { continue }
    if ($entry.exists) {
      $kind = if ($entry.type -eq 'DWord') { 'DWord' } else { 'String' }
      New-ItemProperty -LiteralPath $cursorKey -Name $role -Value $entry.value -PropertyType $kind -Force | Out-Null
    } else {
      Remove-ItemProperty -LiteralPath $cursorKey -Name $role -ErrorAction SilentlyContinue
    }
  }
  $oldName = $backup.PSObject.Properties['_cursorSchemeName'].Value
  $cursorRegistry = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Control Panel\Cursors', $true)
  if ($oldName.exists) {
    $kind = [Enum]::Parse([Microsoft.Win32.RegistryValueKind], [string]$oldName.type)
    $cursorRegistry.SetValue('', [string]$oldName.value, $kind)
  } else {
    $cursorRegistry.DeleteValue('', $false)
  }
  $cursorRegistry.Close()
  $installed = Get-Content -LiteralPath (Join-Path $installRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction SilentlyContinue
  if ($null -ne $installed) {
    foreach ($filename in $installed.files) {
      Remove-Item -LiteralPath (Join-Path $target ([string]$filename)) -Force -ErrorAction SilentlyContinue
    }
  }
  Remove-Item -LiteralPath (Join-Path $installRoot ($safeName + '.theme')) -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath (Join-Path $installRoot 'manifest.json') -Force -ErrorAction SilentlyContinue
  if ((Test-Path -LiteralPath $target -PathType Container) -and -not (Get-ChildItem -LiteralPath $target -Force | Select-Object -First 1)) { Remove-Item -LiteralPath $target -Force }
  if ((Test-Path -LiteralPath $installRoot -PathType Container) -and -not (Get-ChildItem -LiteralPath $installRoot -Force | Select-Object -First 1)) { Remove-Item -LiteralPath $installRoot -Force }
  if (-not ('YuriCursorUser32' -as [type])) {
    Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class YuriCursorUser32 { [DllImport("user32.dll", SetLastError=true)] public static extern bool SystemParametersInfo(uint action, uint param, IntPtr value, uint flags); }'
  }
  [void][YuriCursorUser32]::SystemParametersInfo(0x0057, 0, [IntPtr]::Zero, 0x0003)
  Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
  Write-Host ("Removed " + $schemeName + " and restored previous cursor values.")
} else {
  Write-Warning 'No backup was found; removed the scheme entry only and left current cursor values untouched.'
}
'''
    (out / "install.ps1").write_text(install, encoding="utf-8-sig")
    (out / "uninstall.ps1").write_text(uninstall, encoding="utf-8-sig")
    (out / "install.cmd").write_text('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"\r\nif errorlevel 1 pause\r\n', encoding="utf-8")
    (out / "uninstall.cmd").write_text('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"\r\nif errorlevel 1 pause\r\n', encoding="utf-8")

    theme = ["[Theme]", f"DisplayName={pack_name}", "", "[Control Panel\\Cursors]"]
    for role, filename in role_files.items():
        theme.append(f"{role}=%LOCALAPPDATA%\\{safe}-CursorPack\\Cursors\\{filename}")
    theme.append("DefaultValue=Windows default")
    (out / f"{safe}.theme").write_text("\r\n".join(theme) + "\r\n", encoding="utf-16")
    readme = f"""{pack_name} Windows cursor scheme\n\nInstall: double-click install.cmd. It copies files to %LOCALAPPDATA%, registers the scheme for the current user, and applies available roles. No administrator rights are needed.\n\nThe nine generated roles are: {', '.join(role_files)}. Other cursor roles retain their previous values.\n\nUninstall: double-click uninstall.cmd in this folder to remove this scheme and restore the cursor values backed up at installation.\n"""
    (out / "INSTALL.txt").write_text(readme, encoding="utf-8")


def make_ani_frames(folder: Path, out: Path, hotspot_by_role: dict[str, tuple[int, int]]) -> dict[str, str]:
    generated: dict[str, str] = {}
    for role in ("Help", "No", "Arrow", "Wait", "AppStarting"):
        role_dir = folder / role
        if not role_dir.is_dir():
            continue
        paths = sorted([*role_dir.glob("*.png"), *role_dir.glob("*.PNG")])
        frames: list[bytes] = []
        previous = None
        for path in paths:
            with Image.open(path) as im:
                frame = fit_pixel_art(im, 32)
                signature = frame.tobytes()
                if signature == previous:
                    continue
                previous = signature
                frames.append(cur_bytes([frame], hotspot_by_role.get(role, (2, 2))))
        if len(frames) >= 2:
            filename = f"{role}.ani"
            (out / "Cursors" / filename).write_bytes(build_ani(frames))
            generated[role] = filename
    return generated


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sheet", required=True, type=Path, help="selected transparent 3x3 concept PNG")
    ap.add_argument("--output", required=True, type=Path, help="output cursor pack directory")
    ap.add_argument("--name", default="Character Cursor", help="display name for the mouse scheme")
    ap.add_argument("--animation-frames", type=Path, help="optional directory with role folders containing 2+ distinct frame PNGs")
    args = ap.parse_args()
    if not args.sheet.is_file():
        ap.error(f"sheet not found: {args.sheet}")
    with Image.open(args.sheet) as im:
        sheet = im.convert("RGBA")
    if sheet.width < 300 or sheet.height < 300 or abs(sheet.width - sheet.height) > 2:
        ap.error("concept sheet must be a square 3x3 sprite sheet at least 300×300 pixels")
    alpha_min, alpha_max = sheet.getchannel("A").getextrema()
    if alpha_min == alpha_max == 255:
        ap.error("sheet has no transparency; regenerate the selected concept with a transparent background")

    safe = safe_name(args.name)
    out = args.output.resolve()
    cursors = out / "Cursors"
    previews = out / "Preview"
    cursors.mkdir(parents=True, exist_ok=True)
    previews.mkdir(parents=True, exist_ok=True)
    role_files: dict[str, str] = {}
    hotspot_by_role: dict[str, tuple[int, int]] = {}
    for index, (role, description) in enumerate(CELLS):
        row, col = divmod(index, 3)
        left, right = round(col * sheet.width / 3), round((col + 1) * sheet.width / 3)
        top, bottom = round(row * sheet.height / 3), round((row + 1) * sheet.height / 3)
        cell = sheet.crop((left, top, right, bottom))
        if cell.getchannel("A").getbbox() is None:
            ap.error(f"cell {index + 1} ({role}) is empty; repair or regenerate the concept sheet")
        icon32, icon48 = fit_pixel_art(cell, 32), fit_pixel_art(cell, 48, inset=3)
        icon32.save(previews / f"{index + 1:02d}_{role}.png")
        hotspot = (2, 2) if role in {"Arrow", "Help", "No"} else (16, 16)
        hotspot_by_role[role] = hotspot
        (cursors / f"{role}.cur").write_bytes(cur_bytes([icon32, icon48], hotspot))
        role_files[role] = f"{role}.cur"

    if args.animation_frames:
        if not args.animation_frames.is_dir():
            ap.error("--animation-frames must be a folder")
        role_files.update(make_ani_frames(args.animation_frames, out, hotspot_by_role))

    write_installers(out, args.name.strip() or "Character Cursor", safe, role_files)
    # A preview of the actual cursor-sized pixels in the same 3x3 role order.
    preview = Image.new("RGBA", (3 * 192, 3 * 192), (245, 243, 238, 255))
    for i, (role, _) in enumerate(CELLS):
        im = Image.open(previews / f"{i + 1:02d}_{role}.png").convert("RGBA").resize((128, 128), Image.Resampling.NEAREST)
        x, y = (i % 3) * 192 + 32, (i // 3) * 192 + 32
        preview.alpha_composite(im, (x, y))
    preview.convert("RGB").save(out / "preview.png")
    print(f"Built cursor pack at {out}")
    print(f"Created {len(CELLS)} standard cursor roles and {sum(n.endswith('.ani') for n in role_files.values())} animated roles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
