from fastapi import FastAPI # type: ignore
from app.api.endpoints import auth
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from app.database import engine, Base
from app.models import user, token
from app.api.endpoints import interviews, code, resume, tts
from fastapi.staticfiles import StaticFiles # type: ignore
from google import genai
from dotenv import load_dotenv #type: ignore 
from app.api.endpoints.gemini import InterviewService 
import os

load_dotenv()

Base.metadata.create_all(bind=engine)
app = FastAPI()


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model_name = "gemini-2.5-flash-lite"

app.state.interview_service = InterviewService(client, model_name)

origins = [
    "http://localhost:3000",
    "http://localhost:8001",
    "http://localhost:8000",
    "https://interview-ai-crdv.onrender.com/",
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
app.include_router(code.router, prefix="/code", tags=["code"])
app.include_router(tts.router, tags=["tts"])

app.mount("/", StaticFiles(directory="../frontend/build", html=True), name="static")