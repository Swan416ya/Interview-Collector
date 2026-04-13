# Interview Collector

Monorepo for interview question collection and training.

## Swagger / API Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Structure

- `backend`: FastAPI service
- `frontend`: Vue3 + Vite app
- `docs`: design docs

## 本地启动（前后端）

日常开发需要**两个终端**，分别跑后端和前端。下面假设你已完成本节下方 **Quick Start** 里的一次性配置（虚拟环境、依赖、`backend/.env`、数据库迁移等）。

| 服务 | 工作目录 | 说明 |
|------|-----------|------|
| 后端 API | `backend` | FastAPI，默认 `8000` 端口 |
| 前端 | `frontend` | Vite 开发服务器，默认多为 `5173` |

### 终端 1：启动后端

**PowerShell**（仓库根目录换为你本机路径）：

```powershell
cd "你的路径\Interview-Collector\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**cmd.exe** 下激活虚拟环境请用：

```bat
cd /d "你的路径\Interview-Collector\backend"
.\.venv\Scripts\activate.bat
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 终端 2：启动前端

```bash
cd frontend
npm run dev
```

（若尚未安装依赖，先在 `frontend` 目录执行一次 `npm install`。）

### 终端 3（可选）：启动 Flutter Android 客户端

```bash
cd flutterend
flutter pub get
flutter run -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

- `flutterend` 使用 Material 3 原生组件。
- Android 模拟器访问宿主机后端请使用 `10.0.2.2`，不要用 `localhost`。
- 若用真机调试，请把 `API_BASE_URL` 改成你电脑在局域网的 IP，例如 `http://192.168.1.10:8000`。

### 仅用浏览器调试 Flutter（推荐联调样式时使用）

```bash
cd flutterend
flutter pub get
flutter run -d chrome --web-hostname localhost --web-port 7357 --dart-define=API_BASE_URL=http://localhost:8000
```

- 打开后会自动在浏览器访问 Flutter Web。
- 若你只想固定本地 URL 供反复刷新，也可以改用：

```bash
flutter run -d web-server --web-hostname localhost --web-port 7357 --dart-define=API_BASE_URL=http://localhost:8000
```

### 打开与验证

- 前端：<http://localhost:5173>（具体端口以 Vite 终端输出为准）
- 后端健康检查：<http://127.0.0.1:8000/health>
- Swagger：<http://127.0.0.1:8000/docs>

前端默认通过环境变量 `VITE_API_BASE_URL` 请求后端，未设置时等同于 `http://localhost:8000`，与上述后端端口一致即可。

在对应终端按 `Ctrl+C` 停止该服务。请保证 MySQL（若使用）已启动，且 `backend/.env` 里 `DATABASE_URL` 等信息正确，否则后端无法正常工作。

连接 **MySQL 8**（默认 `caching_sha2_password`）时，PyMySQL 需要 **`cryptography`**，已在 `backend/requirements.txt` 中声明；若仍报错，在 `backend` 目录执行 `pip install -r requirements.txt` 或 `pip install cryptography`。

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### Database Migration (Alembic)

1. 先在 MySQL 里创建数据库（只建库，不用建表）：

```sql
CREATE DATABASE interviewCollector CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 生成并执行迁移：

```bash
cd backend
.\.venv\Scripts\activate
alembic revision --autogenerate -m "init tables"
alembic upgrade head
```

3. 启动后端（命令与本文「本地启动（前后端）」一节中终端 1 相同）：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Verify

- 后端：<http://127.0.0.1:8000/health>、<http://127.0.0.1:8000/docs>
- 前端：<http://localhost:5173>（端口以 Vite 为准）

## Current Baseline

- Backend
  - `GET /health`
  - `GET /api/questions`
  - `POST /api/questions`
  - `POST /api/questions/backfill-reference-answers`
  - `GET /api/practice/ping`
  - `GET /api/practice/categories`
  - `POST /api/practice/sessions/start` (supports category filter)
  - `POST /api/practice/sessions/start/custom` (for memorize->quiz flow)
  - `POST /api/practice/sessions/{session_id}/submit`
  - `POST /api/practice/sessions/{session_id}/skip` (no answer -> auto 0)
  - `GET /api/practice/sessions/{session_id}/summary`
  - `GET /api/practice/sessions`
  - `GET /api/practice/sessions/{session_id}/records`
- Frontend
  - Home / Questions / Practice / Practice History pages
  - Questions page supports filter/sort/CRUD and reference-answer detail
- Database
  - MySQL + Alembic migration initialized
  - Existing tables include: `questions`, `practice_records`, `practice_sessions`, `alembic_version`

## Roadmap (Planned)

- AI import
  - `POST /api/import/preview`
  - `POST /api/import/commit`
  - Source text -> structured JSON -> dedupe -> persist
- Practice flow
  - Session creation
  - Draw question by filters
  - Submit answer and score
- AI grading
  - Structured rubric scoring
  - Wrongbook auto update
  - Mastery score update
- Progress dashboard
  - Overall progress
  - Category progress
  - Weak area insights

## Deployment

### Option A: Local (current)

- Backend: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`（步骤见本文「本地启动（前后端）」）
- Frontend: 在 `frontend` 目录 `npm run dev`
- Flutter Android 客户端: 在 `flutterend` 目录 `flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000`
- DB: Local MySQL `interviewCollector`

### Flutter Android APK 打包与分发

1. 进入 Flutter 客户端目录并构建 release APK：

```bash
cd flutterend
flutter build apk --release --dart-define=API_BASE_URL=https://your-api-domain
```

2. 构建产物位置：

- `flutterend/build/app/outputs/flutter-apk/app-release.apk`

3. 分发方式（调试阶段可先用第 1 种）：

- 通过企业 IM（钉钉/飞书/企业微信）直接发送 APK 给测试同学安装。
- 上传到网盘并分享下载链接（建议加版本号命名，如 `interview-collector-v1.0.0.apk`）。
- 若团队需要更规范的内测分发，可接入 Firebase App Distribution 或蒲公英。

4. 首次安装提示：

- Android 设备需允许“安装未知来源应用”。
- 若后端还在本地网络，测试设备必须与开发机处于同一局域网并可访问 `API_BASE_URL`。

### Option B: Production (recommended)

- Backend: Docker image + Gunicorn/Uvicorn workers
- Frontend: `npm run build` static files via Nginx
- Database: managed MySQL
- Environment
  - `DATABASE_URL`
  - `AI_BASE_URL`
  - `AI_MODEL`
  - `AI_API_KEY`
  - `CORS_ORIGINS`

## Dedicated API Document

- Primary API doc file: `docs/api-reference.md`
- Rule: every backend API change must update this file in the same commit

## Doubao (Volcengine Ark) Integration Notes

- Current project env already switched to Ark-compatible defaults:
  - `AI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3`
  - `AI_MODEL=your_ark_endpoint_id`
- In Ark console, use your endpoint/model deployment id to replace `AI_MODEL`.
- Detailed integration and prompt templates: `docs/ai-doubao-integration.md`
