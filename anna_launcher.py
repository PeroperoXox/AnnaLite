"""Bảng điều khiển Anna — bấm nút là mở, không cần gõ lệnh.

Mở bằng cách bấm đúp file  Mo_Anna.bat  (cùng thư mục với file này).

- "Mở Anna VTuber": tự bật Ollama (nếu chưa bật) -> chạy Open-LLM-VTuber -> mở trình duyệt.
- "Chat chữ với Anna": mở cửa sổ chat AnnaLite.
- "Tắt Anna VTuber": tắt server Open-LLM-VTuber.
Chỉ dùng thư viện chuẩn của Python.
"""

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

HERE = Path(__file__).resolve().parent
SETTINGS_FILE = HERE / "launcher_settings.json"
IS_WIN = os.name == "nt"
OLLAMA_PORT = 11434
VTUBER_PORT = 12393
VTUBER_URL = f"http://localhost:{VTUBER_PORT}"
NO_WINDOW = 0x08000000 if IS_WIN else 0      # CREATE_NO_WINDOW
NEW_CONSOLE = 0x00000010 if IS_WIN else 0    # CREATE_NEW_CONSOLE
OLLAMA_WAIT_S = 45
VTUBER_WAIT_S = 15 * 60  # lần đầu phải tải model nghe giọng nên có thể lâu

# Màu (tông tối giống giao diện Open-LLM-VTuber, điểm nhấn hồng)
BG, CARD, FG, MUTED = "#1e1e24", "#2a2a33", "#f2f2f5", "#9a9aa8"
PINK, PINK_DARK, GREEN, RED, YELLOW = "#ff6fa8", "#e0558e", "#3ccf7a", "#ff5c5c", "#ffc24b"


# ----------------------------------------------------------------- tiện ích
def port_open(port, timeout=0.3):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def _first_file(*candidates):
    for c in candidates:
        if c and Path(c).is_file():
            return str(c)
    return None


def _localappdata(*parts):
    base = os.environ.get("LOCALAPPDATA")
    return str(Path(base, *parts)) if base else None


def find_uv():
    return shutil.which("uv") or _first_file(
        Path.home() / ".local" / "bin" / ("uv.exe" if IS_WIN else "uv"),
        _localappdata("Microsoft", "WinGet", "Links", "uv.exe"),
        Path.home() / ".cargo" / "bin" / ("uv.exe" if IS_WIN else "uv"),
    )


def find_ollama():
    return shutil.which("ollama") or _first_file(_localappdata("Programs", "Ollama", "ollama.exe"))


def find_chrome():
    if not IS_WIN:
        return shutil.which("google-chrome") or shutil.which("chromium")
    bases = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")]
    return _first_file(*[Path(b, "Google", "Chrome", "Application", "chrome.exe") for b in bases if b])


def is_olv_dir(path):
    return bool(path) and (Path(path) / "run_server.py").is_file()


def guess_olv_dir():
    candidates = [Path.home() / "Open-LLM-VTuber", HERE.parent / "Open-LLM-VTuber"]
    if IS_WIN:
        candidates += [Path(f"{d}:/Open-LLM-VTuber") for d in "CDEF"]
    for c in candidates:
        if is_olv_dir(c):
            return str(c)
    return None


def read_vtuber_model(olv_dir):
    """Đọc tên model Ollama trong conf.yaml (mục ollama_llm) mà không cần thư viện yaml."""
    try:
        lines = (Path(olv_dir) / "conf.yaml").read_text(encoding="utf-8-sig").splitlines()
    except (OSError, TypeError):
        return None
    for i, line in enumerate(lines):
        if line.strip() == "ollama_llm:":
            for nxt in lines[i + 1:i + 12]:
                m = re.match(r"\s+model:\s*['\"]?([^'\"#\s]+)", nxt)
                if m:
                    return m.group(1)
    return None


def read_chat_model():
    try:
        return json.loads((HERE / "model_config.json").read_text(encoding="utf-8")).get("model")
    except (OSError, ValueError):
        return None


def ollama_models():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{OLLAMA_PORT}/api/tags", timeout=1.5) as r:
            return [m.get("name", "") for m in json.load(r).get("models", [])]
    except Exception:
        return None


def has_model(models, name):
    return any(m == name or m == f"{name}:latest" for m in models)


def pid_listening_on(port):
    """Tìm tiến trình đang mở cổng (khi server được bật từ chỗ khác)."""
    if not IS_WIN:
        return None
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                             creationflags=NO_WINDOW, timeout=5).stdout
    except Exception:
        return None
    for line in out.splitlines():
        parts = line.split()
        # Không dựa vào chữ "LISTENING" vì Windows tiếng khác có thể dịch chữ này.
        if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[2] in ("0.0.0.0:0", "[::]:0"):
            return int(parts[-1])
    return None


def kill_tree(pid):
    if IS_WIN:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, creationflags=NO_WINDOW)
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except OSError:
            pass


def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


# ----------------------------------------------------------------- giao diện
class Launcher:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        olv = self.settings.get("olv_dir")
        self.olv_dir = olv if is_olv_dir(olv) else guess_olv_dir()
        self.server_proc = None   # server do bảng điều khiển này bật
        self.pending = None       # việc đang chờ: "vtuber" hoặc "chat"
        self.phase = None
        self.phase_started = 0.0
        # Trạng thái do thread nền cập nhật
        self.ollama_up = False
        self.models = None
        self.vtuber_up = False

        root.title("Anna")
        root.configure(bg=BG)
        root.resizable(False, False)
        self._set_icon()
        self._build()
        self._refresh_dir_label()

        threading.Thread(target=self._poll_status, daemon=True).start()
        self.root.after(300, self.tick)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- dựng giao diện
    def _set_icon(self):
        size = 32
        img = tk.PhotoImage(width=size, height=size)
        c, r = (size - 1) / 2, size / 2 - 1
        for y in range(size):
            row = []
            for x in range(size):
                d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
                eye = abs(y - 13) <= 2 and (abs(x - 11) <= 1 or abs(x - 20) <= 1)
                row.append(FG if (d <= r and eye) else (PINK if d <= r else BG))
            img.put("{" + " ".join(row) + "}", to=(0, y))
        self._icon = img
        self.root.iconphoto(True, img)

    def _button(self, parent, text, cmd, color=CARD, hover="#383845", big=False):
        b = tk.Label(parent, text=text, bg=color, fg=FG, cursor="hand2",
                     font=("Segoe UI", 13 if big else 11, "bold" if big else "normal"),
                     padx=14, pady=12 if big else 8)
        b.bind("<Button-1>", lambda _e: cmd())
        b.bind("<Enter>", lambda _e: b.config(bg=hover))
        b.bind("<Leave>", lambda _e: b.config(bg=color))
        return b

    def _build(self):
        pad = {"padx": 18}
        tk.Label(self.root, text="Anna", bg=BG, fg=PINK, font=("Segoe UI", 26, "bold")).pack(anchor="w", pady=(16, 0), **pad)
        tk.Label(self.root, text="Bảng điều khiển — bấm là chạy, khỏi gõ lệnh~", bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", **pad)

        card = tk.Frame(self.root, bg=CARD, padx=14, pady=10)
        card.pack(fill="x", pady=(14, 10), **pad)
        self.status_rows = {}
        for key, title in (("ollama", "Ollama (bộ não)"), ("model", "Model"), ("vtuber", "Anna VTuber")):
            row = tk.Frame(card, bg=CARD)
            row.pack(fill="x", pady=3)
            dot = tk.Label(row, text="●", bg=CARD, fg=MUTED, font=("Segoe UI", 12))
            dot.pack(side="left")
            tk.Label(row, text=title, bg=CARD, fg=FG, font=("Segoe UI", 10, "bold"), width=15, anchor="w").pack(side="left", padx=(6, 0))
            text = tk.Label(row, text="đang kiểm tra...", bg=CARD, fg=MUTED, font=("Segoe UI", 10), anchor="w")
            text.pack(side="left", fill="x")
            self.status_rows[key] = (dot, text)

        self._button(self.root, "▶  Mở Anna VTuber", self.open_vtuber, PINK, PINK_DARK, big=True).pack(fill="x", pady=(4, 6), **pad)
        self._button(self.root, "✎  Chat chữ với Anna", self.open_chat).pack(fill="x", pady=3, **pad)
        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", pady=3, **pad)
        self._button(row, "⌂  Mở lại trang web", self.open_browser).pack(side="left", fill="x", expand=True, padx=(0, 3))
        self._button(row, "■  Tắt Anna VTuber", self.stop_vtuber).pack(side="left", fill="x", expand=True, padx=(3, 0))

        self.message = tk.Label(self.root, text="", bg=BG, fg=YELLOW, font=("Segoe UI", 10),
                                wraplength=380, justify="left", anchor="w")
        self.message.pack(fill="x", pady=(10, 4), **pad)

        foot = tk.Frame(self.root, bg=BG)
        foot.pack(fill="x", pady=(4, 14), **pad)
        self.dir_label = tk.Label(foot, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w",
                                  wraplength=290, justify="left")
        self.dir_label.pack(side="left", fill="x", expand=True)
        link = tk.Label(foot, text="Đổi", bg=BG, fg=PINK, cursor="hand2", font=("Segoe UI", 9, "underline"))
        link.pack(side="left", padx=(6, 0))
        link.bind("<Button-1>", lambda _e: self.choose_olv_dir())
        if IS_WIN:
            sc = tk.Label(foot, text="Tạo lối tắt Desktop", bg=BG, fg=PINK, cursor="hand2", font=("Segoe UI", 9, "underline"))
            sc.pack(side="left", padx=(10, 0))
            sc.bind("<Button-1>", lambda _e: self.make_shortcut())

    def say(self, text, color=YELLOW):
        self.message.config(text=text, fg=color)

    def _refresh_dir_label(self):
        if self.olv_dir:
            self.dir_label.config(text=f"Open-LLM-VTuber: {self.olv_dir}")
        else:
            self.dir_label.config(text="Chưa tìm thấy thư mục Open-LLM-VTuber")

    def _set_status(self, key, color, text):
        dot, label = self.status_rows[key]
        dot.config(fg=color)
        label.config(text=text)

    # ---------- kiểm tra trạng thái (thread nền, không làm đơ giao diện)
    def _poll_status(self):
        while True:
            up = port_open(OLLAMA_PORT)
            self.models = ollama_models() if up else None
            self.ollama_up = up
            self.vtuber_up = port_open(VTUBER_PORT)
            time.sleep(1.5)

    def _required_models(self):
        names = []
        for name in (read_vtuber_model(self.olv_dir) if self.olv_dir else None, read_chat_model()):
            if name and name not in names:
                names.append(name)
        return names

    def tick(self):
        # Cập nhật đèn trạng thái
        if self.ollama_up:
            self._set_status("ollama", GREEN, "đang chạy")
        else:
            self._set_status("ollama", RED if not find_ollama() else MUTED,
                             "chưa cài — tải ở ollama.com" if not find_ollama() else "chưa bật (tự bật khi bấm Mở)")
        needed = self._required_models()
        if self.models is None:
            self._set_status("model", MUTED, ", ".join(needed) or "?")
        else:
            missing = [m for m in needed if not has_model(self.models, m)]
            if missing:
                self._set_status("model", RED, "thiếu: " + ", ".join(missing))
            else:
                self._set_status("model", GREEN, ", ".join(needed) + " — sẵn sàng")
        if self.vtuber_up:
            self._set_status("vtuber", GREEN, f"đang chạy — {VTUBER_URL}")
        elif self.pending == "vtuber":
            self._set_status("vtuber", YELLOW, "đang khởi động...")
        else:
            self._set_status("vtuber", MUTED, "đang tắt")

        self._advance()
        self.root.after(500, self.tick)

    def _advance(self):
        """Đi tiếp các bước của việc đang chờ (chạy trên thread giao diện)."""
        waited = time.time() - self.phase_started
        if self.phase == "wait_ollama":
            if self.ollama_up:
                self._after_ollama()
            elif waited > OLLAMA_WAIT_S:
                self._cancel("Đợi mãi không thấy Ollama. Mở app Ollama bằng tay rồi bấm lại nhé.", RED)
        elif self.phase == "wait_vtuber":
            if self.vtuber_up:
                self._cancel("Anna VTuber đã sẵn sàng! Cho phép dùng micro rồi nói chuyện thôi~", GREEN)
                self.open_browser()
            elif self.server_proc is not None and self.server_proc.poll() is not None:
                self._cancel("Server bị tắt giữa chừng. Xem cửa sổ server (hoặc thư mục logs) để biết lỗi.", RED)
                self.server_proc = None
            elif waited > VTUBER_WAIT_S:
                self._cancel("Server khởi động quá lâu. Mở cửa sổ server ở thanh taskbar xem có lỗi gì không.", RED)
            elif waited > 20:
                self.say(f"Đang khởi động Anna VTuber... ({int(waited)} giây)\n"
                         "Lần đầu sẽ tải model nghe giọng nên khá lâu, cứ để đó nha."
                         + ("\nLâu quá thì mở cửa sổ 'Anna VTuber server' ở taskbar xem có lỗi đỏ không."
                            if waited > 120 else ""))

    def _start_phase(self, pending, phase, msg):
        self.pending, self.phase, self.phase_started = pending, phase, time.time()
        self.say(msg)

    def _cancel(self, msg, color=YELLOW):
        self.pending = self.phase = None
        self.say(msg, color)

    # ---------- Ollama
    def _ensure_ollama(self):
        """Bật Ollama nếu chưa bật. Trả về False nếu không thể bật."""
        if self.ollama_up or port_open(OLLAMA_PORT):
            self.ollama_up = True
            return True
        app = _localappdata("Programs", "Ollama", "ollama app.exe")
        try:
            if app and Path(app).is_file():
                subprocess.Popen([app])
            else:
                exe = find_ollama()
                if not exe:
                    messagebox.showerror("Anna", "Chưa cài Ollama.\nTải ở https://ollama.com/download rồi mở lại bảng điều khiển.")
                    return False
                subprocess.Popen([exe, "serve"], creationflags=NO_WINDOW,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            messagebox.showerror("Anna", f"Không bật được Ollama: {e}")
            return False
        return True

    def _after_ollama(self):
        if self.pending == "chat":
            self._cancel("")
            self._launch_chat()
        elif self.pending == "vtuber":
            self._launch_server()

    # ---------- các nút
    def open_vtuber(self):
        if self.pending:
            return
        if self.vtuber_up:
            self.say("Anna VTuber đang chạy rồi, mở trang web luôn nè~", GREEN)
            self.open_browser()
            return
        if not self.olv_dir and not self.choose_olv_dir():
            return
        if not find_uv():
            messagebox.showerror("Anna", "Không tìm thấy uv.\nCài bằng lệnh:  winget install --id=astral-sh.uv -e")
            return
        if not self._ensure_ollama():
            return
        self._start_phase("vtuber", "wait_ollama", "Đang bật Ollama...")

    def _launch_server(self):
        uv = find_uv()
        try:
            if IS_WIN:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 7  # thu nhỏ xuống taskbar, không giành focus
                # cmd /k: nếu server lỗi, cửa sổ vẫn còn để đọc lỗi.
                # Truyền dạng chuỗi (không phải list) vì cmd không hiểu kiểu thoát \" của Python;
                # cmd sẽ bỏ cặp ngoặc ngoài cùng, còn lại: title ... & "uv.exe" run run_server.py
                cmdline = f'cmd /k "title Anna VTuber server & "{uv}" run run_server.py"'
                self.server_proc = subprocess.Popen(cmdline, cwd=self.olv_dir,
                                                    creationflags=NEW_CONSOLE, startupinfo=si)
            else:
                self.server_proc = subprocess.Popen([uv, "run", "run_server.py"], cwd=self.olv_dir,
                                                    start_new_session=True)
        except OSError as e:
            self._cancel(f"Không chạy được server: {e}", RED)
            return
        self.phase, self.phase_started = "wait_vtuber", time.time()
        self.say("Đang khởi động Anna VTuber... (cửa sổ server nằm thu nhỏ ở taskbar)")

    def open_chat(self):
        if self.pending:
            return
        if not self._ensure_ollama():
            return
        if self.ollama_up:
            self._launch_chat()
        else:
            self._start_phase("chat", "wait_ollama", "Đang bật Ollama...")

    def _launch_chat(self):
        py = sys.executable
        if IS_WIN and py.lower().endswith("python.exe"):
            pyw = py[:-len("python.exe")] + "pythonw.exe"
            py = pyw if Path(pyw).is_file() else py
        try:
            subprocess.Popen([py, str(HERE / "anna_lite_ui.py")], cwd=str(HERE))
            self.say("Đã mở cửa sổ chat~", GREEN)
        except OSError as e:
            self.say(f"Không mở được cửa sổ chat: {e}", RED)

    def open_browser(self):
        chrome = find_chrome()
        try:
            if chrome:  # mở dạng cửa sổ app gọn gàng, Chrome là trình duyệt dự án khuyên dùng
                subprocess.Popen([chrome, f"--app={VTUBER_URL}"])
            else:
                webbrowser.open(VTUBER_URL)
        except OSError:
            webbrowser.open(VTUBER_URL)

    def stop_vtuber(self):
        stopped = False
        if self.server_proc is not None and self.server_proc.poll() is None:
            kill_tree(self.server_proc.pid)
            stopped = True
        self.server_proc = None
        pid = pid_listening_on(VTUBER_PORT)
        if pid:
            kill_tree(pid)
            stopped = True
        if self.pending == "vtuber":
            self.pending = self.phase = None
        self.say("Đã tắt Anna VTuber." if stopped else "Anna VTuber đang không chạy.", MUTED)

    def choose_olv_dir(self):
        path = filedialog.askdirectory(title="Chọn thư mục Open-LLM-VTuber")
        if not path:
            return False
        if not is_olv_dir(path):
            messagebox.showerror("Anna", "Thư mục này không có run_server.py,\nkhông phải thư mục Open-LLM-VTuber.")
            return False
        self.olv_dir = path
        self.settings["olv_dir"] = path
        save_settings(self.settings)
        self._refresh_dir_label()
        return True

    def make_shortcut(self):
        bat = str(HERE / "Mo_Anna.bat").replace("'", "''")
        workdir = str(HERE).replace("'", "''")
        icon = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "shell32.dll") + ",43"
        ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut("
              "[Environment]::GetFolderPath('Desktop')+'\\Anna.lnk');"
              f"$s.TargetPath='{bat}';$s.WorkingDirectory='{workdir}';$s.WindowStyle=7;"
              f"$s.IconLocation='{icon}';$s.Description='Anna';$s.Save()")
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           capture_output=True, text=True, creationflags=NO_WINDOW)
        if r.returncode == 0:
            self.say("Đã tạo lối tắt 'Anna' ngoài Desktop. Lần sau bấm đúp là mở~", GREEN)
        else:
            self.say("Không tạo được lối tắt: " + (r.stderr or "").strip()[:200], RED)

    def on_close(self):
        if self.server_proc is not None and self.server_proc.poll() is None:
            if messagebox.askyesno("Anna", "Tắt luôn Anna VTuber?\n(Chọn No để Anna vẫn chạy sau khi đóng bảng điều khiển)"):
                self.stop_vtuber()
        self.root.destroy()


def main():
    root = tk.Tk()
    Launcher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
