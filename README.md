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

Anna hiện chữ dần khi đang trả lời và nhớ chuyện cũ giữa các lần mở (gõ `/reset` hoặc bấm "Xóa trí nhớ" để quên).

**Muốn Anna có hình Live2D, giọng nói, hoặc chạy trên điện thoại?** Xem
[docs/ANNA_VTUBER_VA_DIEN_THOAI.md](docs/ANNA_VTUBER_VA_DIEN_THOAI.md).

## Các file

| File | Vai trò |
|---|---|
| `anna_lite_ui.py` | Giao diện chat Tkinter |
| `anna_llm.py` | Kết nối tới model local (Ollama / llama.cpp / LM Studio) |
| `model_config.json` | Địa chỉ server, tên model, nhiệt độ, độ dài trả lời, trí nhớ... |
| `personality_config.json` | Tính cách, lời chào, câu nhắc của Anna |
| `Modelfile` | Dùng để tạo model `anna-qwen` trong Ollama |
| `integrations/open-llm-vtuber/anna_vi.yaml` | Nhân vật Anna (tiếng Việt) cho Open-LLM-VTuber |
| `integrations/open-llm-vtuber/apply_anna.py` | Đưa Anna vào `conf.yaml` của Open-LLM-VTuber |
| `scripts/cai_open_llm_vtuber.ps1` | Cài Open-LLM-VTuber + Anna trên Windows chỉ với 1 lệnh |
