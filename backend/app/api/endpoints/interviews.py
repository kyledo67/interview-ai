from fastapi import APIRouter, Depends, status, Response, Request, HTTPException #type: ignore
from app.models.interview import Interview
from app.database import get_db
from app.models.user import User
from datetime import datetime, timedelta
from app.config import settings
from app.core.security import get_current_user
from sqlalchemy.orm import Session #type: ignore
from app.schemas.interview import InterviewCreate, InterviewEnd, InterviewSummary, InterviewSummaryLite
from app.models.interview import Interview
from pydantic import BaseModel #type: ignore
import os


router = APIRouter()

@router.post("/interviews/start")
def start_interview(interview_data: InterviewCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resumepath = f"uploads/resumes/{user.id}_resume.pdf"
    if not os.path.exists(resumepath):
        raise HTTPException(status_code=400, detail="resume not found")
    new_interview = Interview(user_id = user.id, start_time = datetime.now(), status = "active", resume_path = resumepath)
    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)
    return {"message": "Interview started", "interviewid": new_interview.id}

@router.post("/interviews/{id}/end")
def end_interview(id: int, interview_data: InterviewEnd, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview does not exist")
    transcript = [msg.dict() for msg in interview_data.transcript]
    interview.end_time = datetime.now()
    interview.status = "completed"
    new_transcript = [
        {
            "speaker": message.speaker,
            "message": message.message
        }
        for message in interview_data.transcript
    ]
    interview.transcript = new_transcript
    interview.scores = None
    db.commit()
    resume_path = interview.resume_path
    if resume_path and os.path.exists(resume_path):
        try:
            os.remove(resume_path)
        except Exception as e:
            print(f"Failed to delete resume: {e}")
    return {"message": "Interview ended"}

@router.get("/interviews/", response_model= list[InterviewSummaryLite])
def get_all_user_interviews(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interviews = db.query(Interview).filter(Interview.user_id == user.id).all()
    summary = []
    for interview in interviews:
        if interview.end_time is None:
            continue
        duration = int((interview.end_time - interview.start_time).total_seconds())
        summary.append(InterviewSummaryLite(
            duration = duration,
            interview_id = interview.id,
            scores = interview.scores,
            start_time = interview.start_time,
            end_time = interview.end_time
        ))
    return summary

@router.get("/interviews/{id}/", response_model= InterviewSummary)
def get_specific_user_interviews(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    specific_interview = db.query(Interview).filter(Interview.user_id == user.id, Interview.id == id).first()
    if not specific_interview:
        raise HTTPException(status_code=404, detail="Interview not found or access denied")
    return InterviewSummary(
        duration = int((specific_interview.end_time - specific_interview.start_time).total_seconds()),
        interview_id = id,
        scores = specific_interview.scores,
        start_time = specific_interview.start_time,
        end_time = specific_interview.end_time,
        transcript = specific_interview.transcript
    )

 
