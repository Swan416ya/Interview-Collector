from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.import_routes import router as import_router
from app.api.practice_routes import router as practice_router
from app.api.question_routes import router as question_router
from app.api.taxonomy_routes import router as taxonomy_router
from app.core.config import settings
from app.core.database import Base, engine
from app.models import Category, Company, Question, QuestionCompany, QuestionRole, Role  # noqa: F401

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    # Keep this for local bootstrap. In production, prefer Alembic migrations.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


app.include_router(question_router)
app.include_router(practice_router)
app.include_router(taxonomy_router)
app.include_router(import_router)

