from fastapi import FastAPI
from sqlalchemy import text

from Core.database import engine

from Core.database import Base, engine
from Models import Resume, User

from Api.auth import router as auth_router
from Api.resume import router as resume_router, resumes_router
from Api.profile import router as profile_router
from Api.skill_gaps import router as skill_gaps_router
from Api.dashboard import router as dashboard_router
from Api.career_insights import router as career_insights_router
from Api.tasks import router as tasks_router
from Api.jobs import router as jobs_router
from Api.assistant import router as assistant_router

app = FastAPI(
    title="Road2Hire API",
    description="Backend API for the Road2Hire career readiness platform.",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(resume_router)
app.include_router(resumes_router)
app.include_router(profile_router)
app.include_router(skill_gaps_router)
app.include_router(dashboard_router)
app.include_router(career_insights_router)
app.include_router(tasks_router)
app.include_router(jobs_router)
app.include_router(assistant_router)

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