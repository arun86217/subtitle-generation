import os
import sys
import subprocess
import argparse
import shutil
import hashlib
from faster_whisper import WhisperModel
from dotenv import load_dotenv
load_dotenv()

CHUNK_DURATION = 60


def run(cmd):
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        raise Exception(f"Command failed: {' '.join(cmd)}")


def get_duration(video):
    cmd = [
        "ffprobe",
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
    for d in ["chunks_video", "chunks_audio", "transcripts", "srt_parts"]:
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
                "ffmpeg",
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
            "ffmpeg",
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

    files = sorted(
        os.listdir(srt_dir),
        key=lambda x: int(x.split(".")[0]) if x.split(".")[0].isdigit() else -1,
    )

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

    segments, _ = model.transcribe(audio_path)

    tmp_txt = txt_path + ".tmp"
    tmp_srt = srt_path + ".tmp"

    idx = index_start

    with open(tmp_txt, "w", encoding="utf-8") as txt, open(
        tmp_srt, "w", encoding="utf-8"
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

    final_txt = os.path.join(output_dir, f"{video_name}_transcript.txt")
    final_srt = os.path.join(output_dir, f"{video_name}_timestamped.srt")

    with open(final_txt, "w", encoding="utf-8") as ft, open(
        final_srt, "w", encoding="utf-8"
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--resume", action="store_true")

    args = parser.parse_args()

    if "WORKING_DIR" not in os.environ:
        raise Exception("WORKING_DIR not set")

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

    print("Splitting video...")
    split_video(video, base, duration)

    model = WhisperModel("base", compute_type="int8")

    total_chunks = int(duration // CHUNK_DURATION) + 1

    global_index = get_existing_index(base) if args.resume else 1

    for i in range(total_chunks):
        chunk_video = os.path.join(base, "chunks_video", f"chunk_{i}.mp4")
        chunk_audio = os.path.join(base, "chunks_audio", f"{i}.wav")
        txt_path = os.path.join(base, "transcripts", f"{i}.txt")
        srt_path = os.path.join(base, "srt_parts", f"{i}.srt")

        if not os.path.exists(chunk_video):
            continue

        extract_audio(chunk_video, chunk_audio)

        offset = i * CHUNK_DURATION

        global_index = transcribe_chunk(
            model, chunk_audio, txt_path, srt_path, offset, global_index
        )

        with open(os.path.join(base, "progress.log"), "a") as log:
            log.write(f"chunk {i} done\n")

        print(f"chunk {i} done")

    print("Merging outputs...")
    merge_outputs(base, output_dir, video_name, total_chunks)

    print("complete")


if __name__ == "__main__":
    main()
    """
    usage:.
    
    Default output (same folder as input)
    python process.py --input d/video.mp4
    
    Custom output folder:    
    python process.py --input d/video.mp4 --output d/output/
    
    
    Resume previous run
    python process.py --input d/video.mp4 --resume
    
    Fresh run (force reset)
    python process.py --input d/video.mp4
    
    """
