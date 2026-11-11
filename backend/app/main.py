"""SCAMTRACE AI FastAPI Application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.cases import router as cases_router
from backend.app.api.evidence import router as evidence_router
from backend.app.api.graph import router as graph_router
from backend.app.api.integrity import router as integrity_router
from backend.app.api.report import router as report_router
from backend.app.api.risk import router as risk_router
from backend.app.api.timeline import router as timeline_router
from backend.app.db.session import init_db

app = FastAPI(
    title="SCAMTRACE AI",
    description="Explainable Multimodal Digital Forensics & Cybercrime Investigation System",
    version="0.1.0",
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers under /api
app.include_router(cases_router, prefix="/api")
app.include_router(evidence_router, prefix="/api")
app.include_router(integrity_router, prefix="/api")
app.include_router(graph_router, prefix="/api")
app.include_router(timeline_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(report_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    """Initialize database tables on application start."""
    init_db()


@app.get("/api/health")
def health_check():
    """System health check endpoint."""
    return {"status": "ok", "service": "scamtrace-ai", "version": "0.1.0"}
