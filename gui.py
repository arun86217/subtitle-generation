import os
import sys
import threading
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox

APP_TITLE = "Offline Subtitle Generator"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("900x700")

        self.video_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.resume_mode = ctk.BooleanVar(value=True)

        self.process = None

        self.build_ui()

    def build_ui(self):
        title = ctk.CTkLabel(
            self,
            text="Offline Video → Subtitle Generator",
            font=("Arial", 28, "bold"),
        )
        title.pack(pady=20)

        subtitle = ctk.CTkLabel(
            self,
            text="100% Offline • No APIs • No Cloud • No Technical Knowledge Required",
            font=("Arial", 14),
        )
        subtitle.pack(pady=(0, 20))

        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Input
        ctk.CTkLabel(frame, text="Video File").pack(anchor="w", padx=20, pady=(20, 5))

        input_frame = ctk.CTkFrame(frame)
        input_frame.pack(fill="x", padx=20)

        ctk.CTkEntry(
            input_frame,
            textvariable=self.video_path,
            width=600,
        ).pack(side="left", padx=10, pady=10)

        ctk.CTkButton(
            input_frame,
            text="Browse",
            command=self.select_video,
            width=120,
        ).pack(side="right", padx=10)

        # Output
        ctk.CTkLabel(frame, text="Output Folder").pack(anchor="w", padx=20, pady=(20, 5))

        output_frame = ctk.CTkFrame(frame)
        output_frame.pack(fill="x", padx=20)

        ctk.CTkEntry(
            output_frame,
            textvariable=self.output_path,
            width=600,
        ).pack(side="left", padx=10, pady=10)

        ctk.CTkButton(
            output_frame,
            text="Browse",
            command=self.select_output,
            width=120,
        ).pack(side="right", padx=10)

        # Resume
        ctk.CTkCheckBox(
            frame,
            text="Resume interrupted processing",
            variable=self.resume_mode,
        ).pack(anchor="w", padx=20, pady=20)

        # Buttons
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(fill="x", padx=20, pady=10)

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="Start Processing",
            height=50,
            font=("Arial", 18, "bold"),
            command=self.start_processing,
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=10, pady=10)

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="Stop",
            height=50,
            fg_color="red",
            hover_color="#aa0000",
            command=self.stop_processing,
        )
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=10, pady=10)

        # Status
        self.status_label = ctk.CTkLabel(
            frame,
            text="Ready",
            font=("Arial", 16),
        )
        self.status_label.pack(pady=10)

        # Logs
        self.logs = ctk.CTkTextbox(frame, height=300)
        self.logs.pack(fill="both", expand=True, padx=20, pady=20)

    def log(self, text):
        self.logs.insert("end", text + "\n")
        self.logs.see("end")
        self.update()

    def select_video(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Video Files", "*.mp4 *.mkv *.avi *.mov *.webm"),
                ("All Files", "*.*"),
            ]
        )

        if path:
            self.video_path.set(path)

            if not self.output_path.get():
                self.output_path.set(os.path.dirname(path))

    def select_output(self):
        path = filedialog.askdirectory()

        if path:
            self.output_path.set(path)

    def start_processing(self):
        video = self.video_path.get().strip()

        if not video:
            messagebox.showerror("Error", "Please select a video file")
            return

        if not os.path.exists(video):
            messagebox.showerror("Error", "Selected video does not exist")
            return

        thread = threading.Thread(target=self.run_process)
        thread.daemon = True
        thread.start()

    def run_process(self):
        self.start_btn.configure(state="disabled")

        video = self.video_path.get().strip()
        output = self.output_path.get().strip()

        cmd = [
            sys.executable,
            "process.py",
            "--input",
            video,
        ]

        if output:
            cmd += ["--output", output]

        if self.resume_mode.get():
            cmd.append("--resume")

        self.log("Starting processing...")
        self.log(" ".join(cmd))

        self.status_label.configure(text="Processing...")

        try:
            creationflags = 0

            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=creationflags,
            )

            for line in self.process.stdout:
                self.log(line.strip())

            self.process.wait()

            if self.process.returncode == 0:
                self.status_label.configure(text="Complete")
                self.log("\nDone.")
                messagebox.showinfo("Complete", "Subtitle generation completed")
            else:
                self.status_label.configure(text="Failed")
                self.log("\nProcessing failed")
                messagebox.showerror("Failed", "Processing failed")

        except Exception as e:
            self.log(str(e))
            messagebox.showerror("Error", str(e))

        self.start_btn.configure(state="normal")

    def stop_processing(self):
        if self.process:
            self.process.terminate()
            self.log("Processing stopped")
            self.status_label.configure(text="Stopped")


if __name__ == "__main__":
    app = App()
    app.mainloop()
