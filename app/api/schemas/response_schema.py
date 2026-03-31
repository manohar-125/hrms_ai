from pydantic import BaseModel
from typing import Optional


class ChatResponse(BaseModel):
    answer: str
    source: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "The holiday policy allows for 12 paid holidays per year.",
                "source": "Source: Holiday_Policy"
            }
        }