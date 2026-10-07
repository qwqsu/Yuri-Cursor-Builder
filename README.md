# Yuri Cursor Builder

把角色参考图变成一套统一风格的像素 Windows 鼠标光标。工作流会先归纳角色与画风，再生成可复用的四层提示词和多张光标概念图；选定方案后，打包成可安装、可卸载并显示在 Windows“鼠标方案”列表中的光标主题。

## 工作流程

1. **提供角色参考图**：上传至少 8 张清晰、不同角度或状态的角色图，并告诉 Codex 角色名称。
2. **建立角色规范**：归纳稳定的角色特征与共同画风，生成总生成提示词和《角色光标：四层提示词模板》。
3. **挑选概念方案**：生成 3 张透明背景的 3×3 像素光标概念图，分别标为 A、B、C；用户选择前不会打包光标。
4. **生成 Windows 光标包**：根据选定底稿导出 `.cur` 光标文件、安装与卸载脚本、预览图和方案文件；有真实多帧素材时也可生成 `.ani` 动画光标。

## 3×3 光标状态顺序

概念图按下表固定顺序排列。图中的每个格子对应一个 Windows 光标角色：

| 位置 | 光标状态 | Windows 角色 |
| --- | --- | --- |
| 1 | 普通选择 | Arrow |
| 2 | 帮助选择 | Help |
| 3 | 不可用 | No |
| 4 | 文本选择 | IBeam |
| 5 | 精确选择 | Crosshair |
| 6 | 垂直调整大小 | SizeNS |
| 7 | 水平调整大小 | SizeWE |
| 8 | 对角调整大小（左下—右上） | SizeNESW |
| 9 | 对角调整大小（左上—右下） | SizeNWSE |

完整定义见 [`references/cursor-state-map.md`](references/cursor-state-map.md)。

## 在 Codex 中使用

启用 `yuri-cursor-builder` Skill，然后在对话中：

1. 上传 **至少 8 张**角色参考图。请确保图像能正常打开；如果附件失效，请重新上传。
2. 说明角色名称，以及希望保留的关键特征或偏好的光标设计方向。
3. 查看 A、B、C 三张概念图并选择一张。
4. 在 Windows 上运行生成包中的 `install.cmd` 安装；如需恢复原光标，运行 `uninstall.cmd`。

示例请求：

> 请用这些参考图为尤里制作像素风 Windows 光标。先生成总提示词和四层模板，再给我 3 张 3×3 概念图供我选择。

## 安装包内容

生成的光标包通常包含：

- 按光标角色命名的 `.cur` 文件；有真实多帧图时才会包含 `.ani`。
- `install.cmd` / `install.ps1`：安装并应用光标方案。
- `uninstall.cmd` / `uninstall.ps1`：恢复安装前保存的光标设置。
- `.theme`、`manifest.json` 和预览图。

安装器将光标文件放在当前用户的 `%LOCALAPPDATA%` 下，并在当前用户的 Windows 鼠标方案列表中注册方案，不需要管理员权限。概念图未提供的光标角色会保留用户现有设置。安装前请检查生成包中的文件和说明；建议先在 Windows 虚拟机或非主要账户中试用。

## 本仓库结构

| 路径 | 内容 |
| --- | --- |
| [`SKILL.md`](SKILL.md) | Codex Skill 的完整工作流与生成约束 |
| [`assets/four-layer-prompt-template.md`](assets/four-layer-prompt-template.md) | 四层提示词模板底稿 |
| [`references/cursor-state-map.md`](references/cursor-state-map.md) | 3×3 格子与 Windows 光标角色映射 |
| [`references/windows-mouse-schemes.md`](references/windows-mouse-schemes.md) | Windows 鼠标方案注册说明 |
| [`scripts/make_reference_sheet.py`](scripts/make_reference_sheet.py) | 制作角色参考图联系表 |
| [`scripts/build_cursor_pack.py`](scripts/build_cursor_pack.py) | 切分概念图并生成光标包 |
| [`scripts/validate_cursor_pack.py`](scripts/validate_cursor_pack.py) | 检查光标包文件与格式 |

## 运行打包脚本

本地运行 Python 脚本需要 Python 3 和 Pillow。示例：

```bash
python -m pip install Pillow
python scripts/build_cursor_pack.py --sheet selected-3x3.png --output Yuri-Cursors --name "Yuri Pixel Cursors"
python scripts/validate_cursor_pack.py Yuri-Cursors
```

请先确认 `selected-3x3.png` 是已经选定并检查过的 3×3 概念图。具体参数以脚本帮助信息为准：

```bash
python scripts/build_cursor_pack.py --help
python scripts/validate_cursor_pack.py --help
```

## 验证说明

打包脚本可在非 Windows 环境中检查生成的文件与光标二进制格式，但 Windows 注册表写入、方案列表显示和系统光标刷新仍需在实际 Windows 环境中做安装冒烟测试。不要把跨平台格式检查描述为 Windows 安装测试。

## 许可

本仓库未声明开源许可证。公开或再分发前，请仓库维护者选择并添加适用的许可证文件；在此之前，使用权限以仓库作者明确授予的权限为准。
