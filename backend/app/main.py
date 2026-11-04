from fastapi import FastAPI # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from app.database import engine, Base
from app.models import user, token, interview, resume as resume_model
from app.api.endpoints import interviews, code, resume, tts, auth
from fastapi.staticfiles import StaticFiles # type: ignore
from google import genai
from pathlib import Path
from dotenv import load_dotenv #type: ignore 
import os

load_dotenv()

Base.metadata.create_all(bind=engine)
app = FastAPI()


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model_name = "gemini-2.5-flash-lite"

app.state.gemini_client = client
app.state.gemini_model = model_name

origins = [
    "http://localhost:3000",
    "http://localhost:8001",
    *[origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()],
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth.router)  
app.include_router(resume.router)
app.include_router(interviews.router)
app.include_router(code.router, tags=["code"])
app.include_router(tts.router, tags=["tts"])

@app.get("/health")
def health():
    return {"status": "ok"}


# Vercel serves the React build from its CDN; Docker serves it through FastAPI.
frontend_build = Path(__file__).resolve().parents[2] / "frontend" / "build"
if not os.getenv("VERCEL") and frontend_build.is_dir():
    app.mount("/", StaticFiles(directory=frontend_build, html=True), name="static")