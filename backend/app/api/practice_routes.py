from fastapi import APIRouter

router = APIRouter(prefix="/api/practice", tags=["practice"])


@router.get("/ping")
def practice_ping() -> dict:
    return {"message": "practice module ready"}

