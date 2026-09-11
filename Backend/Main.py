from fastapi import FastAPI
from sqlalchemy import text

from Core.database import engine

from Core.database import Base, engine
from Models import User

from Api.auth import router as auth_router

app = FastAPI(
    title="Road2Hire API",
    description="Backend API for the Road2Hire career readiness platform.",
    version="0.1.0",
)

app.include_router(auth_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to Road2Hire API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }

@app.get("/db-test")  # NEW
def test_database():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception as e:
        return {"database": "failed", "error": str(e)}