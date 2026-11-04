from fastapi import APIRouter, Depends, status, Response, Request, HTTPException #type: ignore
from app.models.interview import Interview
from app.database import get_db
from app.models.user import User
from app.models.resume import Resume
from google.genai import types
from datetime import datetime, timedelta
from app.config import settings
from app.core.security import get_current_user
from sqlalchemy.orm import Session #type: ignore
from app.schemas.interview import (
    InterviewCreate, InterviewEnd, InterviewSummary, 
    InterviewSummaryLite, InterviewMessageRequest, 
    InterviewMessageResponse, CodeExecutionRequest, 
    CodeExecutionResponse
)
from app.api.endpoints.gemini import InterviewService
from pydantic import BaseModel #type: ignore
import os
import hashlib
from app.core.interview_policy import ensure_capacity, is_relevant, REDIRECT, LANGUAGES, bounded_history
from app.schemas.interview import CodeContext

router = APIRouter()


def get_interview_service(request: Request, user: User, db: Session):
    # Candidate context must survive cold starts without being shared across users.
    service = InterviewService(
        request.app.state.gemini_client, request.app.state.gemini_model
    )
    resume = db.get(Resume, user.id)
    if resume is not None:
        service.uploaded_resume_file = types.Part.from_bytes(
            data=resume.content, mime_type="application/pdf"
        )
    return service


def ground_service(service, interview, current_code=None, language_id=None):
    meta = interview.meta_info
    if current_code is not None:
        meta["current_code"] = current_code
    if language_id is not None:
        meta["language_id"] = language_id
    service.language = LANGUAGES.get(meta.get("language_id", 71), "Python")
    if meta.get("mode") in ("technical", "candidate_questions"):
        service.technical_context = {
            "problem": meta.get("technical_question"),
            "current_code": meta.get("current_code", ""),
            "last_execution": meta.get("last_execution"),
        }


@router.post("/interviews/start")
def start_interview(
    interview_data: InterviewCreate, 
    request: Request,
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    interview_service: InterviewService = get_interview_service(request, user, db)
    
    stored_resume = db.get(Resume, user.id)
    if stored_resume is None:
        raise HTTPException(status_code=400, detail="Resume not found. Please upload your resume first.")
    filepath = f"database:resumes/{user.id}"
    try:
        resume_data = interview_service.parse_resume_from_pdf(stored_resume.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")

    resume_data["level"] = "new_grad" if resume_data.get("level") == "new_grad" else "intern"

    # Generate first message
    first_message = interview_service.generate_initial_message(resume_data)
    
    # create interview record
    new_interview = Interview(
        user_id=user.id,
        start_time=datetime.now(),
        status="active",
        resume_path=filepath,
        transcript=[{
            "timestamp": datetime.now().isoformat(),
            "speaker": "AI",
            "message": first_message
        }],
        meta_info={
            "candidate_level": resume_data["level"],
            "is_non_traditional": resume_data.get("is_non_traditional", False),
            "background_context": resume_data.get("background_context", ""),
            "mode": "behavioral",
            "questions_asked": 1,
            "behavioral_start_time": datetime.now().isoformat(),
            "technical_start_time": None,
            "technical_question": None,
            "technical_problem_solved": False,
            "asked_candidate_questions": False
        }
    )
    
    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)
    
    return {
        "message": "Interview started",
        "interview_id": new_interview.id,
        "ai_message": first_message,
        "candidate_level": resume_data["level"],
        "is_non_traditional": resume_data.get("is_non_traditional", False),
        "background_context": resume_data.get("background_context", ""),
        "mode": "behavioral"
    }


@router.post("/interviews/{interview_id}/message")
def process_interview_message(
    interview_id: int,
    message_data: InterviewMessageRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    interview_service: InterviewService = get_interview_service(request, user, db)
    
 
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == user.id,
        Interview.status == "active"
    ).with_for_update().first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Active interview not found")
    
    ensure_capacity(interview, message_data.message)
    if not is_relevant(request.app.state.gemini_client, request.app.state.gemini_model,
                       message_data.message, interview.meta_info["mode"],
                       interview.meta_info.get("technical_question"), interview.transcript):
        return {"ai_response": REDIRECT, "should_switch_mode": False, "new_mode": None,
                "technical_data": None, "should_end_interview": False, "redirected": True}
    ground_service(interview_service, interview, message_data.current_code, message_data.language_id)

    interview.transcript.append({
        "timestamp": datetime.now().isoformat(),
        "speaker": "User",
        "message": message_data.message
    })
  
    resume_data = {
        "level": interview.meta_info["candidate_level"],
        "is_non_traditional": interview.meta_info.get("is_non_traditional", False),
        "background_context": interview.meta_info.get("background_context", "")
    }
    
    # calc behavioral duration
    behavioral_start = datetime.fromisoformat(interview.meta_info["behavioral_start_time"])
    behavioral_duration = (datetime.now() - behavioral_start).total_seconds() / 60
    
    # calc technical duration
    technical_duration = 0
    if interview.meta_info.get("technical_start_time"):
        technical_start = datetime.fromisoformat(interview.meta_info["technical_start_time"])
        technical_duration = (datetime.now() - technical_start).total_seconds() / 60
    
   
    result = interview_service.process_message(
        user_message=message_data.message,
        resume_data=resume_data,
        questions_asked=interview.meta_info["questions_asked"],
        behavioral_duration_minutes=behavioral_duration,
        technical_duration_minutes=technical_duration,
        current_code=message_data.current_code or "",
        mode=interview.meta_info["mode"],
        technical_problem_solved=interview.meta_info.get("technical_problem_solved", False),
        asked_candidate_questions=interview.meta_info.get("asked_candidate_questions", False),
        transcript=interview.transcript,
    )
    
    
    interview.transcript.append({
        "timestamp": datetime.now().isoformat(),
        "speaker": "AI",
        "message": result["ai_response"]
    })
    
    # Update interview state based on mode switches
    if result["should_switch_mode"]:
        if result["new_mode"] == "technical":
            interview.meta_info["mode"] = "technical"
            interview.meta_info["technical_question"] = result["technical_data"]
            interview.meta_info["technical_start_time"] = datetime.now().isoformat()
        elif result["new_mode"] == "candidate_questions":
            interview.meta_info["mode"] = "candidate_questions"
            interview.meta_info["asked_candidate_questions"] = True
    else:
        # Increment question count only in behavioral mode
        if interview.meta_info["mode"] == "behavioral":
            interview.meta_info["questions_asked"] += 1
    
    db.commit()
    
    return {
        "ai_response": result["ai_response"],
        "should_switch_mode": result["should_switch_mode"],
        "new_mode": result["new_mode"],
        "technical_data": result.get("technical_data"),
        "should_end_interview": result.get("should_end_interview", False)
    }


@router.post("/interviews/{interview_id}/execute-code")
def execute_code_feedback(
    interview_id: int,
    request: Request,
    execution_data: CodeExecutionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process code execution results and provide AI feedback
    """
    interview_service: InterviewService = get_interview_service(request, user, db)
    
    
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == user.id,
        Interview.status == "active"
    ).with_for_update().first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Active interview not found")
    
    technical_duration = 0
    if interview.meta_info.get("technical_start_time"):
        technical_start = datetime.fromisoformat(interview.meta_info["technical_start_time"])
        technical_duration = (datetime.now() - technical_start).total_seconds() / 60
    
    run = interview.meta_info.get("last_execution", {})
    if run.get("code_hash") != hashlib.sha256(execution_data.code.encode()).hexdigest():
        raise HTTPException(status_code=400, detail="Run this code before requesting feedback.")
    execution_data.output = run["output"]
    execution_data.status = run["status"]
    execution_summary = f"Code Execution - Status: {execution_data.status}\nOutput: {execution_data.output}"[:4000]
    ensure_capacity(interview, execution_summary)
    ground_service(interview_service, interview, execution_data.code, run.get("language_id", 71))

    result = interview_service.process_code_execution(
        code=execution_data.code,
        output=execution_data.output,
        status=execution_data.status,
        candidate_level=interview.meta_info["candidate_level"],
        technical_duration_minutes=technical_duration,
        transcript = interview.transcript,
    )
    
   
    interview.transcript.append({
        "timestamp": datetime.now().isoformat(),
        "speaker": "System",
        "message": execution_summary
    })
    
    interview.transcript.append({
        "timestamp": datetime.now().isoformat(),
        "speaker": "AI",
        "message": result["feedback"]
    })
    
    result["problem_solved"] = interview.meta_info.get("technical_problem_solved", False)
    
    db.commit()
    
    return {
        "feedback": result["feedback"],
        "execution_status": execution_data.status,
        "problem_solved": result.get("problem_solved", False)
    }


@router.post("/interviews/{id}/end")
def end_interview(
    id: int, 
    request: Request,
    interview_data: InterviewEnd, 
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    End interview and generate evaluation scores
    """
    interview_service: InterviewService = get_interview_service(request, user, db)
    
 
    interview = db.query(Interview).filter(
        Interview.id == id,
        Interview.user_id == user.id
    ).with_for_update().first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview does not exist")
    
   
    # The browser transcript is display data, not an authoritative conversation.
    # Never allow clients to insert fake AI/System turns into evaluation.
    ground_service(interview_service, interview, interview_data.final_code)

    # Generate evaluation
    final_code = interview_data.final_code or ""
    meta_info = interview.meta_info or {}
    technical_question_data = meta_info.get("technical_question", {})
    technical_question = technical_question_data.get("title", "Unknown") if isinstance(technical_question_data, dict) else "Unknown"
    candidate_level = meta_info.get("candidate_level", "Unknown")
    
    # Calculate technical duration
    technical_duration = 0
    if meta_info.get("technical_start_time"):
        technical_start = datetime.fromisoformat(meta_info["technical_start_time"])
        technical_end = datetime.now()
        technical_duration = (technical_end - technical_start).total_seconds() / 60
    
    evaluation = interview_service.generate_evaluation(
        transcript=bounded_history(interview.transcript),
        final_code=final_code,
        candidate_level=candidate_level,
        technical_question_title=technical_question,
        technical_duration_minutes=technical_duration
    )
    
    # Update interview status
    interview.end_time = datetime.now()
    interview.status = "completed"
    interview.scores = evaluation
    
    db.commit()
    
    stored_resume = db.get(Resume, user.id)
    if stored_resume is not None:
        db.delete(stored_resume)
        db.commit()

    return {
        "message": "Interview ended",
        "evaluation": evaluation
    }


@router.get("/interviews/", response_model=list[InterviewSummaryLite])
def get_all_user_interviews(
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Get all interviews for current user
    """
    interviews = db.query(Interview).filter(Interview.user_id == user.id).all()
    summary = []
    
    for interview in interviews:
        if interview.end_time is None:
            continue
        
        duration = int((interview.end_time - interview.start_time).total_seconds())
        summary.append(InterviewSummaryLite(
            duration=duration,
            interview_id=interview.id,
            scores=interview.scores,
            start_time=interview.start_time,
            end_time=interview.end_time
        ))
    
    return summary


@router.get("/interviews/{id}/", response_model=InterviewSummary)
def get_specific_user_interviews(
    id: int, 
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    specific_interview = db.query(Interview).filter(
        Interview.user_id == user.id, 
        Interview.id == id
    ).with_for_update().first()
    
    if not specific_interview:
        raise HTTPException(status_code=404, detail="Interview not found or access denied")
    
    return InterviewSummary(
        duration=int((specific_interview.end_time - specific_interview.start_time).total_seconds()),
        interview_id=id,
        scores=specific_interview.scores,
        start_time=specific_interview.start_time,
        end_time=specific_interview.end_time,
        transcript=specific_interview.transcript
    )

@router.get("/interviews/{interview_id}/get-technical-problem")
def get_technical_problem(
    interview_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == user.id,
        Interview.status == "active"
    ).with_for_update().first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Active interview not found")
    

    if interview.meta_info.get("mode") != "technical":
        raise HTTPException(status_code=400, detail="Interview is not in technical phase")
    

    technical_question = interview.meta_info.get("technical_question")
    
    if not technical_question:
        raise HTTPException(status_code=404, detail="No technical problem found")
    
    return {
        "technical_data": technical_question,
        "candidate_level": interview.meta_info.get("candidate_level", "intern")
    }


@router.post("/interviews/{interview_id}/phase")
def advance_phase(interview_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(
        Interview.id == interview_id, Interview.user_id == user.id, Interview.status == "active"
    ).with_for_update().first()
    if interview is None:
        raise HTTPException(status_code=404, detail="Active interview not found")
    meta = interview.meta_info
    elapsed = (datetime.now() - datetime.fromisoformat(meta["behavioral_start_time"])).total_seconds() / 60
    changed = False
    message = None
    if meta["mode"] == "behavioral" and elapsed >= 15:
        meta["mode"] = "technical"
        meta["technical_question"] = InterviewService(None, "")._generate_technical_question(meta["candidate_level"])
        meta["technical_start_time"] = datetime.now().isoformat()
        changed = True
        message = "Let's move on to the technical coding portion. Your problem is now on screen."
    elif meta["mode"] == "technical":
        elapsed = (datetime.now() - datetime.fromisoformat(meta["technical_start_time"])).total_seconds() / 60
        if meta.get("technical_problem_solved") or elapsed >= 45:
            meta["mode"] = "candidate_questions"
            meta["asked_candidate_questions"] = True
            changed = True
            message = "That completes the technical portion. What questions do you have for me?"
    if changed:
        ensure_capacity(interview, message, entries=1)
        interview.transcript.append({"speaker": "AI", "message": message, "timestamp": datetime.now().isoformat()})
        db.commit()
    return {"mode": meta["mode"], "changed": changed, "ai_response": message,
            "technical_data": meta.get("technical_question")}


@router.put("/interviews/{interview_id}/context")
def update_code_context(interview_id: int, data: CodeContext,
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == interview_id,
        Interview.user_id == user.id, Interview.status == "active").with_for_update().first()
    if interview is None:
        raise HTTPException(status_code=404, detail="Active interview not found")
    if interview.meta_info.get("mode") != "technical":
        raise HTTPException(status_code=409, detail="Interview is not in technical phase")
    interview.meta_info["current_code"] = data.current_code
    interview.meta_info["language_id"] = data.language_id
    db.commit()
    return {"updated": True}
