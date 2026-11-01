"""Đưa nhân vật Anna (anna_vi.yaml) vào conf.yaml của Open-LLM-VTuber, để Anna là nhân vật mặc định.

Chạy bên trong thư mục Open-LLM-VTuber (để dùng ruamel.yaml có sẵn của nó):
    uv run python <đường-dẫn>/AnnaLite/integrations/open-llm-vtuber/apply_anna.py .
    uv run python <...>/apply_anna.py . --lan      # cho điện thoại cùng Wi-Fi truy cập
    uv run python <...>/apply_anna.py . --model qwen3.5:4b   # dùng model khác

- Chưa có conf.yaml thì tạo từ config_templates/conf.default.yaml.
- Lần đầu sẽ sao lưu conf.yaml cũ thành conf.yaml.truoc-anna.bak.
- Chỉ ghi đè những mục có trong anna_vi.yaml, giữ nguyên phần còn lại và các dòng chú thích.
"""

import argparse
import shutil
import sys
from pathlib import Path

from ruamel.yaml import YAML

HERE = Path(__file__).resolve().parent


def deep_merge(dst, src):
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            deep_merge(dst[key], value)
        else:
            dst[key] = value


def main():
    parser = argparse.ArgumentParser(description="Đưa Anna vào conf.yaml của Open-LLM-VTuber")
    parser.add_argument("olv_dir", help="Thư mục Open-LLM-VTuber")
    parser.add_argument("--anna", default=str(HERE / "anna_vi.yaml"), help="File nhân vật Anna")
    parser.add_argument("--lan", action="store_true", help="Mở cho máy khác cùng Wi-Fi (host 0.0.0.0)")
    parser.add_argument("--model", help="Tên model Ollama muốn dùng thay cho anna-qwen (vd: qwen3.5:4b)")
    args = parser.parse_args()

    olv = Path(args.olv_dir).resolve()
    conf_path = olv / "conf.yaml"
    template = olv / "config_templates" / "conf.default.yaml"
    if not template.exists():
        sys.exit(f"[Lỗi] Không thấy {template}. '{olv}' có đúng là thư mục Open-LLM-VTuber không?")

    if not conf_path.exists():
        shutil.copyfile(template, conf_path)
        print(f"Đã tạo conf.yaml từ {template.name}")
    backup = olv / "conf.yaml.truoc-anna.bak"
    if not backup.exists():
        shutil.copyfile(conf_path, backup)
        print(f"Đã sao lưu conf.yaml cũ -> {backup.name}")

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    conf = yaml.load(conf_path.read_text(encoding="utf-8-sig"))
    anna = yaml.load(Path(args.anna).read_text(encoding="utf-8"))

    deep_merge(conf["character_config"], anna["character_config"])
    if args.model:
        conf["character_config"]["agent_config"]["llm_configs"]["ollama_llm"]["model"] = args.model
    if args.lan:
        conf["system_config"]["host"] = "0.0.0.0"

    with conf_path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.dump(conf, f)

    c = conf["character_config"]
    model = c["agent_config"]["llm_configs"]["ollama_llm"]["model"]
    piper = c["tts_config"]["piper_tts"]["model_path"]
    print(f"Xong! Nhân vật mặc định: {c['conf_name']} | model: {model}")
    print(f"  Nghe: {c['asr_config']['asr_model']} | Nói: {c['tts_config']['tts_model']}")
    print(f"  Server: http://{conf['system_config']['host']}:{conf['system_config']['port']}")
    if c["tts_config"]["tts_model"] == "piper_tts" and not (olv / piper).exists():
        print(f"  [Chú ý] Chưa có giọng Piper: {piper} (tải file .onnx và .onnx.json vào đó)")


if __name__ == "__main__":
    main()
