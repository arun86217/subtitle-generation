import os
import time
import shutil
import hashlib
import argparse
import subprocess

from datetime import datetime
from dotenv import load_dotenv
from faster_whisper import WhisperModel
Then remove the duration dependency in main():

load_dotenv()

CHUNK_DURATION = 60
LOG_FILE = None


def remux_webm(video):
    """
    Rewrite the container without re-encoding.

    Chrome MediaRecorder files often have Duration=N/A.
    FFmpeg can usually rebuild the container and write proper metadata.
    """

    base, ext = os.path.splitext(video)
    output = base + "_fixed" + ext

    if os.path.exists(output):
        return output

    run(
        [
            FFMPEG,
            "-nostdin",
            "-y",
            "-fflags",
            "+genpts",
            "-i",
            video,
            "-c",
            "copy",
            output,
        ],
        label="Remux",
    )

    return output


def log(msg):
    global LOG_FILE

    ts = datetime.now().strftime("%H:%M:%S")

    safe_msg = str(msg).replace("→", "->")

    line = f"[{ts}] {safe_msg}"

    try:
        print(
            line,
            flush=True,
        )
    except UnicodeEncodeError:
        print(
            line.encode(
                "ascii",
                errors="ignore",
            ).decode(),
            flush=True,
        )

    if LOG_FILE:
        with open(
            LOG_FILE,
            "a",
            encoding="utf-8",
        ) as f:
            f.write(line + "\n")


def get_ffmpeg_binary(name):
    local_path = os.path.join(
        os.getcwd(),
        "ffmpeg",
        "bin",
        f"{name}.exe",
    )

    if os.path.exists(local_path):
        return local_path

    global_path = os.path.join(
        "C:\\ffmpeg",
        "bin",
        f"{name}.exe",
    )

    if os.path.exists(global_path):
        return global_path

    return name


FFMPEG = get_ffmpeg_binary("ffmpeg")
FFPROBE = get_ffmpeg_binary("ffprobe")


def get_default_working_dir():
    workdir = os.path.join(
        os.getcwd(),
        "workdir",
    )

    os.makedirs(
        workdir,
        exist_ok=True,
    )

    return workdir


def get_default_model_path():
    local_model = os.path.join(
        os.getcwd(),
        "models",
        "faster-whisper-base",
    )

    if os.path.exists(local_model):
        return local_model

    env_model = os.environ.get(
        "WHISPER_MODEL_PATH"
    )

    if env_model and os.path.exists(env_model):
        return env_model

    return None


def validate_environment():
    work_dir = os.environ.get(
        "WORKING_DIR"
    )

    if not work_dir:
        work_dir = get_default_working_dir()

        os.environ["WORKING_DIR"] = work_dir

    os.makedirs(
        work_dir,
        exist_ok=True,
    )

    model_path = get_default_model_path()

    if not model_path:
        raise Exception(
            "Whisper model not found.\n\n"
            "Expected:\n"
            "./models/faster-whisper-base/"
        )

    os.environ["WHISPER_MODEL_PATH"] = model_path

    for binary in [FFMPEG, FFPROBE]:
        try:
            subprocess.check_output(
                [binary, "-version"],
                stderr=subprocess.STDOUT,
            )

        except Exception:
            raise Exception(
                f"Missing binary:\n{binary}\n\n"
                "Run install.bat again."
            )


def run(cmd, label=None):
    creationflags = 0

    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        creationflags=creationflags,
    )

    for line in process.stdout:
        line = line.strip()

        if not line:
            continue

        if (
            "time=" in line
            or "size=" in line
            or "speed=" in line
            or "Duration:" in line
        ):
            if label:
                log(f"[{label}] {line}")
            else:
                log(line)

    process.wait()

    if process.returncode != 0:
        raise Exception(
            f"Command failed:\n{' '.join(cmd)}"
        )


def get_duration(video):
    """
    Returns duration in seconds.

    Tries multiple ffprobe methods because some WebM recordings report
    format duration as N/A.
    """

    commands = [
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video,
        ],
        [
            FFPROBE,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video,
        ],
    ]

    for cmd in commands:
        try:
            out = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
            ).decode().strip()

            if out and out != "N/A" and out.lower() != "nan":
                value = float(out)
                if value > 0:
                    return value

        except Exception:
            pass

    try:
        proc = subprocess.run(
            [
                FFMPEG,
                "-i",
                video,
                "-f",
                "null",
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        import re

        match = re.search(
            r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",
            proc.stdout,
        )

        if match:
            h = int(match.group(1))
            m = int(match.group(2))
            s = float(match.group(3))
            return h * 3600 + m * 60 + s

    except Exception:
        pass

    raise Exception(
        "Unable to determine video duration.\n"
        "The input file appears to have no valid duration metadata "
        "or is corrupted."
    )

def format_ts(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)

    return (
        f"{h:02}:{m:02}:{s:02},{ms:03}"
    )


def ensure_dirs(base):
    for d in [
        "chunks_video",
        "chunks_audio",
        "transcripts",
        "srt_parts",
    ]:
        os.makedirs(
            os.path.join(base, d),
            exist_ok=True,
        )


def hash_path(p):
    return hashlib.md5(
        p.encode()
    ).hexdigest()[:8]


def split_video(video, base):
    output_pattern = os.path.join(
        base,
        "chunks_video",
        "chunk_%04d.mp4",
    )

    log("Splitting video into chunks...")

    run(
        [
            FFMPEG,
            "-nostdin",
            "-y",
            "-i",
            video,
            "-map",
            "0",
            "-c",
            "copy",
            "-f",
            "segment",
            "-segment_time",
            str(CHUNK_DURATION),
            "-reset_timestamps",
            "1",
            output_pattern,
        ],
        label="Split",
    )


def extract_audio(
    chunk_path,
    audio_path,
    chunk_index,
):
    if os.path.exists(audio_path):
        return

    log(
        f"[Chunk {chunk_index}] "
        f"Extracting audio"
    )

    run(
        [
            FFMPEG,
            "-nostdin",
            "-y",
            "-i",
            chunk_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            audio_path,
        ],
        label=f"Audio {chunk_index}",
    )


def get_existing_index(base):
    idx = 1

    srt_dir = os.path.join(
        base,
        "srt_parts",
    )

    if not os.path.exists(srt_dir):
        return idx

    files = sorted(
        os.listdir(srt_dir)
    )

    for f in files:
        path = os.path.join(
            srt_dir,
            f,
        )

        if not os.path.isfile(path):
            continue

        with open(
            path,
            encoding="utf-8",
        ) as file:
            for line in file:
                if line.strip().isdigit():
                    idx += 1

    return idx


def transcribe_chunk(
    model,
    audio_path,
    txt_path,
    srt_path,
    offset,
    index_start,
    chunk_index,
    language,
):
    if (
        os.path.exists(txt_path)
        and os.path.exists(srt_path)
    ):
        log(
            f"[Chunk {chunk_index}] "
            f"Already processed"
        )

        return index_start

    log(
        f"[Chunk {chunk_index}] "
        f"Transcribing"
    )

    segments, info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=True,
        beam_size=5,
    )

    segments = list(segments)

    if not segments:
        log(
            f"[Chunk {chunk_index}] "
            f"No speech detected"
        )

        with open(
            txt_path,
            "w",
            encoding="utf-8",
        ) as txt_file:
            txt_file.write("")

        with open(
            srt_path,
            "w",
            encoding="utf-8",
        ) as srt_file:
            srt_file.write("")

        return index_start

    with open(
        txt_path,
        "w",
        encoding="utf-8",
    ) as txt_file:

        with open(
            srt_path,
            "w",
            encoding="utf-8",
        ) as srt_file:

            idx = index_start

            for segment in segments:
                text = segment.text.strip()

                if not text:
                    continue

                txt_file.write(text + "\n")

                start = (
                    segment.start + offset
                )

                end = (
                    segment.end + offset
                )

                srt_file.write(
                    f"{idx}\n"
                )

                srt_file.write(
                    f"{format_ts(start)} "
                    f"--> "
                    f"{format_ts(end)}\n"
                )

                srt_file.write(
                    text + "\n\n"
                )

                idx += 1

    return idx


def merge_outputs(
    base,
    output_dir,
    video_name,
    total_chunks,
):
    output_dir = os.path.abspath(
        os.path.expanduser(output_dir)
    )

    transcript_output = os.path.abspath(
        os.path.join(
            output_dir,
            f"{video_name}_transcript.txt",
        )
    )

    srt_output = os.path.abspath(
        os.path.join(
            output_dir,
            f"{video_name}.srt",
        )
    )

    os.makedirs(
        os.path.dirname(transcript_output),
        exist_ok=True,
    )

    os.makedirs(
        os.path.dirname(srt_output),
        exist_ok=True,
    )

    log(
        f"Merging outputs into: {output_dir}"
    )

    with open(
        transcript_output,
        "w",
        encoding="utf-8",
    ) as txt_out:

        for i in range(total_chunks):
            txt_path = os.path.join(
                base,
                "transcripts",
                f"{i}.txt",
            )

            if os.path.exists(txt_path):
                with open(
                    txt_path,
                    encoding="utf-8",
                ) as f:
                    txt_out.write(
                        f.read()
                    )
                    txt_out.write("\n")

    with open(
        srt_output,
        "w",
        encoding="utf-8",
    ) as srt_out:

        for i in range(total_chunks):
            srt_path = os.path.join(
                base,
                "srt_parts",
                f"{i}.srt",
            )

            if os.path.exists(srt_path):
                with open(
                    srt_path,
                    encoding="utf-8",
                ) as f:
                    srt_out.write(
                        f.read()
                    )

    log(
        f"Transcript saved:\n"
        f"{transcript_output}"
    )

    log(
        f"SRT saved:\n"
        f"{srt_output}"
    )

def main():
    overall_start = time.time()

    validate_environment()

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
    )

    parser.add_argument(
        "--output",
        default=None,
    )

    parser.add_argument(
        "--resume",
        action="store_true",
    )

    parser.add_argument(
        "--language",
        default="en",
    )

    args = parser.parse_args()

    video = args.input
    work_root = os.environ["WORKING_DIR"]

    video_name = os.path.splitext(
        os.path.basename(video)
    )[0]

    video_id = (
        f"{video_name}_"
        f"{hash_path(os.path.abspath(video))}"
    )

    base = os.path.join(
        work_root,
        video_id,
    )

    global LOG_FILE

    ensure_dirs(base)

    LOG_FILE = os.path.join(
        base,
        "progress.log",
    )

    if args.output:
        output_dir = os.path.abspath(
            args.output
        )
    else:
        output_dir = os.path.dirname(
            os.path.abspath(video)
        )

    os.makedirs(
        output_dir,
        exist_ok=True,
    )

    if (
        not args.resume
        and os.path.exists(base)
    ):
        shutil.rmtree(base)

        ensure_dirs(base)

    log(f"Input video: {video}")

    try:

        duration = get_duration(video)

    except Exception:
        log("Duration metadata missing. Remuxing Chrome recording...")

        video = remux_webm(video)

        duration = get_duration(video)


    log(
        f"Video duration: "
        f"{duration / 60:.2f} minutes"
    )

    log("Loading Whisper model")

    model = WhisperModel(
        get_default_model_path(),
        device="cpu",
        compute_type="int8",
        cpu_threads=4,
    )

    log("Whisper model loaded")

    split_video(
        video,
        base,
        duration,
    )

    total_chunks = (
        int(duration // CHUNK_DURATION) + 1
    )

    log(f"Total chunks: {total_chunks}")

    global_index = (
        get_existing_index(base)
        if args.resume
        else 1
    )

    for i in range(total_chunks):
        chunk_start = time.time()

        chunk_video = os.path.join(
            base,
            "chunks_video",
            f"chunk_{i}.mp4",
        )

        chunk_audio = os.path.join(
            base,
            "chunks_audio",
            f"{i}.wav",
        )

        txt_path = os.path.join(
            base,
            "transcripts",
            f"{i}.txt",
        )

        srt_path = os.path.join(
            base,
            "srt_parts",
            f"{i}.srt",
        )

        if not os.path.exists(chunk_video):
            continue

        percent = (
            (i + 1) / total_chunks
        ) * 100

        log(
            f"Processing chunk "
            f"{i + 1}/{total_chunks} "
            f"({percent:.1f}%)"
        )

        extract_audio(
            chunk_video,
            chunk_audio,
            i,
        )

        offset = i * CHUNK_DURATION

        global_index = transcribe_chunk(
            model,
            chunk_audio,
            txt_path,
            srt_path,
            offset,
            global_index,
            i,
            args.language,
        )

        elapsed = (
            time.time() - chunk_start
        )

        avg = (
            time.time() - overall_start
        ) / (i + 1)

        remaining = avg * (
            total_chunks - i - 1
        )

        log(
            f"Chunk {i} complete "
            f"in {elapsed:.1f}s"
        )

        log(
            f"Estimated remaining: "
            f"{remaining / 60:.1f} minutes"
        )

        print(
            f"PROGRESS:{i + 1}:{total_chunks}",
            flush=True,
        )

    merge_outputs(
        base,
        output_dir,
        video_name,
        total_chunks,
    )

    total_elapsed = (
        time.time() - overall_start
    )

    log(
        f"Complete in "
        f"{total_elapsed / 60:.1f} minutes"
    )


if __name__ == "__main__":
    main()

