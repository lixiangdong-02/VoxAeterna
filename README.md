# VoxAeterna

基于 GPT-SoVITS 的 AI 语音合成桌面应用。本地推理，无需联网。

## 技术栈

| 层 | 技术 |
|---|---|
| 桌面框架 | Electron + Vue 3 + TypeScript |
| 推理后端 | FastAPI + GPT-SoVITS v2Pro |
| 语音模型 | BERT + VITS + CNHuBERT |
| 云端服务 | FastAPI + SQLAlchemy（阿里云函数计算） |
| 数据库 | TiDB Cloud（MySQL 兼容） |
| 模型存储 | 魔搭社区（ModelScope） |

## 项目结构

```
VoiceStudio/
├── backend/          # 本地推理后端（FastAPI + GPT-SoVITS）
│   ├── app/
│   │   ├── api/      # REST API 路由
│   │   ├── services/ # 模型管理、推理、文件服务
│   │   └── config.py
│   └── inference/    # GPT-SoVITS 推理引擎
├── cloud/            # 云端服务（用户认证、订阅、支付）
│   ├── api/
│   └── services/
├── frontend/         # Electron + Vue 3 桌面端
│   ├── electron/     # 主进程（环境管理、后端管理）
│   └── src/          # 渲染进程（Vue 3 UI）
└── models/           # 模型权重（不上传 Git）
```

## 开发

```bash
# 后端虚拟环境
python -m venv venv
venv\Scripts\activate
pip install -r requirements-backend.txt

# 前端
cd frontend
npm install
npm run dev
```

## 打包

```bash
cd frontend
npm run build
# 输出: release/{version}/VoxAeterna-Windows-{version}-Setup.exe
```

## 发布

1. `VoxAeterna-Windows-x.x.x-Setup.exe` — 软件安装包
2. `python-runtime.zip` — Python 运行时（嵌入版 Python + 全部依赖）
3. 用户安装 exe 后将 zip 解压到安装目录 `python/` 下
4. 首次启动自动从魔搭社区下载语音模型

## License

MIT
