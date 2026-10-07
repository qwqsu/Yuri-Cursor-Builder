---
name: yuri-cursor-builder
description: Create a consistent pixel-art Windows cursor scheme from the character reference images the user provides, without a fixed minimum image count. Use when a user wants Codex to infer a character canon and art style, write a reusable four-layer prompt template, approve a character example before generating several 3×3 cursor concept sheets, and turn the selected design into installable .cur/.ani files registered as a Windows mouse scheme.
---

# Yuri Cursor Builder

Turn a set of character references into a selectable, installable Windows cursor scheme while keeping the character recognizable at cursor size.

If the user asks for only a prompt, template, or concept sheet, stop at that requested stage; do not create or install a cursor pack beyond the requested scope.

## Workflow

### 1. Check the references

- Work with however many readable character reference images the user provides. Do not impose an eight-image minimum or request extra images just to meet a count. More references can clarify recurring traits, but the user decides whether to add any.
- Verify the supplied image bytes can be opened. If an attachment path is stale, use the current uploaded file paths or ask the user to reattach only the inaccessible images; never reuse a guessed temporary path.
- Make a contact sheet with `scripts/make_reference_sheet.py` when useful. Analyze all available images together. Treat recurring traits as supported canon, changes as scene-specific, and one-off decorations, text, or backgrounds as non-canonical unless the user says otherwise. With sparse or conflicting references, mark uncertain traits as provisional instead of filling gaps with invented details.
- Preserve the user's chosen character name. If none is given, ask once before writing the deliverable filenames and prompts.

### 2. Derive the prompt system

Create `角色光标_四层提示词模板.md` in the task output folder from `assets/four-layer-prompt-template.md`. Use the title `角色光标：四层提示词模板`; use an underscore in the filename because `:` is invalid in Windows filenames:

1. Fill `CHARACTER_CANON` with visual traits supported by the reference set.
2. Fill `STYLE_CANON` with the common drawing technique, palette, edge quality, and detail density.
3. Keep the four consistency locks intact: identity, face, pixel style, and intentional imperfection. Adjust only wording that would contradict the supplied references.
4. Keep `SCENE_VARIABLES` editable and include a nine-state cursor mapping.

Also write a concise **master generation prompt** in the same file (or a separate `总生成提示词.md` if the user asks for a standalone prompt). Do not claim a feature is consistent when references conflict; note the ambiguity and resolve it by the most repeated evidence or ask the user if the choice changes the character identity.

### 3. Generate and confirm a character example

- After creating the prompt template, generate **one character example image** using the current canon, style, and original reference images. This is a likeness check, not a new source of character facts.
- Show the example and ask whether the character looks right. Pause before making any cursor concept sheets.
- If the user approves, continue to selectable concepts. If the user says the example is too different, invite them to optionally upload any additional references they think will help. Revise the canon and template from all original and newly provided references, then generate a new single character example and wait for approval again. Do not require a specific number of extra images.
- If the user gives correction notes without more images, incorporate them as explicit user-provided canon and regenerate the example for approval.

### 4. Generate selectable concepts

- After the user approves the character example, generate **three** distinct 3×3 transparent concept sheets, each with nine cursor states in the same fixed order defined in `references/cursor-state-map.md`.
- Use the entire reference set for each candidate. Keep identity and pixel style locked; vary only the cursor integration approach (for example, character embedded in the cursor glyph, character head attached to the glyph, or compact character silhouette integrated with the glyph).
- Keep the glyph's function legible: the arrow tip, question mark, error mark, text beam, crosshair, and resize directions must remain recognizable. Keep each cell separate, with no labels or borders inside the artwork.
- Present the candidates as **A / B / C**, summarize their visual difference in one line each, and ask the user to choose one. Stop here until the user selects a candidate. Do not silently choose or build an installable pack before selection.

### 5. Build the selected cursor pack

- Generate or refine the selected 3×3 sheet using the chosen candidate as a design reference and the original character references as identity references. Require transparent background.
- Inspect the selected sheet before splitting. If a state symbol is missing, ambiguous, clipped, or placed in the wrong cell, repair or regenerate the sheet before packaging.
- Run `scripts/build_cursor_pack.py` to split the sheet, trim transparent margins, nearest-neighbor scale to 32×32 and 48×48 cursor images, and package standard `.cur` files with role-appropriate hotspots.
- Run it as `python scripts/build_cursor_pack.py --sheet <selected-3x3.png> --output <pack-folder> --name "<scheme display name>"` from the skill directory or use absolute paths. Pillow is required.
- Map the nine cells exactly as defined in `references/cursor-state-map.md`. Leave unavailable Windows roles on the user's existing cursor values rather than assigning an unrelated icon.
- If the design includes actual multi-frame artwork, place frames in role-named folders and pass `--animation-frames`. The builder writes valid RIFF `.ani` files from two or more frames. Never label a static duplicate as an animation.
- Create `install.cmd`, `install.ps1`, `uninstall.cmd`, `uninstall.ps1`, `manifest.json`, a preview sheet, and a `.theme` file. The installer copies assets under `%LOCALAPPDATA%`, registers a named scheme under the current user's `HKCU\Control Panel\Cursors\Schemes`, applies the mapped roles, and refreshes system cursors. Do not require administrator privileges.
- Preserve existing cursor assignments for roles not included in the concept sheet. Back up the prior current assignments and restore them on uninstall.
- Run `scripts/validate_cursor_pack.py` on the finished pack. Do not claim the Windows registry change was tested unless the scripts were actually run on Windows. On non-Windows hosts, validate binary formats and clearly state that Windows-side installation still needs a Windows smoke test.

## Cursor order and safety

Read `references/cursor-state-map.md` before generating or splitting a sheet. Read `references/windows-mouse-schemes.md` before changing installer behavior. Windows theme files support cursor roles, while the installer must separately register the named entry in the per-user mouse scheme registry list. Keep installation scoped to the current user; do not modify `HKLM`, system cursor files, or unrelated registry values.

## Deliverables

Return the generated four-layer template, the approved character example, the three concept choices, and after selection the installable cursor pack directory. Give direct links to the template, character example, selected preview, and install script. The pack must include a one-click `.cmd` installer and a reversible uninstaller. Do not return a ZIP unless the user asks for one.
