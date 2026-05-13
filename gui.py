import os
import sys
import threading
import subprocess
import customtkinter as ctk

from tkinter import (
    filedialog,
    messagebox,
)

APP_TITLE = (
    "Offline Subtitle Generator"
)

LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Kannada": "kn",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese": "zh",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Russian": "ru",
    "Auto Detect": "",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)

        # -------------------------------------------------
        # Automatic responsive sizing
        # -------------------------------------------------

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Use 85% of screen size
        width = int(screen_width * 0.85)
        height = int(screen_height * 0.88)

        # Set maximum limits
        width = min(width, 1700)
        height = min(height, 1100)

        # Set minimum limits
        width = max(width, 950)
        height = max(height, 700)

        # Center window
        x = int((screen_width - width) / 2)
        y = int((screen_height - height) / 2)

        self.geometry(
            f"{width}x{height}+{x}+{y}"
        )

        self.minsize(900, 650)

        # Start maximized automatically
        try:
            self.state("zoomed")
        except Exception:
            pass

        self.video_path = ctk.StringVar()

        self.output_path = ctk.StringVar()

        self.resume_mode = ctk.BooleanVar(
            value=True
        )

        self.language_name = (
            ctk.StringVar(
                value="English"
            )
        )

        self.process = None

        self.build_ui()

    def build_ui(self):

        # -------------------------------------------------
        # Main scrollable container
        # -------------------------------------------------

        self.scroll_frame = (
            ctk.CTkScrollableFrame(
                self,
                corner_radius=0,
            )
        )

        self.scroll_frame.pack(
            fill="both",
            expand=True,
        )

        # -------------------------------------------------
        # Header
        # -------------------------------------------------

        title = ctk.CTkLabel(
            self.scroll_frame,
            text=(
                "Offline Video → "
                "Subtitle Generator"
            ),
            font=(
                "Arial",
                32,
                "bold",
            ),
        )

        title.pack(
            pady=(25, 10)
        )

        subtitle = ctk.CTkLabel(
            self.scroll_frame,
            text=(
                "100% Offline • "
                "No APIs • "
                "No Cloud"
            ),
            font=("Arial", 15),
        )

        subtitle.pack(
            pady=(0, 25)
        )

        # -------------------------------------------------
        # Main Content Frame
        # -------------------------------------------------

        frame = ctk.CTkFrame(
            self.scroll_frame,
            corner_radius=15,
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20),
        )

        # -------------------------------------------------
        # Video Input
        # -------------------------------------------------

        ctk.CTkLabel(
            frame,
            text="Video File",
            font=("Arial", 16, "bold"),
        ).pack(
            anchor="w",
            padx=25,
            pady=(25, 8),
        )

        input_frame = ctk.CTkFrame(frame)

        input_frame.pack(
            fill="x",
            padx=20,
        )

        ctk.CTkEntry(
            input_frame,
            textvariable=self.video_path,
            height=42,
            font=("Arial", 14),
        ).pack(
            side="left",
            padx=10,
            pady=10,
            fill="x",
            expand=True,
        )

        ctk.CTkButton(
            input_frame,
            text="Browse",
            command=self.select_video,
            width=130,
            height=40,
            font=("Arial", 14, "bold"),
        ).pack(
            side="right",
            padx=10,
        )

        # -------------------------------------------------
        # Output Folder
        # -------------------------------------------------

        ctk.CTkLabel(
            frame,
            text="Output Folder",
            font=("Arial", 16, "bold"),
        ).pack(
            anchor="w",
            padx=25,
            pady=(25, 8),
        )

        output_frame = ctk.CTkFrame(frame)

        output_frame.pack(
            fill="x",
            padx=20,
        )

        ctk.CTkEntry(
            output_frame,
            textvariable=self.output_path,
            height=42,
            font=("Arial", 14),
        ).pack(
            side="left",
            padx=10,
            pady=10,
            fill="x",
            expand=True,
        )

        ctk.CTkButton(
            output_frame,
            text="Browse",
            command=self.select_output,
            width=130,
            height=40,
            font=("Arial", 14, "bold"),
        ).pack(
            side="right",
            padx=10,
        )

        # -------------------------------------------------
        # Language Selection
        # -------------------------------------------------

        ctk.CTkLabel(
            frame,
            text="Subtitle Language",
            font=("Arial", 16, "bold"),
        ).pack(
            anchor="w",
            padx=25,
            pady=(25, 8),
        )

        language_dropdown = (
            ctk.CTkOptionMenu(
                frame,
                variable=self.language_name,
                values=list(
                    LANGUAGES.keys()
                ),
                width=320,
                height=42,
                font=("Arial", 14),
                dropdown_font=("Arial", 14),
            )
        )

        language_dropdown.pack(
            anchor="w",
            padx=20,
            pady=(0, 20),
        )

        # -------------------------------------------------
        # Resume Checkbox
        # -------------------------------------------------

        ctk.CTkCheckBox(
            frame,
            text=(
                "Resume interrupted "
                "processing"
            ),
            variable=self.resume_mode,
            font=("Arial", 14),
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 20),
        )

        # -------------------------------------------------
        # Buttons
        # -------------------------------------------------

        btn_frame = ctk.CTkFrame(frame)

        btn_frame.pack(
            fill="x",
            padx=20,
            pady=10,
        )

        self.start_btn = (
            ctk.CTkButton(
                btn_frame,
                text="Start Processing",
                height=55,
                font=(
                    "Arial",
                    18,
                    "bold",
                ),
                command=self.start_processing,
            )
        )

        self.start_btn.pack(
            side="left",
            expand=True,
            fill="x",
            padx=10,
            pady=10,
        )

        self.stop_btn = (
            ctk.CTkButton(
                btn_frame,
                text="Stop",
                height=55,
                fg_color="red",
                hover_color="#aa0000",
                font=(
                    "Arial",
                    18,
                    "bold",
                ),
                command=self.stop_processing,
            )
        )

        self.stop_btn.pack(
            side="left",
            expand=True,
            fill="x",
            padx=10,
            pady=10,
        )

        # -------------------------------------------------
        # Status
        # -------------------------------------------------

        self.status_label = (
            ctk.CTkLabel(
                frame,
                text="Ready",
                font=("Arial", 18, "bold"),
            )
        )

        self.status_label.pack(
            pady=(20, 5)
        )

        self.progress_label = (
            ctk.CTkLabel(
                frame,
                text="0%",
                font=("Arial", 14),
            )
        )

        self.progress_label.pack()

        self.progress_bar = (
            ctk.CTkProgressBar(
                frame,
                height=24,
            )
        )

        self.progress_bar.pack(
            fill="x",
            padx=20,
            pady=15,
        )

        self.progress_bar.set(0)

        # -------------------------------------------------
        # Logs
        # -------------------------------------------------

        ctk.CTkLabel(
            frame,
            text="Logs",
            font=("Arial", 16, "bold"),
        ).pack(
            anchor="w",
            padx=25,
            pady=(10, 5),
        )

        self.logs = ctk.CTkTextbox(
            frame,
            height=350,
            font=("Consolas", 13),
        )

        self.logs.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 25),
        )

    # -------------------------------------------------
    # Logging
    # -------------------------------------------------

    def log(self, text):

        self.logs.insert(
            "end",
            text + "\n",
        )

        self.logs.see("end")

        self.update()

    # -------------------------------------------------
    # Progress
    # -------------------------------------------------

    def update_progress(
        self,
        current,
        total,
    ):

        if total <= 0:
            return

        progress = current / total

        self.progress_bar.set(
            progress
        )

        self.progress_label.configure(
            text=(
                f"{progress * 100:.1f}% "
                f"({current}/{total})"
            )
        )

        self.update()

    # -------------------------------------------------
    # Select Video
    # -------------------------------------------------

    def select_video(self):

        path = (
            filedialog.askopenfilename(
                filetypes=[
                    (
                        "Video Files",
                        "*.mp4 *.mkv "
                        "*.avi *.mov "
                        "*.webm",
                    ),
                    (
                        "All Files",
                        "*.*",
                    ),
                ]
            )
        )

        if path:

            self.video_path.set(path)

            if not self.output_path.get():

                self.output_path.set(
                    os.path.dirname(path)
                )

    # -------------------------------------------------
    # Select Output
    # -------------------------------------------------

    def select_output(self):

        path = (
            filedialog.askdirectory()
        )

        if path:

            self.output_path.set(path)

    # -------------------------------------------------
    # Start Processing
    # -------------------------------------------------

    def start_processing(self):

        video = (
            self.video_path.get().strip()
        )

        if not video:

            messagebox.showerror(
                "Error",
                "Please select a video file",
            )

            return

        if not os.path.exists(video):

            messagebox.showerror(
                "Error",
                "Selected video does not exist",
            )

            return

        self.logs.delete(
            "1.0",
            "end",
        )

        self.progress_bar.set(0)

        self.progress_label.configure(
            text="0%"
        )

        thread = threading.Thread(
            target=self.run_process
        )

        thread.daemon = True

        thread.start()

    # -------------------------------------------------
    # Run Process
    # -------------------------------------------------

    def run_process(self):

        self.start_btn.configure(
            state="disabled"
        )

        video = (
            self.video_path.get().strip()
        )

        output = (
            self.output_path.get().strip()
        )

        language = LANGUAGES[
            self.language_name.get()
        ]

        cmd = [
            sys.executable,
            "process.py",
            "--input",
            video,
        ]

        if output:

            cmd += [
                "--output",
                output,
            ]

        if language:

            cmd += [
                "--language",
                language,
            ]

        if self.resume_mode.get():

            cmd.append("--resume")

        self.log(
            "Starting processing..."
        )

        self.log(" ".join(cmd))

        self.status_label.configure(
            text="Processing..."
        )

        try:

            creationflags = 0

            if os.name == "nt":

                creationflags = (
                    subprocess.CREATE_NO_WINDOW
                )

            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=creationflags,
            )

            for line in self.process.stdout:

                line = line.strip()

                if not line:
                    continue

                if line.startswith(
                    "PROGRESS:"
                ):

                    try:

                        (
                            _,
                            current,
                            total,
                        ) = line.split(":")

                        self.update_progress(
                            int(current),
                            int(total),
                        )

                    except Exception:
                        pass

                    continue

                self.log(line)

            self.process.wait()

            if self.process.returncode == 0:

                self.status_label.configure(
                    text="Complete"
                )

                self.progress_bar.set(1)

                self.progress_label.configure(
                    text="100%"
                )

                self.log("\nDone.")

                messagebox.showinfo(
                    "Complete",
                    (
                        "Subtitle generation "
                        "completed"
                    ),
                )

            else:

                self.status_label.configure(
                    text="Failed"
                )

                self.log(
                    "\nProcessing failed"
                )

                messagebox.showerror(
                    "Failed",
                    "Processing failed",
                )

        except Exception as e:

            self.log(str(e))

            messagebox.showerror(
                "Error",
                str(e),
            )

        self.start_btn.configure(
            state="normal"
        )

    # -------------------------------------------------
    # Stop Processing
    # -------------------------------------------------

    def stop_processing(self):

        if self.process:

            self.process.terminate()

            self.log(
                "Processing stopped"
            )

            self.status_label.configure(
                text="Stopped"
            )


if __name__ == "__main__":
    app = App()
    app.mainloop()
