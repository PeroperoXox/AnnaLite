# Anna: chat, VTuber có giọng nói, và chạy trên điện thoại

Có 3 cách dùng Anna, từ nhẹ tới xịn:

| Cách | Có gì | Máy cần |
|---|---|---|
| **1. AnnaLite** (repo này) | Cửa sổ chat chữ, nhẹ, hiện chữ dần, nhớ chuyện cũ | Laptop của sếp chạy tốt |
| **2. Open-LLM-VTuber** | Nhân vật Live2D biết cử động, **nói chuyện bằng giọng**, nghe sếp nói | Chạy được, nhưng nặng hơn |
| **3. Điện thoại** (Z Fold 8) | Chat chữ trên điện thoại, offline | Điện thoại flagship chạy model 4B ổn |

Cả 3 cách dùng **chung một model** `anna-qwen` (Qwen3.5-4B-heretic).
Làm bước chuẩn bị model trong [CHAY_MODEL_OFFLINE.md](CHAY_MODEL_OFFLINE.md) trước.

---

## Cách 1 — Chat với Anna bằng AnnaLite

```powershell
# 1) Tạo model trong Ollama (chỉ làm 1 lần, đứng trong thư mục AnnaLite)
ollama create anna-qwen -f Modelfile

# 2) Mở cửa sổ chat
python anna_lite_ui.py

#    hoặc chat trong terminal
python anna_llm.py
```

- Chữ hiện dần ngay khi model đang nghĩ, không phải chờ hết câu.
- Anna **nhớ chuyện cũ** giữa các lần mở (lưu ở `anna_memory.json` trên máy sếp,
  không đẩy lên GitHub). Bấm **Xóa trí nhớ** (hoặc gõ `/reset`) để bắt đầu lại.

**Chưa có file GGUF của bản heretic?** Dùng tạm model chính thức của Ollama:
`ollama pull qwen3.5:4b`, rồi sửa `model_config.json`: `"model": "qwen3.5:4b"`.
Bản chính thức có thể "suy nghĩ" trước khi trả lời nên chậm hơn, và hay từ chối hơn bản heretic.

**Mẹo cho laptop RTX 2050 (4 GB):**
- Cắm sạc khi dùng.
- Mặc định Ollama tắt model sau 5 phút không dùng, lần hỏi sau phải đợi nạp lại.
  Muốn giữ model luôn sẵn sàng: `setx OLLAMA_KEEP_ALIVE -1` rồi khởi động lại Ollama.
- Đừng chạy Anna và Claude Code (`ollama launch claude`) cùng lúc, 2 model sẽ giành card đồ họa.

---

## Cách 2 — Anna thành VTuber với Open-LLM-VTuber

**Có phải chỉ cần cài model heretic vào là xong?** Gần đúng, nhưng thiếu 3 thứ:

1. **Model chat:** đổi sang `anna-qwen` trong Ollama ✅ (dễ)
2. **Nghe tiếng Việt:** bộ nhận giọng mặc định (SenseVoice) **không hiểu tiếng Việt**, phải đổi sang Whisper.
3. **Nói tiếng Việt:** giọng mặc định là tiếng Anh, phải đổi sang giọng Việt.
   Muốn offline thì dùng Piper.

Cả 3 thứ đã gói sẵn trong file nhân vật
[`integrations/open-llm-vtuber/anna_vi.yaml`](../integrations/open-llm-vtuber/anna_vi.yaml),
kèm tính cách của Anna, được chỉnh để nói ngắn, không emoji (cho hợp giọng nói).
Script cài đặt bên dưới sẽ tự đưa file này vào `conf.yaml`.

> Không nên tự làm lại cả Open-LLM-VTuber trong AnnaLite: dự án đó đã làm rất kỹ
> (Live2D, ngắt lời khi đang nói, chống AI nghe lại giọng của chính nó...).
> Dùng nó và chỉ thêm "linh hồn" Anna vào là hợp lý nhất.

### Cài đặt tự động (khuyên dùng, cần mạng lần đầu)

Script `scripts/cai_open_llm_vtuber.ps1` làm hết các bước trong
[hướng dẫn chính thức](https://docs.llmvtuber.com/en/docs/quick-start), cộng thêm phần tiếng Việt:
cài Git, FFmpeg, uv → tải Open-LLM-VTuber (có `--recursive`) → `uv sync` →
thêm `faster-whisper` và `piper-tts` → tải giọng Piper tiếng Việt → đưa Anna vào `conf.yaml`
để Anna là nhân vật mặc định.

Mở **PowerShell** trong thư mục AnnaLite:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\cai_open_llm_vtuber.ps1
```

Tùy chọn:

| Thêm vào cuối lệnh | Tác dụng |
|---|---|
| `-Model qwen3.5:4b` | Dùng model Ollama khác (khi chưa có `anna-qwen`) |
| `-Lan` | Cho điện thoại cùng Wi-Fi mở được giao diện |
| `-InstallDir D:\AI\Open-LLM-VTuber` | Cài chỗ khác (mặc định `C:\Users\<tên>\Open-LLM-VTuber`). **Đường dẫn không được có dấu.** |

- Bước `uv sync` lần đầu khá lâu (tải PyTorch...), cứ để nó chạy.
- Chạy lại script bao nhiêu lần cũng được, bước nào xong rồi sẽ bỏ qua.
- **Không cần** cài CUDA Toolkit / cuDNN như hướng dẫn gốc nhắc tới: Ollama đã kèm sẵn
  phần chạy GPU, còn nghe/nói của Anna chạy bằng CPU.
- `conf.yaml` cũ (nếu có) được sao lưu thành `conf.yaml.truoc-anna.bak`.

### Chạy

```powershell
cd $HOME\Open-LLM-VTuber
uv run run_server.py
```

- Đợi tới dòng `Uvicorn running on ...`, rồi mở **Chrome** (dự án chỉ khuyên dùng Chrome):
  <http://localhost:12393> → cho phép dùng micro → nói chuyện thôi.
- Lần chạy đầu sẽ tự tải model nghe giọng Whisper (~500 MB), cần có mạng. Các lần sau chạy offline.
- Muốn có app riêng hoặc chế độ "thú cưng" nằm trên desktop: tải file `.exe` `open-llm-vtuber-electron`
  ở [Open-LLM-VTuber-Web Releases](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber-Web/releases/latest).
  App này cần server (`uv run run_server.py`) đang chạy.

### Cài tay (nếu script lỗi)

```powershell
winget install Git.Git
winget install Gyan.FFmpeg
winget install --id=astral-sh.uv -e
# đóng PowerShell, mở lại

git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber --recursive
cd Open-LLM-VTuber
uv sync
uv add faster-whisper piper-tts
```

Tải 2 file `vi_VN-vais1000-medium.onnx` và `vi_VN-vais1000-medium.onnx.json` ở
<https://huggingface.co/rhasspy/piper-voices/tree/main/vi/vi_VN/vais1000/medium>,
bỏ vào `Open-LLM-VTuber\models\piper\`. Rồi đưa Anna vào cấu hình (sửa đường dẫn AnnaLite cho đúng):

```powershell
uv run python ..\AnnaLite\integrations\open-llm-vtuber\apply_anna.py .
```

### Lỗi thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| Web hiện `{"detail":"Not Found"}` | Thiếu giao diện: `git submodule update --init --recursive` trong thư mục Open-LLM-VTuber |
| `Error calling the chat endpoint` | Ollama chưa bật, hoặc tên model sai: gõ `ollama list` xem tên, chạy lại script với `-Model <tên>` |
| Lỗi thiếu file âm thanh | Chưa có FFmpeg: `winget install Gyan.FFmpeg`, mở lại PowerShell |
| `Model not found: models/piper/...` | Chưa tải giọng Piper (xem phần cài tay ở trên) |
| Bật VPN/proxy thì không gọi được Ollama | Tắt proxy, hoặc cho proxy bỏ qua `localhost` |

### Nếu máy chạy không nổi

Laptop RTX 2050 phải gánh 3 thứ cùng lúc: model chat (trên card đồ họa), Whisper và Piper (trên CPU).
- Anna nghe chậm: giữ Whisper `small`. Nghe sai nhiều thì thử `medium` (chậm hơn).
- Muốn giọng hay hơn và chấp nhận dùng mạng: trong `anna_vi.yaml` đổi
  `tts_model: 'piper_tts'` thành `tts_model: 'edge_tts'` (giọng HoaiMy của Microsoft).
- Gõ chữ thay vì nói vẫn được, ô chat có trên giao diện web.

---

## Cách 3 — Anna trên Z Fold 8

### 3a. Điện thoại tự chạy model, offline 100% (khuyên dùng)

Z Fold 8 là máy flagship nên chạy model 4B bản Q4 khá mượt.

1. Cài app **PocketPal AI** (miễn phí, trên Google Play). App này chạy file GGUF ngay trên điện thoại.
2. Copy file `anna-qwen-Q4_K_M.gguf` (~2,7 GB, đã làm ở bước chuẩn bị model) từ máy tính
   sang điện thoại qua cáp USB hoặc Quick Share.
3. Trong PocketPal: **Models → + → Add Local Model** → chọn file vừa copy → **Load**.
4. Tạo một **Pal** tên Anna, dán `system_prompt` trong `personality_config.json` vào phần
   **System prompt**. Vậy là Anna có tính cách y như trên máy tính.
5. Tắt mạng, chat thử.

> App báo lỗi không nạp được model ("unknown architecture"...)? Qwen3.5 khá mới,
> cập nhật PocketPal lên bản mới nhất. Vẫn lỗi thì tìm và tải bản `Qwen3.5-4B` GGUF
> ngay trong app (mục tìm model trên Hugging Face).

Cách này không có Live2D hay giọng nói, nhưng mang Anna đi đâu cũng được.

### 3b. Dùng giao diện VTuber của máy tính trên điện thoại (cùng Wi-Fi)

Máy tính chạy Open-LLM-VTuber, điện thoại chỉ mở web. Không cần internet, chỉ cần
2 máy chung một mạng Wi-Fi.

1. Chạy lại script cài đặt với `-Lan` (hoặc tự sửa `host: 'localhost'` thành `host: '0.0.0.0'`
   trong `conf.yaml` của Open-LLM-VTuber), rồi chạy lại server. Windows hỏi tường lửa thì bấm **Allow**.
2. Xem IP máy tính: gõ `ipconfig`, tìm dòng **IPv4 Address** (ví dụ `192.168.1.5`).
3. Trên điện thoại, mở **Chrome**: `http://192.168.1.5:12393`.
4. **Micro sẽ không chạy**, vì trình duyệt chỉ cho dùng micro trên trang `https`. Cách khắc phục:
   mở `chrome://flags/#unsafely-treat-insecure-origin-as-secure` trên Chrome điện thoại,
   điền `http://192.168.1.5:12393`, chọn **Enabled**, rồi khởi động lại Chrome.
   (Hoặc cứ gõ chữ, không cần micro.)

### 3c. (Nâng cao) Chạy đúng code AnnaLite trên điện thoại bằng Termux

Cài **Termux** (từ F-Droid), rồi trong Termux:

```bash
pkg install python git llama-cpp
git clone https://github.com/PeroperoXox/AnnaLite && cd AnnaLite
# copy file gguf vào ~/AnnaLite/models/ trước, rồi:
llama-server -m models/anna-qwen-Q4_K_M.gguf --port 8080 -c 4096 --jinja &
```

Sửa `model_config.json`: `"base_url": "http://localhost:8080/v1"`, rồi chạy `python anna_llm.py`.
Cửa sổ Tkinter không chạy trên điện thoại, chỉ có bản chat trong terminal.
Nếu `pkg install llama-cpp` không có gói, xem hướng dẫn build llama.cpp cho Android trên GitHub của llama.cpp.
