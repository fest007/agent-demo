# Release

本项目的发布链路支持两种入口：修改 `VERSION` 后推送到 `main`，或推送 `vX.Y.Z` tag。GitHub Actions 会自动构建并上传到 GitHub Releases。

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

- `agent-demo-web/dist`：Web 前端构建产物
- `agent-demo-server`：FastAPI 服务源码与依赖声明
- `agent-demo-agent`：Agent 核心源码与依赖声明
- `scripts`、`STARTUP.md`、`docker-compose.yml`：启动脚本与部署说明

当前仓库还没有 Electron/Tauri 桌面壳，所以 Release 产物是三项目可部署包；后续加入桌面端时，可在同一个 workflow 中追加 `.exe`、`.dmg` 构建步骤。

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
