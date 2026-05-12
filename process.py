import os
import shutil
import hashlib
import argparse
import subprocess

from dotenv import load_dotenv
from faster_whisper import WhisperModel

load_dotenv()

CHUNK_DURATION = 60


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
    workdir = os.path.join(os.getcwd(), "workdir")

    os.makedirs(workdir, exist_ok=True)

    return workdir


def get_default_model_path():
    local_model = os.path.join(
        os.getcwd(),
        "models",
        "faster-whisper-base",
    )

    if os.path.exists(local_model):
        return local_model

    env_model = os.environ.get("WHISPER_MODEL_PATH")

    if env_model and os.path.exists(env_model):
        return env_model

    return None


def validate_environment():
    work_dir = os.environ.get("WORKING_DIR")

    if not work_dir:
        work_dir = get_default_working_dir()
        os.environ["WORKING_DIR"] = work_dir

    os.makedirs(work_dir, exist_ok=True)

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
            subprocess.check_output([binary, "-version"])
        except Exception:
            raise Exception(
                f"Missing binary:\n{binary}\n\n"
                "Run install.bat again."
            )


def run(cmd):
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise Exception(f"Command failed: {' '.join(cmd)}")


def get_duration(video):
    cmd = [
        FFPROBE,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video,
    ]

    out = subprocess.check_output(cmd).decode().strip()

    return float(out)


def format_ts(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)

    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def ensure_dirs(base):
    for d in [
        "chunks_video",
        "chunks_audio",
        "transcripts",
        "srt_parts",
    ]:
        os.makedirs(os.path.join(base, d), exist_ok=True)


def hash_path(p):
    return hashlib.md5(p.encode()).hexdigest()[:8]


def split_video(video, base, duration):
    i = 0
    t = 0

    while t < duration:
        out = os.path.join(base, "chunks_video", f"chunk_{i}.mp4")

        if os.path.exists(out):
            i += 1
            t += CHUNK_DURATION
            continue

        run(
            [
                FFMPEG,
                "-y",
                "-i",
                video,
                "-ss",
                str(t),
                "-t",
                str(CHUNK_DURATION),
                "-c",
                "copy",
                out,
            ]
        )

        i += 1
        t += CHUNK_DURATION


def extract_audio(chunk_path, audio_path):
    if os.path.exists(audio_path):
        return

    run(
        [
            FFMPEG,
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
        ]
    )


def get_existing_index(base):
    idx = 1

    srt_dir = os.path.join(base, "srt_parts")

    if not os.path.exists(srt_dir):
        return idx

    files = sorted(os.listdir(srt_dir))

    for f in files:
        path = os.path.join(srt_dir, f)

        if not os.path.isfile(path):
            continue

        with open(path, encoding="utf-8") as file:
            for line in file:
                if line.strip().isdigit():
                    idx += 1

    return idx


def transcribe_chunk(model, audio_path, txt_path, srt_path, offset, index_start):
    if os.path.exists(txt_path) and os.path.exists(srt_path):
        return index_start

    segments, _ = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
    )

    tmp_txt = txt_path + ".tmp"
    tmp_srt = srt_path + ".tmp"

    idx = index_start

    with open(tmp_txt, "w", encoding="utf-8") as txt, open(
        tmp_srt,
        "w",
        encoding="utf-8",
    ) as srt:

        for seg in segments:
            start = seg.start + offset
            end = seg.end + offset
            text = seg.text.strip()

            txt.write(text + "\n")

            srt.write(f"{idx}\n")
            srt.write(f"{format_ts(start)} --> {format_ts(end)}\n")
            srt.write(text + "\n\n")

            idx += 1

    os.replace(tmp_txt, txt_path)
    os.replace(tmp_srt, srt_path)

    return idx


def merge_outputs(base, output_dir, video_name, total_chunks):
    os.makedirs(output_dir, exist_ok=True)

    final_txt = os.path.join(
        output_dir,
        f"{video_name}_transcript.txt",
    )

    final_srt = os.path.join(
        output_dir,
        f"{video_name}_timestamped.srt",
    )

    with open(final_txt, "w", encoding="utf-8") as ft, open(
        final_srt,
        "w",
        encoding="utf-8",
    ) as fs:

        idx = 1

        for i in range(total_chunks):
            txt_part = os.path.join(base, "transcripts", f"{i}.txt")
            srt_part = os.path.join(base, "srt_parts", f"{i}.srt")

            if os.path.exists(txt_part):
                with open(txt_part, encoding="utf-8") as f:
                    ft.write(f.read())

            if os.path.exists(srt_part):
                with open(srt_part, encoding="utf-8") as f:
                    for line in f:
                        if line.strip().isdigit():
                            fs.write(f"{idx}\n")
                            idx += 1
                        else:
                            fs.write(line)


def main():
    validate_environment()

    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--resume", action="store_true")

    args = parser.parse_args()

    video = args.input
    work_root = os.environ["WORKING_DIR"]

    video_name = os.path.splitext(os.path.basename(video))[0]

    video_id = f"{video_name}_{hash_path(os.path.abspath(video))}"

    base = os.path.join(work_root, video_id)

    if args.output:
        output_dir = os.path.abspath(args.output)
    else:
        output_dir = os.path.dirname(os.path.abspath(video))

    if not args.resume and os.path.exists(base):
        shutil.rmtree(base)

    ensure_dirs(base)

    duration = get_duration(video)

    print("Loading Whisper model...")

    model = WhisperModel(
        get_default_model_path(),
        compute_type="int8",
    )

    print("Splitting video...")
    split_video(video, base, duration)

    total_chunks = int(duration // CHUNK_DURATION) + 1

    global_index = get_existing_index(base) if args.resume else 1

    for i in range(total_chunks):
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

        print(f"Processing chunk {i}...")

        extract_audio(chunk_video, chunk_audio)

        offset = i * CHUNK_DURATION

        global_index = transcribe_chunk(
            model,
            chunk_audio,
            txt_path,
            srt_path,
            offset,
            global_index,
        )

        print(f"chunk {i} done")

    print("Merging outputs...")

    merge_outputs(
        base,
        output_dir,
        video_name,
        total_chunks,
    )

    print("complete")


if __name__ == "__main__":
    main()