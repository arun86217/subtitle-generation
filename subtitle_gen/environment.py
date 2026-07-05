import os
import subprocess


class Environment:
    """Resolves ffmpeg/ffprobe binaries, the Whisper model path, and the
    working directory. Raises early with an actionable message if anything
    required is missing."""

    def __init__(self):
        self.ffmpeg = self._find_binary("ffmpeg")
        self.ffprobe = self._find_binary("ffprobe")
        self.work_dir = self._default_working_dir()
        self.model_path = self._resolve_model_path()

    @staticmethod
    def _find_binary(name):
        local_path = os.path.join(os.getcwd(), "ffmpeg", "bin", f"{name}.exe")
        if os.path.exists(local_path):
            return local_path

        global_path = os.path.join("C:\\ffmpeg", "bin", f"{name}.exe")
        if os.path.exists(global_path):
            return global_path

        return name

    @staticmethod
    def _default_working_dir():
        work_dir = os.environ.get("WORKING_DIR")
        if not work_dir:
            work_dir = os.path.join(os.getcwd(), "workdir")
            os.environ["WORKING_DIR"] = work_dir

        os.makedirs(work_dir, exist_ok=True)
        return work_dir

    @staticmethod
    def _resolve_model_path():
        local_model = os.path.join(
            os.getcwd(), "models", "faster-whisper-base"
        )
        if os.path.exists(local_model):
            return local_model

        env_model = os.environ.get("WHISPER_MODEL_PATH")
        if env_model and os.path.exists(env_model):
            return env_model

        return None

    def validate(self):
        if not self.model_path:
            raise Exception(
                "Whisper model not found.\n\n"
                "Expected:\n"
                "./models/faster-whisper-base/"
            )

        os.environ["WHISPER_MODEL_PATH"] = self.model_path

        for binary in (self.ffmpeg, self.ffprobe):
            try:
                subprocess.check_output(
                    [binary, "-version"], stderr=subprocess.STDOUT
                )
            except Exception:
                raise Exception(
                    f"Missing binary:\n{binary}\n\nRun install.bat again."
                )
