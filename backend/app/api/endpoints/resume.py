from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File # type: ignore
from sqlalchemy.orm import Session # type: ignore
from app.models.user import User
from app.models.token import RefreshToken
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.database import get_db
from app.core.security import get_current_user
from datetime import datetime, timedelta
from app.config import settings
from fastapi import Response, Request #type: ignore
import shutil
import os
import asyncio

router = APIRouter()

@router.post("/resumeupload")
async def upload_resume(resume: UploadFile = File(), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    #js checks if directory exists, makes on if doesn't
    maxfilesize = 5 * 1024 * 1024 #5mb
    upload_dir = "uploads/resumes"
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{user.id}_resume.pdf"
    filepath = os.path.join(upload_dir, filename)

    x = await resume.read(5)
    if not x.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid file format, only pdfs")
    total = 0
    with open(filepath, "wb") as f:
        while chunk := await resume.read(1024*1024):
            total += len(chunk)
            if total > maxfilesize:
                raise HTTPException(status_code=413, detail="File too large, exceeds 5MB.")
            f.write(chunk)


    return {"resume path": filepath}
