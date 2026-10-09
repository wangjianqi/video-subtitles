# 变更日志

所有重要变更都将记录在此文件中。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-10-09

### 新增

- 🎬 本地视频语音识别（支持 mlx-whisper 和 faster-whisper）
- 🤖 AI Agent 翻译工作流（source.json → translation.json）
- 🎨 三种字幕输出模式：
  - `burn` — 烧录字幕视频
  - `soft` — 可开关软字幕
  - `srt` — 仅导出 SRT 文件
- 🌐 中英双语字幕支持，自动语言检测
- 📝 双语字幕输出（`--bilingual`）
- 🔧 可配置字体、字号、边距等渲染参数
- ✅ 时间轴、ID、空文本等自动校验
- 📋 完整的 CLI 参数支持
- 🛠️ SKILL.md 支持作为 AI IDE Skill 使用