"""ORCA — Marine Ecosystem Reasoning with Collaborative Agents
FastAPI Backend Application Entry Point
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("orca.main")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("==================================================")
    logger.info("ORCA Marine Intelligence Backend Starting...")
    logger.info(f"Target Prototype Sector: Kochi, Kerala (Arabian Sea)")
    logger.info(f"Adapter Mode: DEMONSTRATION / MOCK ADAPTERS ENABLED")
    logger.info("==================================================")
    yield
    logger.info("ORCA Marine Intelligence Backend Shutting down...")

app = FastAPI(
    title="ORCA — Marine Ecosystem Intelligence API",
    description="Agentic AI-powered conversational marine intelligence platform for coastal safety & fisheries",
    version="0.1.0",
    lifespan=lifespan
)

# CORS Configuration
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
origins.extend(["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5174", "*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Welcome to ORCA Marine Ecosystem Intelligence API",
        "health": "/api/health",
        "chat": "/api/chat",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
