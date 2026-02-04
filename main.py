"""
DigiWood Blog Automation - FastAPI Backend
Gemini AI를 활용한 블로그 글 자동 생성 시스템
"""
import sys
import os
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
# 1. First try local .env in backend folder
# 2. Then try parent directory .env.local and .env
current_dir = Path(__file__).parent
parent_dir = current_dir.parent

load_dotenv(current_dir / ".env", override=True)
load_dotenv(parent_dir / ".env.local", override=False)
load_dotenv(parent_dir / ".env", override=False)

# Import routers
from routers import projects, photos, generate, settings

# Create FastAPI app
app = FastAPI(
    title="DigiWood Blog API",
    description="Gemini AI 기반 블로그 글 자동 생성 API",
    version="1.0.0",
)

# CORS 설정 (Next.js 프론트엔드 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://hr.digiwood.co.kr",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app|https://hr\.digiwood\.co\.kr",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router)
app.include_router(photos.router)
app.include_router(generate.router)
app.include_router(settings.router)


@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "status": "ok",
        "message": "DigiWood Blog API is running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
