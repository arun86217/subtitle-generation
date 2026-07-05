import os
import shutil
import time

from subtitle_gen.workspace import JobWorkspace
from subtitle_gen.subtitle_writer import SubtitleWriter


class SubtitlePipeline:
    """Orchestrates one end-to-end run: resolve duration, split into
    chunks, transcribe each chunk, merge into the final transcript/SRT.
    Depends only on the small collaborators passed in, so swapping the
    transcription backend or the media backend never touches this file."""

    CHUNK_DURATION = 60

    def __init__(self, environment, logger, media_tools, transcriber):
        self.environment = environment
        self.logger = logger
        self.media_tools = media_tools
        self.transcriber = transcriber
        self.subtitle_writer = SubtitleWriter(logger)

    def run(self, video, output_dir, resume, language):
        overall_start = time.time()

        workspace = JobWorkspace(self.environment.work_dir, video)

        if not resume and os.path.exists(workspace.base):
            shutil.rmtree(workspace.base)

        workspace.ensure_dirs()
        self.logger.log_file = workspace.log_file

        if output_dir:
            output_dir = os.path.abspath(output_dir)
        else:
            output_dir = os.path.dirname(os.path.abspath(video))
        os.makedirs(output_dir, exist_ok=True)

        self.logger.log(f"Input video: {video}")

        try:
            duration = self.media_tools.get_duration(video)
        except Exception:
            self.logger.log("Duration metadata missing. Remuxing Chrome recording...")
            video = self.media_tools.remux(video)
            duration = self.media_tools.get_duration(video)

        self.logger.log(f"Video duration: {duration / 60:.2f} minutes")

        self.transcriber.load()

        self.media_tools.split(video, workspace.chunks_dir(), self.CHUNK_DURATION)

        total_chunks = int(duration // self.CHUNK_DURATION) + 1
        self.logger.log(f"Total chunks: {total_chunks}")

        global_index = (
            workspace.existing_subtitle_index() if resume else 1
        )

        for i in range(total_chunks):
            chunk_start = time.time()

            chunk_video = workspace.chunk_video_path(i)
            if not os.path.exists(chunk_video):
                continue

            percent = ((i + 1) / total_chunks) * 100
            self.logger.log(f"Processing chunk {i + 1}/{total_chunks} ({percent:.1f}%)")

            chunk_audio = workspace.chunk_audio_path(i)
            self.media_tools.extract_audio(chunk_video, chunk_audio, i)

            offset = i * self.CHUNK_DURATION
            global_index = self.transcriber.transcribe_chunk(
                chunk_audio,
                workspace.chunk_txt_path(i),
                workspace.chunk_srt_path(i),
                offset,
                global_index,
                i,
                language,
            )

            elapsed = time.time() - chunk_start
            avg = (time.time() - overall_start) / (i + 1)
            remaining = avg * (total_chunks - i - 1)

            self.logger.log(f"Chunk {i} complete in {elapsed:.1f}s")
            self.logger.log(f"Estimated remaining: {remaining / 60:.1f} minutes")

            print(f"PROGRESS:{i + 1}:{total_chunks}", flush=True)

        self.subtitle_writer.merge(workspace, output_dir, total_chunks)

        total_elapsed = time.time() - overall_start
        self.logger.log(f"Complete in {total_elapsed / 60:.1f} minutes")
