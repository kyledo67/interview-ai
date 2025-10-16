from fastapi import APIRouter, HTTPException, Depends #type: ignore
from fastapi.responses import Response #type: ignore
from pydantic import BaseModel #type: ignore
from typing import List, Optional
import requests #type: ignore
import os
from dotenv import load_dotenv #type: ignore 
from app.core.security import get_current_user
from app.models.user import User

load_dotenv()

router = APIRouter()


VOGENT_API_URL = "https://api.vogent.ai/api/tts"
VOGENT_API_KEY = os.getenv("VOGENT_API_KEY")


class VoiceOption(BaseModel):
    optionId: str
    value: str


class AudioFormat(BaseModel):
    outputType: str = "WAV_PCM16"
    sampleRate: int = 24000


class TTSRequest(BaseModel):
    text: str
    voiceId: Optional[str] = "default"
    voiceOptionValues: Optional[List[VoiceOption]] = []
    format: Optional[AudioFormat] = AudioFormat()


@router.post("/tts")
async def text_to_speech(
    tts_request: TTSRequest,
    user: User = Depends(get_current_user)
):
    
    
    if not VOGENT_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="no api key"
        )
    
    
    headers = {
        "Authorization": f"Bearer {VOGENT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    
    payload = {
        "text": tts_request.text,
        "voiceId": tts_request.voiceId,
        "voiceOptionValues": [
            {"optionId": opt.optionId, "value": opt.value} 
            for opt in tts_request.voiceOptionValues
        ] if tts_request.voiceOptionValues else [],
        "format": {
            "outputType": tts_request.format.outputType,
            "sampleRate": tts_request.format.sampleRate
        }
    }
    
    try:
        response = requests.post(
            VOGENT_API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        
        if response.status_code == 200:
            # Determine content type based on format
            content_type = "audio/wav" if tts_request.format.outputType == "WAV_PCM16" else "audio/mpeg"
            
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename=speech.{tts_request.format.outputType.lower()}"
                }
            )
        else:
            error_detail = response.text
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Vogent API error: {error_detail}"
            )
            
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Request to Vogent API timed out"
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Vogent API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"error: {str(e)}"
        )