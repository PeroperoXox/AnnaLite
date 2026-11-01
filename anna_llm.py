"""Bộ não của Anna: nói chuyện với model chạy LOCAL trên máy (không cần internet).

Anna gọi tới một server local có API kiểu OpenAI (/v1/chat/completions).
Cả 3 công cụ phổ biến đều có sẵn API này:
  - Ollama          -> http://localhost:11434/v1
  - llama.cpp       -> http://localhost:8080/v1   (lệnh `llama-server`)
  - LM Studio       -> http://localhost:1234/v1

Chỉ dùng thư viện chuẩn của Python, không cần `pip install` gì thêm.
Chạy thử trong terminal:  python anna_llm.py
"""

import json
import re
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
}

DEFAULT_PERSONALITY = {
    "greeting": "Chào sếp! Anna sẵn sàng phục vụ~",
    "idle_reminder": "Sếp ơi, lâu rồi không làm gì hết á ~!",
    "system_prompt": "Bạn là Anna, trợ lý AI dễ thương, hay cà khịa. Trả lời bằng tiếng Việt.",
}

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


def strip_thinking(text):
    """Bỏ phần suy nghĩ <think>...</think> mà dòng Qwen hay sinh ra."""
    text = _THINK_BLOCK.sub("", text)
    # Một số chat template mở sẵn <think> trong prompt, nên output chỉ có thẻ đóng.
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


class AnnaBrain:
    def __init__(self, model_config=None, personality=None):
        self.config = model_config or load_json("model_config.json", DEFAULT_MODEL_CONFIG)
        self.personality = personality or load_json("personality_config.json", DEFAULT_PERSONALITY)
        self.history = []

    def reset(self):
        self.history.clear()

    def _messages(self):
        keep = int(self.config.get("max_history_turns", 10)) * 2
        recent = self.history[-keep:] if keep > 0 else []
        return [{"role": "system", "content": self.personality["system_prompt"]}] + recent

    def _payload(self):
        payload = {
            "model": self.config["model"],
            "messages": self._messages(),
            "temperature": self.config.get("temperature", 0.7),
            "top_p": self.config.get("top_p", 0.8),
            "max_tokens": self.config.get("max_tokens", 512),
            "stream": False,
        }
        if self.config.get("disable_thinking"):
            # llama.cpp và LM Studio đọc khóa này để tắt chế độ "thinking" của Qwen;
            # Ollama bỏ qua nó (thinking của Ollama nằm ở trường riêng, không lẫn vào câu trả lời).
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        return payload

    def _post(self, payload):
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
            with urllib.request.urlopen(req, timeout=self.config.get("timeout", 180)) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            raise LocalLLMError(f"Server local báo lỗi {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise LocalLLMError(
                f"Không kết nối được tới {url} ({e}). "
                "Sếp đã bật Ollama / llama-server / LM Studio chưa?"
            ) from e

    def ask(self, user_text):
        """Gửi một câu cho Anna, trả về câu trả lời (đã bỏ phần <think>)."""
        self.history.append({"role": "user", "content": user_text})
        try:
            data = self._post(self._payload())
            reply = strip_thinking(data["choices"][0]["message"].get("content") or "")
        except LocalLLMError:
            self.history.pop()
            raise
        except (KeyError, IndexError, TypeError, ValueError) as e:
            self.history.pop()
            raise LocalLLMError(f"Server trả về dữ liệu lạ: {e}") from e
        if not reply:
            reply = "...Anna đơ mất rồi, sếp hỏi lại nha~"
        self.history.append({"role": "assistant", "content": reply})
        return reply


def main():
    brain = AnnaBrain()
    print(f"[model: {brain.config['model']} @ {brain.config['base_url']}]")
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
        try:
            print("Anna:", brain.ask(text), "\n")
        except LocalLLMError as e:
            print("[Lỗi]", e, "\n")


if __name__ == "__main__":
    main()
