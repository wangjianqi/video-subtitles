# Video Subtitles

> 基于 AI Agent 的视频自动识别、翻译与字幕生成工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#安装前置)

[English](#english) | 中文

---

## ✨ 功能特性

- 🎬 **本地语音识别** — 使用 MLX Whisper（Apple Silicon）或 Faster-Whisper（其他平台）在本地完成对白识别
- 🤖 **Agent 智能翻译** — 由 AI Agent 完成翻译，支持中英互译，保留上下文和术语一致性
- 🎨 **多种输出格式**
  - **烧录字幕视频** — 字幕直接嵌入画面，兼容性最好
  - **软字幕视频** — 可开关的字幕轨，不破坏原视频画面
  - **SRT 字幕文件** — 标准格式，便于后期编辑
  - **双语字幕** — 同时显示原文和译文
- 🔄 **完整工作流** — 从识别、翻译到渲染验证的一站式解决方案
- 🛡️ **无损输出** — 源视频不被覆盖，所有产物输出到独立目录
- 🔧 **高度可配置** — 支持自定义模型、字体、字号、边距等参数

## 🏗️ 架构概览

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│  transcribe │────▶│  Agent 翻译      │────▶│   render    │
│  本地识别    │     │  translation.json│     │   渲染输出   │
└─────────────┘     └─────────────────┘     └─────────────┘
       │                    │                       │
       ▼                    ▼                       ▼
  source.json         translation.json      subtitled.mp4
  (带时间轴)           (纯文本译文)          subtitles.srt
```

## 📋 安装前置

### 必需依赖

| 依赖 | 说明 | 安装方式 |
|------|------|----------|
| **Python** | 3.9 或更高版本 | [python.org](https://www.python.org/downloads/) |
| **uv** | 快速 Python 包管理器 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **FFmpeg** | 视频处理和字幕烧录 | 见下方说明 |

### FFmpeg 安装

FFmpeg 有三种获取方式，优先级从上到下：

1. **系统安装（推荐）**
   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt install ffmpeg

   # Windows (使用 winget)
   winget install Gyan.FFmpeg
   ```

2. **imageio-ffmpeg 内置** — 使用 `uv run --with imageio-ffmpeg` 时自动提供
3. **环境变量指定** — 设置 `SUBTITLE_FFMPEG=/path/to/ffmpeg`

> ⚠️ 烧录字幕需要 FFmpeg 编译时启用了 `libass/subtitles` 滤镜。系统包通常已包含。

### Whisper 后端

| 平台 | 推荐后端 | 安装 |
|------|----------|------|
| **Apple Silicon (M1/M2/M3)** | mlx-whisper | `uv run --with mlx-whisper` |
| **其他平台 (Intel/Linux/Windows)** | faster-whisper | `uv run --with faster-whisper` |

> 首次运行会自动下载 Whisper 模型（约 150MB~2.9GB）。使用 `--model /path/to/local/model` 可指定本地模型目录。

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/wangjianqi/video-subtitles.git
cd video-subtitles
```

### 2. 识别视频对白

```bash
# Apple Silicon (英文视频 → 中文)
uv run --with mlx-whisper --with imageio-ffmpeg \
  python scripts/subtitles.py transcribe "/path/to/video.mp4" \
  --source-lang en --target-lang zh \
  --output-dir "./output/video-zh"

# 其他平台 (中文视频 → 英文)
uv run --with faster-whisper --with imageio-ffmpeg \
  python scripts/subtitles.py transcribe "/path/to/video.mp4" \
  --source-lang zh --target-lang en \
  --backend faster-whisper \
  --output-dir "./output/video-en"
```

执行完成后会生成：
- `source.json` — 识别结果（带时间轴和原文）
- `translation.json` — 待填写的译文模板

### 3. AI Agent 翻译

这一步由 AI Agent（如 Trae、Cursor 等）自动完成。Agent 读取 `source.json`，将译文填入 `translation.json` 的每个 `text` 字段。

翻译质量要点：
- 保持人名、数字、术语一致性
- 中文字幕每行 ≤ 22 字，英文 ≤ 42 字
- 长视频分批处理（每批 50-100 条），携带上下文
- 结合上下文修正识别错误

### 4. 渲染输出

```bash
# 烧录字幕（默认，直接嵌入视频）
uv run --with imageio-ffmpeg \
  python scripts/subtitles.py render \
  --source "./output/video-zh/source.json" \
  --translation "./output/video-zh/translation.json" \
  --output-dir "./output/video-zh/final"

# 软字幕（可开关）
uv run --with imageio-ffmpeg \
  python scripts/subtitles.py render \
  --source "./output/video-zh/source.json" \
  --translation "./output/video-zh/translation.json" \
  --output-dir "./output/video-zh/final" \
  --mode soft

# 仅导出 SRT 文件
uv run --with imageio-ffmpeg \
  python scripts/subtitles.py render \
  --source "./output/video-zh/source.json" \
  --translation "./output/video-zh/translation.json" \
  --output-dir "./output/video-zh/final" \
  --mode srt

# 双语字幕（原文 + 译文）
uv run --with imageio-ffmpeg \
  python scripts/subtitles.py render \
  --source "./output/video-zh/source.json" \
  --translation "./output/video-zh/translation.json" \
  --output-dir "./output/video-zh/final" \
  --bilingual
```

### 5. 预览（可选）

想快速预览效果？使用 `--limit-seconds` 只处理前 N 秒：

```bash
uv run --with mlx-whisper --with imageio-ffmpeg \
  python scripts/subtitles.py transcribe "/path/to/video.mp4" \
  --source-lang en --target-lang zh \
  --output-dir "./output/preview" \
  --limit-seconds 30
```

## 📖 命令行参数

### transcribe

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `video` | ✅ | — | 输入视频文件路径 |
| `--output-dir` | ✅ | — | 输出目录 |
| `--source-lang` | ❌ | `auto` | 源语言（`en`, `zh`, `auto`） |
| `--target-lang` | ❌ | 自动推断 | 目标语言（`en`, `zh`） |
| `--backend` | ❌ | 平台默认 | Whisper 后端（`mlx`, `faster-whisper`） |
| `--model` | ❌ | `small` | Whisper 模型名称或本地路径 |
| `--limit-seconds` | ❌ | — | 仅处理前 N 秒（用于预览） |

### render

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--source` | ✅ | — | source.json 路径 |
| `--translation` | ✅ | — | translation.json 路径 |
| `--output-dir` | ✅ | — | 输出目录 |
| `--mode` | ❌ | `burn` | 输出模式（`burn`, `soft`, `srt`） |
| `--bilingual` | ❌ | `false` | 同时显示原文和译文 |
| `--font` | ❌ | `Arial Unicode MS` | 字幕字体（需已安装） |
| `--font-size` | ❌ | `22` | 字号 |
| `--margin-v` | ❌ | `24` | 底部边距（ASS 画布单位） |

## 📦 输出文件

| 文件 | 说明 |
|------|------|
| `source.json` | 识别结果，包含时间轴和原文（transcribe 阶段生成） |
| `translation.json` | 译文文件，Agent 翻译后填入（transcribe 生成模板，render 读取） |
| `subtitles.srt` | 标准 SRT 字幕文件 |
| `subtitled.mp4` | 带字幕的视频（burn/soft 模式） |

### source.json 结构

```json
{
  "video": "/absolute/path/to/video.mp4",
  "duration": 123.45,
  "source_language": "en",
  "target_language": "zh",
  "preview": false,
  "segments": [
    {"id": 1, "start": 0.5, "end": 3.2, "text": "Hello everyone."},
    {"id": 2, "start": 3.5, "end": 6.0, "text": "Welcome to the show."}
  ]
}
```

### translation.json 结构

```json
{
  "target_language": "zh",
  "segments": [
    {"id": 1, "text": "大家好。"},
    {"id": 2, "text": "欢迎来到节目现场。"}
  ]
}
```

## 🤖 作为 Trae Skill 使用

本项目也可以作为 [Trae](https://trae.ai) / [Cursor](https://cursor.com) 等 AI IDE 的 Skill 使用：

1. 将 `SKILL.md`、`scripts/subtitles.py`、`agents/openai.yaml` 放入 Skill 目录
2. AI Agent 会自动识别并调用本 Skill 完成字幕任务

详见 [SKILL.md](SKILL.md)。

## ❓ FAQ

### Q: 为什么烧录字幕时出现方块？
A: 目标语言字体缺失。请安装 `--font` 指定的字体，或使用 `--font "PingFang SC"` 等中文字体。

### Q: 如何使用更大的 Whisper 模型？
A: 使用 `--model large`（或 `medium`/`tiny` 等）。模型越大，识别越准确，但速度越慢。首次运行会下载对应模型。

### Q: 我的视频已经有字幕怎么办？
A: 使用 `--margin-v 60` 可以提高新字幕位置，避免重叠。完全移除原字幕需要额外处理。

### Q: 支持哪些语言？
A: Whisper 支持约 99 种语言识别（`--source-lang auto` 自动检测）。当前 `--target-lang` 仅支持中英互译（`zh` / `en`）。如需其他目标语言，可自行修改 CLI 参数校验。

### Q: 沙盒环境无法下载依赖怎么办？
A: 使用 `--cache-dir /tmp/video-subtitles-uv` 参数指定可写缓存目录。

### Q: 输出视频的 HDR 色彩会保留吗？
A: 默认流程不承诺保留 HDR。HDR 素材需要额外的色彩转换处理。

### Q: 如何取消已在运行的任务？
A: 直接 Ctrl+C 即可。已写入的文件可以安全删除，重新运行时请使用新的输出目录。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<a id="english"></a>

## English

> AI Agent-powered automatic video transcription, translation, and subtitle generation

### ✨ Features

- 🎬 **Local Speech Recognition** — Use MLX Whisper (Apple Silicon) or Faster-Whisper (other platforms) for on-device transcription
- 🤖 **Agent-Powered Translation** — AI Agent handles translation with context awareness and terminology consistency
- 🎨 **Multiple Output Formats**
  - **Burned-in Subtitles** — Embedded directly into video, best compatibility
  - **Soft Subtitles** — Toggleable subtitle track, preserves original video
  - **SRT Subtitle File** — Standard format for easy editing
  - **Bilingual Subtitles** — Show both original and translation
- 🔄 **Complete Workflow** — All-in-one solution from transcription through translation to rendering
- 🛡️ **Lossless Output** — Source video is never overwritten; all outputs go to separate directories
- 🔧 **Highly Configurable** — Customizable model, font, font size, margin, and more

### 🏗️ Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│  transcribe │────▶│  Agent Translate │────▶│   render    │
│  Local STT  │     │ translation.json │     │   Output    │
└─────────────┘     └─────────────────┘     └─────────────┘
       │                    │                       │
       ▼                    ▼                       ▼
  source.json         translation.json      subtitled.mp4
  (with timestamps)   (plain translation)   subtitles.srt
```

### 📋 Prerequisites

| Dependency | Description | Installation |
|------------|-------------|--------------|
| **Python** | 3.9+ | [python.org](https://www.python.org/downloads/) |
| **uv** | Fast Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **FFmpeg** | Video processing & subtitle burning | See below |

### FFmpeg Installation

Three options, priority top to bottom:

1. **System install (recommended)**
   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt install ffmpeg

   # Windows
   winget install Gyan.FFmpeg
   ```

2. **imageio-ffmpeg built-in** — Automatically provided when using `uv run --with imageio-ffmpeg`
3. **Environment variable** — Set `SUBTITLE_FFMPEG=/path/to/ffmpeg`

> ⚠️ Subtitle burning requires FFmpeg compiled with `libass/subtitles` filter. System packages usually include it.

### Whisper Backend

| Platform | Recommended Backend | Command |
|----------|---------------------|---------|
| **Apple Silicon (M1/M2/M3)** | mlx-whisper | `uv run --with mlx-whisper` |
| **Other (Intel/Linux/Windows)** | faster-whisper | `uv run --with faster-whisper` |

> First run downloads the Whisper model (~150MB~2.9GB). Use `--model /path/to/local/model` for offline usage.

### 🚀 Quick Start

```bash
# Clone
git clone https://github.com/wangjianqi/video-subtitles.git
cd video-subtitles

# Step 1: Transcribe
uv run --with mlx-whisper --with imageio-ffmpeg \
  python scripts/subtitles.py transcribe "video.mp4" \
  --source-lang en --target-lang zh \
  --output-dir "./output/video-zh"

# Step 2: AI Agent translates translation.json automatically

# Step 3: Render
uv run --with imageio-ffmpeg \
  python scripts/subtitles.py render \
  --source "./output/video-zh/source.json" \
  --translation "./output/video-zh/translation.json" \
  --output-dir "./output/video-zh/final"
```

For more details, see the Chinese section above.

### 📄 License

[MIT License](LICENSE)