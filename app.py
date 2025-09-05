
# app.py
import json
import os
from pathlib import Path
from flask import Flask, request, redirect, url_for, render_template, jsonify
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_ROOT = BASE_DIR / "uploads"
CONFIG_PATH = BASE_DIR / "organizer_config.json"

# Load or fallback config
DEFAULT_CONFIG = {
    "mappings": {
        ".gif": "Images",
        ".jpeg": "Images",
        ".jpg": "Images",
        ".png": "Images",
        ".webp": "Images",
        ".mp4": "Video",
        ".mkv": "Video",
        ".zip": "Compressed",
        ".tar": "Compressed",
        ".gz": "Compressed",
        ".mp3": "Music",
        ".wav": "Music",
        ".pdf": "Documents",
        ".docx": "Documents",
        ".doc": "Documents",
        ".xlsx": "Documents",
        ".csv": "Documents",
        ".py": "Programs",
        ".js": "Programs",
        ".exe": "Programs",
        ".ini": "System Files",
        ".icc": "System Files"
    },
    "others_folder_name": "Others"
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
                # ensure keys lowercased
                cfg["mappings"] = {k.lower(): v for k, v in cfg.get("mappings", {}).items()}
                return cfg
        except Exception:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

config = load_config()
mappings = config.get("mappings", {})
OTHERS = config.get("others_folder_name", "Others")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB max (adjust as needed)


def categorize_and_save(file_path: Path) -> Path:
    """
    Move the uploaded file to a categorized folder and return the final path.
    """
    ext = file_path.suffix.lower()
    target_folder_name = mappings.get(ext, OTHERS)
    target_dir = UPLOAD_ROOT / target_folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    # handle collisions by appending counter
    dest = target_dir / file_path.name
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        i = 1
        while True:
            candidate = target_dir / f"{stem} ({i}){suffix}"
            if not candidate.exists():
                dest = candidate
                break
            i += 1

    file_path.replace(dest)  # move file
    return dest


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """
    Accepts file uploads (multipart/form-data). Multiple files allowed with field name 'files'.
    """
    if "files" not in request.files:
        return jsonify({"success": False, "message": "No file part 'files' found"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"success": False, "message": "No files uploaded"}), 400

    saved = []
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    for f in files:
        if f.filename == "":
            continue
        filename = secure_filename(f.filename)
        if filename == "":
            # skip odd filenames
            continue

        # save to a temp location first inside uploads root
        temp_path = UPLOAD_ROOT / filename
        # if collision, add counter to temp name (avoids overwrite during concurrent uploads)
        if temp_path.exists():
            stem = temp_path.stem
            suffix = temp_path.suffix
            i = 1
            while True:
                candidate = UPLOAD_ROOT / f"{stem} ({i}){suffix}"
                if not candidate.exists():
                    temp_path = candidate
                    break
                i += 1

        f.save(str(temp_path))
        final_path = categorize_and_save(temp_path)
        saved.append({
            "original": f.filename,
            "stored": str(final_path.relative_to(BASE_DIR)),
            "category": final_path.parent.name
        })

    return jsonify({"success": True, "saved": saved})


if __name__ == "__main__":
    # use development server; for production use gunicorn/uwsgi + reverse proxy
    app.run(host="0.0.0.0", port=5000, debug=True)
