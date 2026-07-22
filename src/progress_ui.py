"""Small Tkinter dialogs for update consent, progress, and errors."""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import messagebox, ttk


def ask_optional_update(
    current_version: str, latest_version: str, release_notes: str
) -> bool:
    root = tk.Tk()
    root.withdraw()
    detail = (
        f"Current Version: {current_version}\n"
        f"Latest Version: {latest_version}\n\n"
        f"{release_notes or 'A new version is available.'}\n\n"
        "Install it now?"
    )
    result = messagebox.askyesno("Update Available", detail, parent=root)
    root.destroy()
    return result


def show_error(title: str, message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, message, parent=root)
    root.destroy()


class ProgressWindow:
    """Thread-safe progress window driven by a queue and Tk's event loop."""

    def __init__(self, current_version: str, latest_version: str, total_bytes: int):
        self.total_bytes = max(total_bytes, 1)
        self.downloaded = 0
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.root = tk.Tk()
        self.root.title("Snake Update")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        frame = ttk.Frame(self.root, padding=20)
        frame.grid()
        ttk.Label(frame, text="Update Available", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            frame,
            text=f"Current Version: {current_version}\nLatest Version: {latest_version}",
        ).grid(row=1, column=0, sticky="w", pady=(8, 16))
        self.status = tk.StringVar(value="Downloading...")
        ttk.Label(frame, textvariable=self.status).grid(row=2, column=0, sticky="w")
        self.progress = ttk.Progressbar(frame, length=360, maximum=100)
        self.progress.grid(row=3, column=0, pady=(6, 4))
        self.percentage = tk.StringVar(value="0%")
        ttk.Label(frame, textvariable=self.percentage).grid(
            row=4, column=0, sticky="e"
        )

    def add_downloaded(self, byte_count: int) -> None:
        self.events.put(("bytes", byte_count))

    def set_status(self, text: str) -> None:
        self.events.put(("status", text))

    def close(self) -> None:
        self.events.put(("close", None))

    def run(self) -> None:
        self.root.after(50, self._drain_events)
        self.root.mainloop()

    def _drain_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "bytes":
                    self.downloaded += int(value)
                    percent = min(100, round(self.downloaded * 100 / self.total_bytes))
                    self.progress["value"] = percent
                    self.percentage.set(f"{percent}%")
                elif event == "status":
                    self.status.set(str(value))
                elif event == "close":
                    self.root.destroy()
                    return
        except queue.Empty:
            self.root.after(50, self._drain_events)
