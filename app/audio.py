from pathlib import Path
import subprocess
import uuid

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".webm"}


def validate_audio_file(filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format '{suffix}'. Supported formats: "
            + ", ".join(sorted(SUPPORTED_EXTENSIONS))
        )


def normalize_audio(input_path: str, output_dir: str) -> str:
    """Convert audio to mono 16 kHz WAV using FFmpeg."""
    output_path = str(Path(output_dir) / f"normalized_{uuid.uuid4().hex}.wav")

    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        output_path,
    ]

    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg is not installed or not available on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.decode(errors="ignore") if exc.stderr else "Unknown FFmpeg error"
        raise RuntimeError(f"Audio conversion failed: {message}") from exc

    return output_path
