"""Bộ não của Anna: nói chuyện với model chạy LOCAL trên máy (không cần internet).

Anna gọi tới một server local có API kiểu OpenAI (/v1/chat/completions).
Cả 3 công cụ phổ biến đều có sẵn API này:
  - Ollama          -> http://localhost:11434/v1
  - llama.cpp       -> http://localhost:8080/v1   (lệnh `llama-server`)
  - LM Studio       -> http://localhost:1234/v1

Chỉ dùng thư viện chuẩn của Python, không cần `pip install` gì thêm.
Chạy thử trong terminal:  python anna_llm.py
"""

import http.client
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_MODEL_CONFIG = {
    "base_url": "http://localhost:11434/v1",
    "model": "anna-qwen",
    "api_key": "local",
    "temperature": 0.7,
    "top_p": 0.8,
    "max_tokens": 512,
    "timeout": 180,
    "max_history_turns": 10,
    "disable_thinking": True,
    "stream": True,
    "memory_file": "anna_memory.json",
}

DEFAULT_PERSONALITY = {
    "greeting": "Chào sếp! Anna sẵn sàng phục vụ~",
    "idle_reminder": "Sếp ơi, lâu rồi không làm gì hết á ~!",
    "system_prompt": "Bạn là Anna, trợ lý AI dễ thương, hay cà khịa. Trả lời bằng tiếng Việt.",
}

MAX_SAVED_MESSAGES = 200  # trí nhớ lưu ra file tối đa bao nhiêu tin nhắn
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


class LocalLLMError(RuntimeError):
    """Lỗi khi không nói chuyện được với model local."""


def load_json(name, defaults):
    """Đọc file JSON cạnh script; thiếu file hoặc thiếu khóa thì dùng mặc định."""
    path = BASE_DIR / name
    data = dict(defaults)
    if path.exists():
        with path.open(encoding="utf-8") as f:
            data.update(json.load(f))
    return data


def strip_thinking(text, final=True):
    """Bỏ phần suy nghĩ <think>...</think> mà dòng Qwen hay sinh ra.

    final=False dùng khi đang stream: giấu luôn khối <think> chưa đóng
    và mẩu thẻ "<thi..." còn dở ở cuối, để không lộ ra màn hình.
    """
    text = _THINK_BLOCK.sub("", text)
    # Một số chat template mở sẵn <think> trong prompt, nên output chỉ có thẻ đóng.
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    if not final:
        if "<think>" in text:
            text = text.split("<think>", 1)[0]
        for i in range(len("<think>") - 1, 0, -1):
            if text.endswith("<think>"[:i]):
                text = text[:-i]
                break
    return text.strip()


class AnnaBrain:
    def __init__(self, model_config=None, personality=None):
        self.config = model_config or load_json("model_config.json", DEFAULT_MODEL_CONFIG)
        self.personality = personality or load_json("personality_config.json", DEFAULT_PERSONALITY)
        self.history = self._load_memory()

    # ---------- trí nhớ ----------
    def _memory_path(self):
        name = self.config.get("memory_file")
        return BASE_DIR / name if name else None

    def _load_memory(self):
        path = self._memory_path()
        if not path or not path.exists():
            return []
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            return [m for m in data if m.get("role") in ("user", "assistant") and m.get("content")]
        except (OSError, ValueError, AttributeError):
            return []  # file hỏng thì bỏ qua, coi như mới quen

    def _save_memory(self):
        path = self._memory_path()
        if not path:
            return
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(self.history[-MAX_SAVED_MESSAGES:], f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def reset(self):
        self.history.clear()
        self._save_memory()

    # ---------- gọi model ----------
    def _messages(self):
        keep = int(self.config.get("max_history_turns", 10)) * 2
        recent = self.history[-keep:] if keep > 0 else []
        return [{"role": "system", "content": self.personality["system_prompt"]}] + recent

    def _payload(self, stream):
        payload = {
            "model": self.config["model"],
            "messages": self._messages(),
            "temperature": self.config.get("temperature", 0.7),
            "top_p": self.config.get("top_p", 0.8),
            "max_tokens": self.config.get("max_tokens", 512),
            "stream": stream,
        }
        if self.config.get("disable_thinking"):
            # llama.cpp và LM Studio đọc khóa này để tắt chế độ "thinking" của Qwen;
            # Ollama bỏ qua nó (thinking của Ollama nằm ở trường riêng, không lẫn vào câu trả lời).
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        return payload

    def _open(self, payload):
        url = self.config["base_url"].rstrip("/") + "/chat/completions"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + str(self.config.get("api_key", "local")),
            },
            method="POST",
        )
        try:
            return urllib.request.urlopen(req, timeout=self.config.get("timeout", 180))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            raise LocalLLMError(f"Server local báo lỗi {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise LocalLLMError(
                f"Không kết nối được tới {url} ({e}). "
                "Sếp đã bật Ollama / llama-server / LM Studio chưa?"
            ) from e

    def _complete(self, on_update):
        """Trả về toàn bộ chữ thô model sinh ra; gọi on_update(chữ_hiển_thị) khi có chữ mới."""
        stream = bool(self.config.get("stream", True))
        try:
            with self._open(self._payload(stream)) as resp:
                if not stream:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"].get("content") or ""
                raw = ""
                for line in resp:
                    line = line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    choices = json.loads(chunk).get("choices") or []
                    piece = (choices[0].get("delta") or {}).get("content") if choices else None
                    if piece:
                        raw += piece
                        if on_update:
                            on_update(strip_thinking(raw, final=False))
                return raw
        except (TimeoutError, ConnectionError, urllib.error.URLError, http.client.HTTPException) as e:
            raise LocalLLMError(f"Mất kết nối giữa chừng: {e}") from e

    def ask(self, user_text, on_update=None):
        """Gửi một câu cho Anna, trả về câu trả lời hoàn chỉnh (đã bỏ phần <think>).

        on_update: hàm tùy chọn, được gọi liên tục với phần chữ đã sinh tới lúc đó
        (để UI hiện chữ dần dần thay vì chờ cả câu).
        """
        self.history.append({"role": "user", "content": user_text})
        try:
            reply = strip_thinking(self._complete(on_update))
        except LocalLLMError:
            self.history.pop()
            raise
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            self.history.pop()
            raise LocalLLMError(f"Server trả về dữ liệu lạ: {e}") from e
        if not reply:
            reply = "...Anna đơ mất rồi, sếp hỏi lại nha~"
        self.history.append({"role": "assistant", "content": reply})
        self._save_memory()
        return reply


def main():
    brain = AnnaBrain()
    print(f"[model: {brain.config['model']} @ {brain.config['base_url']}]")
    if brain.history:
        print(f"[Anna còn nhớ {len(brain.history) // 2} lượt chat trước]")
    print("Anna:", brain.personality["greeting"])
    print("(gõ 'exit' để thoát, '/reset' để xóa trí nhớ)\n")
    while True:
        try:
            text = input("Sếp: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text.lower() in {"exit", "quit", "thoát"}:
            break
        if text == "/reset":
            brain.reset()
            print("Anna: Quên sạch rồi nha~\n")
            continue

        shown = ""

        def show(visible):
            nonlocal shown
            if visible.startswith(shown):  # chỉ in phần chữ mới
                sys.stdout.write(visible[len(shown):])
                sys.stdout.flush()
                shown = visible

        sys.stdout.write("Anna: ")
        sys.stdout.flush()
        try:
            reply = brain.ask(text, on_update=show)
            if reply.startswith(shown):
                sys.stdout.write(reply[len(shown):])
            else:
                sys.stdout.write("\n" + reply)
            print("\n")
        except LocalLLMError as e:
            print("\n[Lỗi]", e, "\n")


if __name__ == "__main__":
    main()
