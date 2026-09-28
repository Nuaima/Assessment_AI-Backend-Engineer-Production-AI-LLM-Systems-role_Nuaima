# Audio Transcription Service

A small production-style speech-to-text API built for the Volga Partners Software Engineer Assessment.

## What it does

- Accepts audio uploads through a FastAPI endpoint.
- Supports WAV, MP3, M4A, AAC, FLAC, OGG, and WebM.
- Normalizes audio to mono 16 kHz WAV using FFmpeg.
- Transcribes speech using `faster-whisper`.
- Returns the full transcription plus timestamps for every segment.
- Uses temporary files so uploaded audio is deleted automatically after processing.
- Rejects unsupported formats and oversized uploads with clear HTTP errors.

## Architecture

```text
Client
  |
  v
POST /transcribe
  |
  v
Validate file -> Save temporary upload -> FFmpeg normalization
  |                                      |
  +--------------------------------------+
                     |
                     v
               faster-whisper
                     |
                     v
       Text + language + timestamps
                     |
                     v
                 JSON response
```

## Why these technologies?

### FastAPI
FastAPI provides typed request/response models, automatic OpenAPI documentation, validation, and straightforward support for uploaded files.

### faster-whisper
`faster-whisper` is an efficient implementation of OpenAI Whisper using CTranslate2. It produces segment timestamps and can run locally without depending on an external transcription API.

### FFmpeg
Incoming files can use different codecs, sample rates, and channel layouts. FFmpeg normalizes them to a consistent mono 16 kHz WAV representation before transcription.

## Run locally

### 1. Install FFmpeg

Linux:

```bash
sudo apt-get install ffmpeg
```

Windows: install FFmpeg and make sure `ffmpeg` is available on PATH.

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

Open Swagger UI at:

```text
http://localhost:8000/docs
```

## Example API request

```bash
curl -X POST "http://localhost:8000/transcribe" \
  -F "file=@sample.wav"
```

Example response:

```json
{
  "text": "Hello, this is a test recording.",
  "language": "en",
  "duration": 3.64,
  "segments": [
    {
      "start": 0.0,
      "end": 3.64,
      "text": "Hello, this is a test recording."
    }
  ]
}
```

## Different audio formats

The API validates the file extension and uses FFmpeg to decode and normalize common formats such as MP3, WAV, M4A, AAC, FLAC, OGG, and WebM. This keeps the transcription layer independent from the original codec and sample rate.

## Long audio files

Whisper processes audio internally in smaller windows, so the current implementation can handle longer audio without loading the entire decoded waveform into application memory. Uploads are also streamed to disk in chunks rather than being read into RAM all at once.

For a higher-scale production system, I would make long transcriptions asynchronous. The API would upload the audio to object storage, create a job in a queue, and return a job ID. Background workers would split or process the audio, persist progress, and merge timestamped results.

## Concurrent uploads

For a production deployment I would avoid running many CPU/GPU-heavy transcriptions directly inside the web process. The API layer would accept uploads and enqueue jobs to a worker queue such as Celery/RQ with Redis, RabbitMQ, or a managed queue. Worker concurrency would be capped according to CPU/GPU capacity. This protects latency and prevents GPU out-of-memory failures during traffic spikes.

## Storage strategy

In production:

- Original audio: object storage such as Amazon S3 or Google Cloud Storage.
- Transcript metadata: PostgreSQL.
- Transcript JSON: either PostgreSQL JSONB or object storage depending on size.
- Store only object keys/URLs in the database rather than large audio blobs.
- Apply retention rules so raw audio is deleted when no longer required.

The assessment implementation uses temporary local files because persistent storage is not required for the demo.

## Retry and recovery

I would represent each transcription as a job with states such as:

```text
queued -> processing -> completed
                    -> failed
```

Transient failures would use exponential backoff with a limited retry count, for example 3 attempts. Jobs should be idempotent by using a unique job ID or file checksum so a retry does not create duplicate transcripts. Permanent failures would be marked failed with an error reason and remain available for manual retry or investigation.

## Production API design

A scalable asynchronous version could expose:

```text
POST /v1/transcriptions
GET  /v1/transcriptions/{job_id}
GET  /v1/transcriptions/{job_id}/result
DELETE /v1/transcriptions/{job_id}
GET  /health
```

`POST /v1/transcriptions` would return HTTP 202 with a job ID while processing occurs asynchronously.

Example:

```json
{
  "job_id": "tr_12345",
  "status": "queued"
}
```

The client could poll the status endpoint or provide a webhook URL for completion callbacks.

## Security and reliability considerations

- Validate file type and file size.
- Set request and processing timeouts.
- Authenticate API requests in production.
- Use rate limits to prevent abuse.
- Scan or isolate uploaded content when required.
- Keep temporary files outside the public web directory.
- Add structured logging and request/job IDs.
- Collect metrics for latency, failure rate, queue depth, and transcription duration.

## Tests

```bash
pytest
```

Current tests verify the health endpoint and rejection of unsupported file types. In a production codebase I would also mock the transcription model and test successful uploads, FFmpeg failures, oversized files, timeout behavior, and malformed audio.

## Trade-offs

I intentionally kept the assessment implementation synchronous because it is easier to run and review. For production, long-running transcription should move to asynchronous workers so the API can handle concurrent users reliably.
