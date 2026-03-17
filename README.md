# Offline Video → Subtitle Generator

Fully offline pipeline to convert video → transcript (.txt) + subtitles (.srt) with timestamps.

No APIs. No cloud. No data leakage.

---

## Features

* Handles long videos (3–4 hours+)
* Chunk-based processing (constant RAM usage)
* Resume support (crash-safe)
* Fully offline after setup
* Deterministic outputs
* No hidden dependencies

---

## Requirements

* Python >= 3.9
* FFmpeg (system installed)
* Local Whisper model (pre-downloaded)

---

## Quick Setup (Windows)

Run:

```
setup_check.bat
```

This performs:

* Python detection
* Virtual environment creation
* Dependency installation
* FFmpeg validation
* Environment variable check
* Model validation

---

## Manual Setup

### 1. Create virtual environment

```
python -m venv venv
venv\Scripts\activate
```

If `python` fails:

```
python3 -m venv venv
```

---

### 2. Install dependencies

```
pip install -r requirements.txt
```

---

## Install FFmpeg

Download:

[https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)

Steps:

1. Extract to:

```
C:\ffmpeg
```

2. Add to PATH:

```
C:\ffmpeg\bin
```

Verify:

```
ffmpeg -version
ffprobe -version
```

---

## Download Whisper Model (One-Time)

```
git lfs install
git clone https://huggingface.co/Systran/faster-whisper-base
```

Expected structure:

```
/models/faster-whisper-base/
 ├── config.json
 ├── model.bin
 ├── tokenizer.json
 ├── vocabulary.json
```

---

## Set Environment Variables

### Windows (CMD)

```
set WORKING_DIR=D:\temp
set WHISPER_MODEL_PATH=D:\models\faster-whisper-base
```

### Windows (PowerShell)

```
$env:WORKING_DIR="D:\temp"
$env:WHISPER_MODEL_PATH="D:\models\faster-whisper-base"
```

### Linux / macOS

```
export WORKING_DIR=/fast_disk/tmp
export WHISPER_MODEL_PATH=/models/faster-whisper-base
```

---

## Usage

### Default output (same folder as input)

```
python process.py --input video.mp4
```

---

### Custom output folder

```
python process.py --input video.mp4 --output out/
```

---

### Resume interrupted run

```
python process.py --input video.mp4 --resume
```

---

## Output

For input:

```
video.mp4
```

Generated:

```
video_transcript.txt
video_timestamped.srt
```

---

## Processing Flow

1. Split video into chunks
2. Extract audio per chunk
3. Transcribe using local Whisper model
4. Generate per-chunk transcripts and SRT
5. Merge into final outputs

---

## Working Directory (Temporary)

All intermediate files stored in:

```
WORKING_DIR/
 └── video_hash/
      ├── chunks_video/
      ├── chunks_audio/
      ├── transcripts/
      ├── srt_parts/
      └── progress.log
```

---

## Resume Behavior

* Skips already processed chunks
* Uses filesystem as source of truth
* No dependency on logs for correctness
* Safe to rerun multiple times

---

## Reset State

To fully restart:

```
delete WORKING_DIR/<video_hash>/
```

---

## Performance Notes

* CPU-only: ~real-time or slower
* GPU (if enabled): significantly faster
* Disk usage: ~1.2x–1.5x video size

---

## Constraints

* No automatic installation of Python or FFmpeg
* No network usage during processing
* Model must exist locally before run
* Chunk duration must remain constant across runs

---

## Failure Handling

* Chunk-level isolation
* Atomic file writes prevent corruption
* Partial runs safely resumable
* Clear failure points (FFmpeg / model / env)

---

## Minimal Project Structure

```
project/
 ├── process.py
 ├── setup_check.bat
 ├── requirements.txt
 ├── README.md
 └── .gitignore
```

---

## License

MIT
