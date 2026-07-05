import os


class SubtitleWriter:
    """Concatenates per-chunk transcript/SRT fragments into the final
    output files."""

    def __init__(self, logger):
        self.logger = logger

    def merge(self, workspace, output_dir, total_chunks):
        output_dir = os.path.abspath(os.path.expanduser(output_dir))
        os.makedirs(output_dir, exist_ok=True)

        transcript_output = os.path.join(
            output_dir, f"{workspace.video_name}_transcript.txt"
        )
        srt_output = os.path.join(
            output_dir, f"{workspace.video_name}.srt"
        )

        self.logger.log(f"Merging outputs into: {output_dir}")

        with open(transcript_output, "w", encoding="utf-8") as txt_out:
            for i in range(total_chunks):
                txt_path = workspace.chunk_txt_path(i)
                if os.path.exists(txt_path):
                    with open(txt_path, encoding="utf-8") as f:
                        txt_out.write(f.read())
                        txt_out.write("\n")

        with open(srt_output, "w", encoding="utf-8") as srt_out:
            for i in range(total_chunks):
                srt_path = workspace.chunk_srt_path(i)
                if os.path.exists(srt_path):
                    with open(srt_path, encoding="utf-8") as f:
                        srt_out.write(f.read())

        self.logger.log(f"Transcript saved:\n{transcript_output}")
        self.logger.log(f"SRT saved:\n{srt_output}")
