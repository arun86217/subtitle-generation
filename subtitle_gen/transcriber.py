import os

from faster_whisper import WhisperModel

from subtitle_gen.workspace import format_ts


class Transcriber:
    """Wraps the Whisper model: loads it once, then transcribes one audio
    chunk at a time into a plain-text and an SRT fragment."""

    def __init__(self, model_path, logger, device="cpu", compute_type="int8", cpu_threads=4):
        self.model_path = model_path
        self.logger = logger
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.model = None

    def load(self):
        self.logger.log("Loading Whisper model")
        self.model = WhisperModel(
            self.model_path,
            device=self.device,
            compute_type=self.compute_type,
            cpu_threads=self.cpu_threads,
        )
        self.logger.log("Whisper model loaded")

    def transcribe_chunk(self, audio_path, txt_path, srt_path, offset, index_start, chunk_index, language):
        if os.path.exists(txt_path) and os.path.exists(srt_path):
            self.logger.log(f"[Chunk {chunk_index}] Already processed")
            return index_start

        self.logger.log(f"[Chunk {chunk_index}] Transcribing")

        segments, _info = self.model.transcribe(
            audio_path, language=language, vad_filter=True, beam_size=5,
        )
        segments = list(segments)

        if not segments:
            self.logger.log(f"[Chunk {chunk_index}] No speech detected")
            open(txt_path, "w", encoding="utf-8").close()
            open(srt_path, "w", encoding="utf-8").close()
            return index_start

        idx = index_start
        with open(txt_path, "w", encoding="utf-8") as txt_file, \
             open(srt_path, "w", encoding="utf-8") as srt_file:

            for segment in segments:
                text = segment.text.strip()
                if not text:
                    continue

                txt_file.write(text + "\n")

                start = segment.start + offset
                end = segment.end + offset

                srt_file.write(f"{idx}\n")
                srt_file.write(f"{format_ts(start)} --> {format_ts(end)}\n")
                srt_file.write(text + "\n\n")

                idx += 1

        return idx
