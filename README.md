# Interview Collector

Monorepo for interview question collection and training.

## Structure

- `backend`: FastAPI service
- `frontend`: Vue3 + Vite app
- `docs`: design docs

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

