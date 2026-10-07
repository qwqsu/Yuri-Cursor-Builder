# Windows cursor scheme packaging

## File roles

- `.cur` is the still cursor format. Include an explicit hotspot for each image and at least 32×32 output; this skill writes 32×32 and 48×48 PNG-backed CUR entries.
- `.ani` is a RIFF animated cursor. Emit it only from two or more distinct frames; otherwise keep the role as `.cur`.
- A Windows `.theme` file can specify values in `[Control Panel\Cursors]`. Microsoft documents the supported cursor role names and `.cur`/`.ani` paths in the Theme File Format reference.
- The Windows Mouse Properties scheme picker is separate from simply producing `.theme`; the per-user installer writes a named comma-delimited scheme entry under `HKCU\Control Panel\Cursors\Schemes`, applies the mapped role paths under `HKCU\Control Panel\Cursors`, and updates the Cursors key's unnamed current-scheme value. Microsoft's Scripting Blog documents the per-role values, unnamed current-scheme name, and cursor refresh call.

## Installer requirements

1. Copy cursor files into a stable path under `%LOCALAPPDATA%`; absolute paths in registry values must continue to resolve after the download folder moves.
2. Back up only the current user's cursor role values and `Scheme Source` before changing them. Preserve all roles the generated set does not supply.
3. Register a named scheme and apply it without administrator privileges. Never write to `HKLM` or overwrite files under `%SystemRoot%`.
4. Refresh cursors with `SystemParametersInfo(SPI_SETCURSORS, 0, NULL, ...)`. The official API documentation says this reloads system cursors; use the update/send-change flags where applicable.
5. Provide an uninstaller that removes only this scheme and restores the backup values. Keep user files outside the generated pack untouched.
6. Generate a `.theme` alongside the registry scheme entry for discoverability. Do not claim the `.theme` itself guarantees appearing in Mouse Properties' Scheme dropdown.

## Validation limitations

CUR/ANI binary structures and package scripts can be validated cross-platform, but registry behavior and the Mouse Properties dropdown must receive a Windows smoke test before claiming Windows execution was verified. The skill's Python tools do not execute PowerShell or modify the registry.

## Microsoft references

- [Theme File Format — `[Control Panel\Cursors]`](https://learn.microsoft.com/en-us/windows/win32/controls/themesfileformat-overview)
- [Resource File Formats — CUR hotspots and PNG-compressed cursor data](https://learn.microsoft.com/en-us/windows/win32/menurc/resource-file-formats)
- [SystemParametersInfo — `SPI_SETCURSORS`](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-systemparametersinfoa)
- [Microsoft Scripting Blog — Use PowerShell to Change the Mouse Pointer Scheme](https://devblogs.microsoft.com/scripting/use-powershell-to-change-the-mouse-pointer-scheme/)
