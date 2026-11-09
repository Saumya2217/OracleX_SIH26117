from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.core.seed_data import seed_database
from app.services.readiness import collect_readiness
from app.services.vector_store import VectorStoreUnavailable

# Import all API routers
from app.api.auth import router as auth_router
from app.api.company import router as company_router
from app.api.users import router as users_router
from app.api.knowledge import router as knowledge_router
from app.api.agents import router as agents_router
from app.api.workflows import router as workflows_router
from app.api.audit import router as audit_router
from app.api.adaptation import router as adaptation_router
from app.api.conversations import router as conversations_router
from app.api.requests import router as requests_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DEMO_MODE and settings.DEMO_SEED_ON_STARTUP and not settings.TESTING:
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    yield

app = FastAPI(
    title="OracleX",
    description="Private company document workspace with evidence-backed assistance.",
    version=settings.VERSION,
    lifespan=lifespan
)


@app.exception_handler(VectorStoreUnavailable)
async def vector_store_unavailable(_request, _error):
    return JSONResponse(status_code=503, content={"detail": "Document search is temporarily unavailable. Please retry."})

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(company_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)
app.include_router(knowledge_router, prefix=settings.API_V1_PREFIX)
app.include_router(agents_router, prefix=settings.API_V1_PREFIX)
app.include_router(workflows_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_router, prefix=settings.API_V1_PREFIX)
app.include_router(adaptation_router, prefix=settings.API_V1_PREFIX)
app.include_router(conversations_router, prefix=settings.API_V1_PREFIX)
app.include_router(requests_router, prefix=settings.API_V1_PREFIX)

@app.get("/health/live")
@app.get("/health")
def health_check():
    return {
        "status": "live",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    payload, status_code = await collect_readiness(db)
    return JSONResponse(content=payload, status_code=status_code)

@app.get("/")
def root():
    return {
        "message": "OracleX API",
        "docs": "/docs",
        "api": settings.API_V1_PREFIX
    }
