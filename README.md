# Anna Lite

Trợ lý AI cà khịa dễ thương, chạy local với UI cơ bản.
Your sassy assistant watching your every move 👀✨

## Chạy nhanh

1. Chuẩn bị model local (offline): xem hướng dẫn chi tiết ở
   [docs/CHAY_MODEL_OFFLINE.md](docs/CHAY_MODEL_OFFLINE.md)
   (mặc định dùng `Qwen3.5-4B-heretic` qua Ollama).
2. Chat với Anna:

```bash
python anna_lite_ui.py    # cửa sổ chat
python anna_llm.py        # hoặc chat trong terminal
```

## Các file

| File | Vai trò |
|---|---|
| `anna_lite_ui.py` | Giao diện chat Tkinter |
| `anna_llm.py` | Kết nối tới model local (Ollama / llama.cpp / LM Studio) |
| `model_config.json` | Địa chỉ server, tên model, nhiệt độ, độ dài trả lời... |
| `personality_config.json` | Tính cách, lời chào, câu nhắc của Anna |
| `Modelfile` | Dùng để tạo model `anna-qwen` trong Ollama |
