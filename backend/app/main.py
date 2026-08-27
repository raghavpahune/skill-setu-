"""FastAPI application for SkillSetu backend."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load demo data if needed
    if settings.use_demo_data:
        from app.db import load_demo_data
        load_demo_data()
    yield


app = FastAPI(
    title="SkillSetu API",
    description="AI-Powered Labour-Market Intelligence & Curriculum-Alignment Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and mount routers
from app.routers import (
    skills, jobs, gaps, courses, signals, forecast,
    districts, student, copilot, employer, schemes, opportunities, sync,
)

app.include_router(skills.router, prefix="/api", tags=["Skills"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(gaps.router, prefix="/api", tags=["Skill Gaps"])
app.include_router(courses.router, prefix="/api", tags=["Courses"])
app.include_router(signals.router, prefix="/api", tags=["Industry Signals"])
app.include_router(forecast.router, prefix="/api", tags=["Forecast"])
app.include_router(districts.router, prefix="/api", tags=["Districts"])
app.include_router(student.router, prefix="/api", tags=["Student"])
app.include_router(copilot.router, prefix="/api", tags=["AI Copilot"])
app.include_router(employer.router, prefix="/api", tags=["Employer"])
app.include_router(schemes.router, prefix="/api", tags=["Schemes"])
app.include_router(opportunities.router, prefix="/api", tags=["Opportunities"])
app.include_router(sync.router, prefix="/api", tags=["Data Ingestion & Sync"])


@app.get("/api/health")
async def health():
    import os
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or settings.gemini_api_key
    return {
        "status": "ok",
        "demo_mode": settings.use_demo_data,
        "ai_available": bool(key and key.strip()),
    }


@app.get("/api/health/ai")
async def health_ai():
    """Safe diagnostic endpoint for AI provider status without exposing secrets."""
    from ai.gemini_provider import GeminiProvider
    provider = GeminiProvider()
    probe_result = await provider.diagnose()
    return probe_result
