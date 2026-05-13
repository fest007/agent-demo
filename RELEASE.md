# Release

本项目的发布链路支持两种入口：修改 `VERSION` 后推送到 `main`，或推送 `vX.Y.Z` tag。GitHub Actions 会自动构建 Tauri 桌面安装包并上传到 GitHub Releases。

## 本地发版步骤

```bash
source ~/.nvm/nvm.sh
nvm use 23

node scripts/bump-version.mjs 0.2.0
git add VERSION agent-demo-web/package.json agent-demo-agent/pyproject.toml agent-demo-server/pyproject.toml
git commit -m "chore: release v0.2.0"
git push origin main
```

如需显式打 tag，也可以继续执行：

```bash
git tag v0.2.0
git push origin v0.2.0
```

## 自动打包内容

- `agent-demo-<version>-macos.dmg`：macOS 桌面安装包
- `agent-demo-<version>-windows.exe`：Windows NSIS 安装包
- `agent-demo-<version>-macos.tar.gz` / `agent-demo-<version>-windows.zip`：源码/部署补充包

桌面包采用 Tauri + Python sidecar MVP：Tauri 负责桌面壳，PyInstaller 将 FastAPI 后端打成 sidecar，应用启动时只绑定 `127.0.0.1:18765`。

当前尚未配置 Apple Developer ID、Windows 代码签名证书和 macOS notarization，因此安装包是未签名包。后续正式分发需要补签名与公证链路。

## 向量库环境

开发默认使用 Chroma：

```bash
VECTOR_STORE=chroma
CHROMA_PERSIST_DIR=./data/chroma
```

生产推荐使用 Qdrant：

```bash
VECTOR_STORE=qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_PREFIX=agent_demo
QDRANT_VECTOR_SIZE=768
```
