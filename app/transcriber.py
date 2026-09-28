import os
from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self) -> None:
        model_size = os.getenv("WHISPER_MODEL", "base")
        device = os.getenv("WHISPER_DEVICE", "cpu")
        compute_type = os.getenv(
            "WHISPER_COMPUTE_TYPE",
            "int8" if device == "cpu" else "float16",
        )

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe(self, audio_path: str) -> dict:
        segments, info = self.model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
        )

        result_segments = []
        full_text_parts = []

        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue

            result_segments.append(
                {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": text,
                }
            )
            full_text_parts.append(text)

        return {
            "text": " ".join(full_text_parts),
            "language": getattr(info, "language", None),
            "duration": round(getattr(info, "duration", 0.0), 2),
            "segments": result_segments,
        }
