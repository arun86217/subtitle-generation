from datetime import datetime


class Logger:
    """Timestamps messages, prints them, and optionally mirrors them to a
    log file. Passed around instead of a module-global so multiple jobs
    (or tests) never fight over shared state."""

    def __init__(self, log_file=None):
        self.log_file = log_file

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        safe_msg = str(msg).replace("→", "->")
        line = f"[{ts}] {safe_msg}"

        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            print(line.encode("ascii", errors="ignore").decode(), flush=True)

        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
