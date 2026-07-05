import os
import re
import subprocess


class MediaTools:
    """All ffmpeg/ffprobe operations: running commands, reading duration,
    fixing broken containers, splitting into chunks, and extracting audio."""

    def __init__(self, environment, logger):
        self.ffmpeg = environment.ffmpeg
        self.ffprobe = environment.ffprobe
        self.logger = logger

    def run(self, cmd, label=None):
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

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
                self.logger.log(f"[{label}] {line}" if label else line)

        process.wait()

        if process.returncode != 0:
            raise Exception(f"Command failed:\n{' '.join(cmd)}")

    def get_duration(self, video):
        """Tries multiple ffprobe methods, then falls back to parsing
        ffmpeg's own banner, because Chrome/Zoom recordings often report
        duration as N/A."""

        commands = [
            [
                self.ffprobe, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video,
            ],
            [
                self.ffprobe, "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video,
            ],
        ]

        for cmd in commands:
            try:
                out = subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT
                ).decode().strip()

                if out and out != "N/A" and out.lower() != "nan":
                    value = float(out)
                    if value > 0:
                        return value
            except Exception:
                pass

        try:
            proc = subprocess.run(
                [self.ffmpeg, "-i", video, "-f", "null", "-"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            match = re.search(
                r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", proc.stdout
            )
            if match:
                h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
                return h * 3600 + m * 60 + s
        except Exception:
            pass

        raise Exception(
            "Unable to determine video duration.\n"
            "The input file appears to have no valid duration metadata "
            "or is corrupted."
        )

    def remux(self, video):
        """Rewrite the container without re-encoding, so ffprobe can read
        a real duration afterwards.

        Always outputs .mkv regardless of the source extension: Chrome/Zoom
        recordings are sometimes saved as .webm while actually holding
        h264/opus, which WebM's muxer rejects. Matroska accepts any codec.
        """

        base, _ext = os.path.splitext(video)
        output = base + "_fixed.mkv"

        if os.path.exists(output):
            return output

        self.run(
            [
                self.ffmpeg, "-nostdin", "-y",
                "-fflags", "+genpts",
                "-i", video,
                "-c", "copy",
                output,
            ],
            label="Remux",
        )

        return output

    def split(self, video, chunks_dir, chunk_duration):
        """Segments the video via ffmpeg's segment muxer (fast, no
        re-encode). Output is always .mkv - Matroska tolerates whatever
        codec the source used (h264, vp8, vp9, ...), unlike mp4."""

        output_pattern = os.path.join(chunks_dir, "chunk_%04d.mkv")

        self.logger.log("Splitting video into chunks...")

        self.run(
            [
                self.ffmpeg, "-nostdin", "-y",
                "-i", video,
                "-map", "0",
                "-c", "copy",
                "-f", "segment",
                "-segment_time", str(chunk_duration),
                "-reset_timestamps", "1",
                output_pattern,
            ],
            label="Split",
        )

    def extract_audio(self, chunk_path, audio_path, chunk_index):
        if os.path.exists(audio_path):
            return

        self.logger.log(f"[Chunk {chunk_index}] Extracting audio")

        self.run(
            [
                self.ffmpeg, "-nostdin", "-y",
                "-i", chunk_path,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                audio_path,
            ],
            label=f"Audio {chunk_index}",
        )
