import os
import hashlib


def format_ts(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def hash_path(p):
    return hashlib.md5(p.encode()).hexdigest()[:8]


class JobWorkspace:
    """Owns the on-disk layout for a single transcription job: chunk
    videos, extracted audio, per-chunk transcripts/SRTs, and the log file.
    Centralizing paths here means the writer (MediaTools.split) and the
    reader (SubtitlePipeline's chunk loop) can never drift out of sync on
    a filename pattern again."""

    SUBDIRS = ("chunks_video", "chunks_audio", "transcripts", "srt_parts")

    def __init__(self, work_root, video_path):
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        video_id = f"{video_name}_{hash_path(os.path.abspath(video_path))}"

        self.video_name = video_name
        self.base = os.path.join(work_root, video_id)
        self.log_file = os.path.join(self.base, "progress.log")

    def ensure_dirs(self):
        for d in self.SUBDIRS:
            os.makedirs(os.path.join(self.base, d), exist_ok=True)

    def chunks_dir(self):
        return os.path.join(self.base, "chunks_video")

    def chunk_video_path(self, index):
        return os.path.join(self.chunks_dir(), f"chunk_{index:04d}.mkv")

    def chunk_audio_path(self, index):
        return os.path.join(self.base, "chunks_audio", f"{index}.wav")

    def chunk_txt_path(self, index):
        return os.path.join(self.base, "transcripts", f"{index}.txt")

    def chunk_srt_path(self, index):
        return os.path.join(self.base, "srt_parts", f"{index}.srt")

    def existing_subtitle_index(self):
        """Highest subtitle index already written, for --resume."""
        idx = 1
        srt_dir = os.path.join(self.base, "srt_parts")
        if not os.path.exists(srt_dir):
            return idx

        for f in sorted(os.listdir(srt_dir)):
            path = os.path.join(srt_dir, f)
            if not os.path.isfile(path):
                continue

            with open(path, encoding="utf-8") as file:
                for line in file:
                    if line.strip().isdigit():
                        idx += 1

        return idx
