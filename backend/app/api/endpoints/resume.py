from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.resume import Resume

router = APIRouter()


@router.post("/resumeupload")
async def upload_resume(
    resume: UploadFile = File(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Leave room for multipart overhead under Vercel's 4.5 MB request limit.
    max_size = 4 * 1024 * 1024
    content = await resume.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="File too large, exceeds 4MB.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid file format, only pdfs")

    stored = db.get(Resume, user.id)
    if stored is None:
        db.add(Resume(user_id=user.id, content=content))
    else:
        stored.content = content
    db.commit()
    return {"resume path": f"database:resumes/{user.id}"}
