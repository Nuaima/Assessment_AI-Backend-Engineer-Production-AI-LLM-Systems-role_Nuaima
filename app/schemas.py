from pydantic import BaseModel


class Segment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None = None
    duration: float | None = None
    segments: list[Segment]
