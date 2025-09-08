from fastapi import APIRouter, Depends #type: ignore
import httpx #type: ignore
import os
from pydantic import BaseModel #type: ignore

router = APIRouter()

JUDGE0_URL = os.getenv("JUDGE0_URL", "https://judge0-ce.p.rapidapi.com/submissions")
JUDGE0_API_KEY = os.getenv("JUDGE0_API_KEY")

headers = {
    "Content-Type": "application/json",
    "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
    "X-RapidAPI-Key": JUDGE0_API_KEY
    }

class request(BaseModel):
    source_code: str
    language_id: int
    stdin: str = ""

@router.post("/execute")
async def executecode(request: request):
    async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{JUDGE0_URL}?base64_encoded=false&wait=true",
                headers=headers,
                json={
                    "source_code": request.source_code,
                    "language_id": request.language_id,
                    "stdin": request.stdin
                }
        )
            return response.json()
        


        
        