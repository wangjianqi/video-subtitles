# 贡献指南

感谢你对 video-subtitles 感兴趣！欢迎任何形式的贡献。

## 🤝 如何贡献

### 报告 Bug

1. 搜索现有 [Issues](https://github.com/wangjianqi/video-subtitles/issues) 确认问题未被报告
2. 创建新 Issue，包含：
   - 清晰的标题
   - 可复现的步骤
   - 预期行为 vs 实际行为
   - 环境信息（操作系统、Python 版本、FFmpeg 版本）
   - 相关日志或错误信息

### 建议新功能

1. 先搜索现有 Issues 和 Discussions
2. 创建 Feature Request Issue，描述：
   - 功能用途
   - 预期使用场景
   - 可能的实现思路

### 提交 Pull Request

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

## 📐 开发规范

### 代码风格

本项目遵循 [PEP 8](https://peps.python.org/pep-0008/) 风格指南，使用 [Ruff](https://docs.astral.sh/ruff/) 进行格式化和检查：

```bash
# 安装开发依赖
pip install ruff

# 检查代码
ruff check scripts/

# 自动修复
ruff check --fix scripts/

# 格式化
ruff format scripts/
```

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 风格：

```
feat: 添加双语字幕支持
fix: 修复 FFmpeg 路径检测失败的问题
docs: 更新 README 安装说明
refactor: 重构字幕渲染逻辑
test: 添加转写参数校验测试
chore: 更新依赖版本
```

## 🧪 测试

提交前请确保你的更改可以正常运行：

```bash
# 测试转写功能（使用 --limit-seconds 快速验证）
uv run --with mlx-whisper --with imageio-ffmpeg \
  python scripts/subtitles.py transcribe "test.mp4" \
  --source-lang en --target-lang zh \
  --output-dir "./test-output" \
  --limit-seconds 10

# 测试渲染功能
uv run --with imageio-ffmpeg \
  python scripts/subtitles.py render \
  --source "./test-output/source.json" \
  --translation "./test-output/translation.json" \
  --output-dir "./test-output/final"
```

## 📋 PR Checklist

- [ ] 代码符合 Ruff 检查
- [ ] 代码已格式化
- [ ] 测试通过
- [ ] 已更新相关文档
- [ ] 已添加 changelog 条目（如适用）
- [ ] PR 描述清晰，关联相关 Issue

## 📄 许可证

通过贡献代码，你同意你的贡献将按照 [MIT License](LICENSE) 授权给项目。