from pathlib import Path
import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.audio import normalize_audio, validate_audio_file
from app.schemas import TranscriptionResponse
from app.transcriber import Transcriber

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
CHUNK_SIZE = 1024 * 1024
FRONTEND_PATH = Path(__file__).parent / "static" / "index.html"

app = FastAPI(
    title="Audio Transcription Service",
    version="1.0.0",
    description="Upload audio and receive timestamped speech-to-text transcription.",
)

_transcriber: Transcriber | None = None


def get_transcriber() -> Transcriber:
    global _transcriber
    if _transcriber is None:
        _transcriber = Transcriber()
    return _transcriber


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(FRONTEND_PATH)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...)) -> TranscriptionResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    try:
        validate_audio_file(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    suffix = Path(file.filename).suffix.lower()

    with tempfile.TemporaryDirectory() as temp_dir:
        original_path = str(Path(temp_dir) / f"input{suffix}")

        total_bytes = 0
        with open(original_path, "wb") as destination:
            while chunk := await file.read(CHUNK_SIZE):
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_MB * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds {MAX_UPLOAD_MB} MB upload limit.",
                    )
                destination.write(chunk)

        try:
            normalized_path = normalize_audio(original_path, temp_dir)
            result = get_transcriber().transcribe(normalized_path)
            return TranscriptionResponse(**result)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {exc}",
            ) from exc
        finally:
            await file.close()
