from fastapi import APIRouter, Depends, status, Response, Request, HTTPException #type: ignore
from app.models.interview import Interview
from app.database import get_db
from app.models.user import User
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

router = APIRouter()


@router.post("/interviews/start")
def start_interview(
    interview_data: InterviewCreate, 
    request: Request,
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    interview_service: InterviewService = request.app.state.interview_service
    
    # get resume path and send to Gemini for analysis
    upload_dir = "uploads/resumes"
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{user.id}_resume.pdf"
    filepath = os.path.join(upload_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=400, detail="Resume not found. Please upload your resume first.")
    
    try:
        resume_data = interview_service.parse_resume_from_pdf(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")
    
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
            "questions_asked": 0,  # ← Changed from 1 to 0
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
    interview_service: InterviewService = request.app.state.interview_service
    

    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == user.id,
        Interview.status == "active"
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Active interview not found")
    
    
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
        asked_candidate_questions=interview.meta_info.get("asked_candidate_questions", False)
    )
    
    # Add AI response to transcript
    interview.transcript.append({
        "timestamp": datetime.now().isoformat(),
        "speaker": "AI",
        "message": result["ai_response"]
    })
    
    
    if result["should_switch_mode"]:
        if result["new_mode"] == "technical":
            interview.meta_info["mode"] = "technical"
            interview.meta_info["technical_question"] = result["technical_data"]
            interview.meta_info["technical_start_time"] = datetime.now().isoformat()
        elif result["new_mode"] == "candidate_questions":
            interview.meta_info["mode"] = "candidate_questions"
            interview.meta_info["asked_candidate_questions"] = True
    else:
        # Increment question count only in behavioral mode AND only if not a greeting response
        if interview.meta_info["mode"] == "behavioral":
            # Only increment if we've moved past the greeting (questions_asked >= 1)
            # OR if the user's message was substantial (not just "good"/"fine")
            user_msg_lower = message_data.message.lower().strip()
            greeting_responses = [
                'good', 'fine', 'great', 'ok', 'okay', 'alright', 'well',
                'bad', 'not good', 'terrible', 'rough', 'stressful', 'not great',
                'im good', "i'm good", 'im fine', "i'm fine", 'pretty good', 'not bad'
            ]
            
            is_greeting_response = (
                interview.meta_info["questions_asked"] == 0 and
                len(message_data.message.split()) <= 5 and
                any(phrase in user_msg_lower for phrase in greeting_responses)
            )
            
      
            if not is_greeting_response:
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
    interview_service: InterviewService = request.app.state.interview_service
    
    # Get interview
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == user.id,
        Interview.status == "active"
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Active interview not found")
    
    # Calculate technical duration
    technical_duration = 0
    if interview.meta_info.get("technical_start_time"):
        technical_start = datetime.fromisoformat(interview.meta_info["technical_start_time"])
        technical_duration = (datetime.now() - technical_start).total_seconds() / 60
    
    # Get AI feedback on code execution
    result = interview_service.process_code_execution(
        code=execution_data.code,
        output=execution_data.output,
        status=execution_data.status,
        candidate_level=interview.meta_info["candidate_level"],
        technical_duration_minutes=technical_duration
    )
    
    # Add execution to transcript
    interview.transcript.append({
        "timestamp": datetime.now().isoformat(),
        "speaker": "System",
        "message": f"Code Execution - Status: {execution_data.status}\nOutput: {execution_data.output}"
    })
    
    interview.transcript.append({
        "timestamp": datetime.now().isoformat(),
        "speaker": "AI",
        "message": result["feedback"]
    })
    
    # Update problem solved status
    if result.get("problem_solved"):
        interview.meta_info["technical_problem_solved"] = True
    
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
    interview_service: InterviewService = request.app.state.interview_service
    
    # Get interview
    interview = db.query(Interview).filter(
        Interview.id == id,
        Interview.user_id == user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview does not exist")
    
    # Update transcript with any new messages from frontend
    new_transcript = [
        {
            "speaker": message.speaker,
            "message": message.message,
            "timestamp": message.timestamp.isoformat()
        }
        for message in interview_data.transcript
    ]
    
    interview.transcript = new_transcript
    
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
        transcript=interview.transcript,
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
    
    # Delete resume file
    filepath = interview.resume_path
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Failed to delete resume: {e}")
    
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
    """
    Get specific interview details
    """
    specific_interview = db.query(Interview).filter(
        Interview.user_id == user.id, 
        Interview.id == id
    ).first()
    
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