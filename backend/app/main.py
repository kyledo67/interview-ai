from fastapi import FastAPI # type: ignore
from app.api.endpoints import auth
from fastapi.middleware.cors import CORSMiddleware #type: ignore
from app.database import engine, Base
from app.models import user, token
from app.api.endpoints import interviews, code, resume
from fastapi.staticfiles import StaticFiles #type: ignore

Base.metadata.create_all(bind=engine)
app = FastAPI()



origins = [
    "http://localhost:3000" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def read_root():
    return {"message": "hi"}

app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(interviews.router)
app.include_router(code.router, prefix="/code", tags=["code"])

app.mount("/", StaticFiles(directory="../frontend/build/", html=True), name="static")
