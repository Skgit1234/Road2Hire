from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from Models import LearningTask, Resume, SkillGap, User

from Api.auth import router as auth_router
from Api.profile import router as profile_router
from Api.resume import router as resume_router, resumes_router
from Api.skill_gaps import router as skill_gaps_router
from Api.career_insights import router as career_insights_router
from Api.tasks import router as tasks_router
from Api.dashboard import router as dashboard_router
from Api.jobs import router as jobs_router
from Api.assistant import router as assistant_router

app = FastAPI(
    title="Road2Hire API",
    description="Backend API for the Road2Hire career readiness platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(resume_router)
app.include_router(resumes_router)
app.include_router(skill_gaps_router)
app.include_router(career_insights_router)
app.include_router(tasks_router)
app.include_router(dashboard_router)
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
