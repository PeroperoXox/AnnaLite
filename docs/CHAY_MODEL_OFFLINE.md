# Chạy Anna với model local, offline 100%

Model: [`saidutta69/Qwen3.5-4B-heretic`](https://huggingface.co/saidutta69/Qwen3.5-4B-heretic)
(bản Qwen3.5 4B đã được "heretic" gỡ bớt kiểu từ chối của model gốc).

Ý tưởng: **chỉ cần internet một lần** để tải model và phần mềm. Sau đó rút mạng,
Anna vẫn chạy bình thường vì mọi thứ nằm trên máy sếp.

```
[Anna UI (Tkinter)] --HTTP localhost--> [Ollama / llama.cpp / LM Studio] --> [file .gguf trên ổ cứng]
```

---

## 0. Máy có chạy nổi không?

Model 4 tỷ tham số. Nên dùng bản **nén GGUF Q4_K_M**:

| Bản | Dung lượng file | RAM/VRAM cần | Ghi chú |
|---|---|---|---|
| Q4_K_M (khuyên dùng) | ~2,5–3 GB | ~4–6 GB | Chạy được bằng CPU, laptop 8 GB RAM vẫn ổn |
| Q8_0 | ~4,5 GB | ~6–8 GB | Khôn hơn chút, chậm hơn |
| Gốc BF16 (safetensors) | ~8–9 GB | ~10+ GB | Không cần thiết cho Anna |

- Chỉ có CPU: chạy được, tốc độ khoảng vài đến ~15 chữ/giây tùy máy.
- Có card NVIDIA ≥ 4 GB VRAM: nhanh hơn nhiều.

---

## 1. (Cần mạng) Lấy file GGUF

Repo trên Hugging Face hiện là định dạng gốc (safetensors). Mấy app chạy local
cần định dạng **GGUF**, nên có 2 cách:

### Cách A — Tìm bản GGUF có sẵn (dễ nhất)

Vào trang model → khung **Model tree** bên phải → mục **Quantizations**.
Nếu có ai đã đăng bản GGUF (thường tên kiểu `...-GGUF`), tải file
`*Q4_K_M.gguf` về, đổi tên thành `anna-qwen-Q4_K_M.gguf` rồi để vào thư mục
`models/` của project. Xong, qua bước 2.

> Nếu repo GGUF đó có sẵn, với Ollama còn có thể chạy thẳng:
> `ollama run hf.co/<tên-người-đăng>/<tên-repo-GGUF>:Q4_K_M`
> (lần đầu tự tải, những lần sau chạy offline).

### Cách B — Tự chuyển sang GGUF bằng llama.cpp

Cần Python 3.10+ và git.

```bash
# 1) Tải model gốc (~8–9 GB)
pip install -U "huggingface_hub[cli]"
hf download saidutta69/Qwen3.5-4B-heretic --local-dir models/Qwen3.5-4B-heretic
#   (bản huggingface_hub cũ thì dùng: huggingface-cli download ... )

# 2) Lấy công cụ chuyển đổi của llama.cpp
git clone --depth 1 https://github.com/ggml-org/llama.cpp
pip install -r llama.cpp/requirements.txt

# 3) Chuyển sang GGUF (bản f16, file trung gian)
python llama.cpp/convert_hf_to_gguf.py models/Qwen3.5-4B-heretic \
    --outfile models/anna-qwen-f16.gguf --outtype f16

# 4) Nén xuống Q4_K_M
llama-quantize models/anna-qwen-f16.gguf models/anna-qwen-Q4_K_M.gguf Q4_K_M
```

- `llama-quantize` có sẵn trong bản build của llama.cpp: tải file zip ở trang
  [Releases](https://github.com/ggml-org/llama.cpp/releases)
  (Windows: chọn `...-bin-win-cpu-x64.zip`, hoặc bản `cuda` nếu có card NVIDIA).
- Nếu bước 3 báo lỗi kiểu *"Model architecture ... is not supported"* thì
  llama.cpp đang cũ, `git pull` bản mới nhất rồi chạy lại (Qwen3.5 là kiến trúc mới).
- Qwen3.5 có cả phần đọc ảnh, nhưng Anna chỉ cần chat chữ nên bước trên chỉ
  chuyển phần ngôn ngữ là đủ.
- Xong có thể xóa `models/Qwen3.5-4B-heretic` và `anna-qwen-f16.gguf` cho đỡ tốn ổ.

---

## 2. (Cần mạng) Cài phần mềm chạy model — chọn 1

| Công cụ | Ưu điểm | Địa chỉ server |
|---|---|---|
| **Ollama** (khuyên dùng) | Dễ nhất, tự chạy nền | `http://localhost:11434/v1` |
| **llama.cpp** (`llama-server`) | Nhẹ, nhanh, không cần cài | `http://localhost:8080/v1` |
| **LM Studio** | Có giao diện, bấm chuột là xong | `http://localhost:1234/v1` |

Tải Ollama: <https://ollama.com/download>

---

## 3. (Offline từ đây) Bật model

### Với Ollama

Đứng ở thư mục project (có file `Modelfile`):

```bash
ollama create anna-qwen -f Modelfile
ollama run anna-qwen          # chat thử trong terminal, gõ /bye để thoát
```

Ollama tự chạy server nền ở cổng 11434. `model_config.json` mặc định đã trỏ
sẵn tới đây với tên model `anna-qwen`, **không cần sửa gì**.

### Với llama.cpp

```bash
llama-server -m models/anna-qwen-Q4_K_M.gguf --port 8080 -c 8192 --jinja
#   có GPU NVIDIA thì thêm:  -ngl 99
```

Sửa `model_config.json`:

```json
"base_url": "http://localhost:8080/v1",
```

### Với LM Studio

Mở LM Studio → *My Models* → import file `.gguf` → tab *Developer* → *Start Server*.
Sửa `model_config.json`: `"base_url": "http://localhost:1234/v1"` và
`"model"` là tên model hiện trong LM Studio.

---

## 4. Chạy Anna

```bash
python anna_llm.py        # chat trong terminal (để test nhanh)
python anna_lite_ui.py    # mở cửa sổ chat Tkinter
```

Không cần `pip install` gì thêm, Anna chỉ dùng thư viện chuẩn của Python.

Muốn chắc là offline thật: tắt Wi-Fi rồi chat thử. 😎

---

## Tùy chỉnh

- **Tính cách Anna**: sửa `system_prompt` trong `personality_config.json`.
- **`model_config.json`**:
  - `temperature`: càng cao càng "bay", càng thấp càng nghiêm túc (0.6–0.8 là vừa).
  - `max_tokens`: độ dài tối đa mỗi câu trả lời.
  - `max_history_turns`: Anna nhớ bao nhiêu lượt chat gần nhất.
  - `disable_thinking`: `true` = tắt chế độ "suy nghĩ" của Qwen, trả lời nhanh hơn.
    Code cũng tự lọc phần `<think>...</think>` nếu model vẫn sinh ra.
  - `stream`: `true` = chữ hiện dần trong lúc model đang sinh.
  - `memory_file`: file lưu trí nhớ giữa các lần mở Anna. Để `""` nếu không muốn Anna nhớ.

## Lỗi thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| `Không kết nối được tới http://localhost:...` | Chưa bật Ollama / llama-server, hoặc sai cổng trong `model_config.json` |
| `Server local báo lỗi 404 ... model not found` | Tên `model` trong `model_config.json` khác tên đã `ollama create` |
| Trả lời rất chậm | Dùng bản Q4_K_M, giảm `max_tokens`, bật GPU (`-ngl 99` với llama.cpp) |
| Trả lời lan man, tự nói chuyện một mình | Kiểm tra đã dùng `Modelfile` (Ollama) hoặc cờ `--jinja` (llama.cpp) chưa |
| `ModuleNotFoundError: tkinter` (Linux) | `sudo apt install python3-tk` |
