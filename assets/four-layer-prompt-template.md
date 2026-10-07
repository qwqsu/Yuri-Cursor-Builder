# {{CHARACTER_NAME}} 角色光标：四层提示词模板

本文件是生成式图像 Prompt 模板。第 1–3 层固定，第 4 层仅按本次光标场景填写。角色设定只写参考图中有证据支持的共性，不把单张图的偶然元素误写成身份特征。

## ① CHARACTER_CANON｜角色身份

{{CHARACTER_CANON_FROM_USER_PROVIDED_REFERENCES}}

## ② STYLE_CANON｜系列画风

{{STYLE_CANON_FROM_ALL_REFERENCES}}

## ③ CONSISTENCY_LOCKS｜四个强锁

以下强锁优先于动作、状态符号、构图和创意变化。

### IDENTITY_LOCK
始终是同一个角色。保留参考图中反复出现且足以识别角色的轮廓、发型、颜色、配件和比例。只有确实被姿势或光标状态遮挡时才允许暂时不可见；不得借此重设计角色。

### FACE_LOCK
保持参考图中的面部构造和表情语言。允许改变情绪，不改变脸部设计系统；在小尺寸下优先保留最具辨识度的五官，禁止擅自精修或增加不符合参考图的细节。

### PIXEL_LOCK
保持参考图的像素尺度、硬边、调色板、描边和细节密度。使用清晰的像素阶梯边缘和最近邻缩放逻辑；禁止抗锯齿、平滑渐变、写实渲染、3D 和无依据的细节添加。

### IMPERFECTION_LOCK
保留参考图有意的简化、笨拙比例、略微不均匀的线条和原始可爱感。不要“改善”成精致商业插画。粗糙必须与参考图一致，不得变成随机失真。

## ④ SCENE_VARIABLES｜每张光标图可变

使用 `references/cursor-state-map.md` 中九格顺序；每格必须有透明背景、清楚可辨的状态符号和可用的鼠标热点。参考角色图优先决定角色外观，光标样例图只决定功能符号和方向。

```text
IMAGE_ID: {{ID}}
WINDOWS_CURSOR_ROLE: {{Arrow|Help|No|IBeam|Crosshair|SizeNS|SizeWE|SizeNESW|SizeNWSE}}
SCENE/ACTION: {{角色如何与状态符号结合}}
EXPRESSION: {{表情}}
PROPS/SYMBOLS: {{只列帮助问号、错误标记等必要元素}}
COMPOSITION: {{方向、热点位置、图标占比}}
BACKGROUND: fully transparent
TEXT: none (except the single conventional ? symbol in Help)
SPECIAL_REQUIREMENTS: preserve CHARACTER_CANON, STYLE_CANON, and all four locks
```

## 总生成提示词

```text
使用用户提供的全部可读取角色参考图，综合提取有依据的 CHARACTER_CANON 与 STYLE_CANON；不要求固定数量的参考图。参考较少或互相矛盾时，将不确定特征标为暂定，并先生成一张角色示例图供用户确认。严格遵循本文件的四层结构：CHARACTER_CANON、STYLE_CANON 与四个 CONSISTENCY_LOCKS 固定，只有 SCENE_VARIABLES 可以改变。用户确认角色示例图后，再生成透明背景的低分辨率像素 Windows 光标；角色在 32×32 尺寸仍需辨认，功能符号和热点优先清晰。不要把参考图中的场景文字、背景或一次性装饰误当成人物设定。不要美化、重设计、抗锯齿或补入未要求的物件。
```
