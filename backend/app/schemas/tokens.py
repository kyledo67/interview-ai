from pydantic import BaseModel #type: ignore

class Token(BaseModel):
    access_token: str
    token_type: str