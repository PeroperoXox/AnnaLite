"""Anna Lite với UI Tkinter — chat với model chạy local, không cần internet.

Chạy:  python anna_lite_ui.py
(Nhớ bật Ollama / llama-server / LM Studio trước, xem docs/CHAY_MODEL_OFFLINE.md)
"""

import queue
import threading
import tkinter as tk
from tkinter import scrolledtext

from anna_llm import AnnaBrain, LocalLLMError

IDLE_MS = 5 * 60 * 1000  # 5 phút không làm gì thì Anna nhắc


class AnnaApp:
    def __init__(self, root):
        self.root = root
        self.brain = AnnaBrain()
        self.results = queue.Queue()
        self.idle_job = None
        self.busy = False

        root.title("Anna Lite 👀✨")
        root.geometry("560x640")

        self.chat = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED, font=("Segoe UI", 11))
        self.chat.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))
        self.chat.tag_config("anna", foreground="#c2185b")
        self.chat.tag_config("me", foreground="#1565c0")
        self.chat.tag_config("sys", foreground="#888888")

        bottom = tk.Frame(root)
        bottom.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.entry = tk.Entry(bottom, font=("Segoe UI", 11))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda _e: self.send())
        self.send_btn = tk.Button(bottom, text="Gửi", width=8, command=self.send)
        self.send_btn.pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(bottom, text="Xóa trí nhớ", command=self.reset).pack(side=tk.LEFT, padx=(6, 0))

        cfg = self.brain.config
        self.write(f"[model: {cfg['model']} @ {cfg['base_url']}]\n", "sys")
        self.write("Anna: " + self.brain.personality["greeting"] + "\n\n", "anna")
        self.entry.focus_set()
        self.touch()
        self.root.after(100, self.poll)

    def write(self, text, tag):
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, text, tag)
        self.chat.config(state=tk.DISABLED)
        self.chat.see(tk.END)

    def touch(self):
        """Reset đồng hồ nhắc nhở mỗi khi sếp có hoạt động."""
        if self.idle_job:
            self.root.after_cancel(self.idle_job)
        self.idle_job = self.root.after(IDLE_MS, self.idle)

    def idle(self):
        self.write("Anna: " + self.brain.personality["idle_reminder"] + "\n\n", "anna")
        self.touch()

    def reset(self):
        if self.busy:
            return
        self.brain.reset()
        self.write("Anna: Quên sạch rồi nha~\n\n", "anna")
        self.touch()

    def send(self):
        text = self.entry.get().strip()
        if not text or self.busy:
            return
        self.entry.delete(0, tk.END)
        self.write("Sếp: " + text + "\n", "me")
        self.write("Anna đang nghĩ...\n", "sys")
        self.busy = True
        self.send_btn.config(state=tk.DISABLED)
        self.touch()
        threading.Thread(target=self.work, args=(text,), daemon=True).start()

    def work(self, text):
        # Chạy ở thread riêng để UI không bị đơ trong lúc model đang sinh chữ.
        try:
            self.results.put(("anna", "Anna: " + self.brain.ask(text)))
        except LocalLLMError as e:
            self.results.put(("sys", "[Lỗi] " + str(e)))

    def poll(self):
        try:
            tag, msg = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.write(msg + "\n\n", tag)
            self.busy = False
            self.send_btn.config(state=tk.NORMAL)
            self.touch()
        self.root.after(100, self.poll)


if __name__ == "__main__":
    root = tk.Tk()
    AnnaApp(root)
    root.mainloop()
