from fastapi import FastAPI

app = FastAPI(
    title="Road2Hire API",
    description="Backend API for the Road2Hire career readiness platform.",
    version="0.1.0",
)


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