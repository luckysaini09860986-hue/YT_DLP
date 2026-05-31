import os
import sys
import json
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Use an absolute path for the downloads directory relative to this script
BASE_DIR = Path(__file__).parent.absolute()
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# In-memory job tracker
jobs = {}


def run_job(job_id, fn, *args, **kwargs):
    try:
        jobs[job_id]["status"] = "running"
        result = fn(*args, **kwargs)
        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = result
    except Exception as e:
        import traceback
        print(f"Job {job_id} failed: {str(e)}")
        traceback.print_exc()
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


# ── Helpers ──────────────────────────────────────────────────────────────────

def ytdlp(*args):
    # Try the yt-dlp CLI first; if it’s not available, fall back to the Python module.
    # Added --restrict-filenames to avoid problematic characters in Windows
    common_args = ["--no-warnings", "--quiet", "--restrict-filenames"]
    cmd = ["yt-dlp"] + common_args + list(args)
    
    try:
        # On Windows, shell=True can help find the executable in some environments
        r = subprocess.run(cmd, capture_output=True, text=True, shell=os.name == "nt")
        if r.returncode != 0 and "not found" in (r.stderr or "").lower():
            raise FileNotFoundError
    except FileNotFoundError:
        # CLI not found – use the Python module via `sys.executable -m yt_dlp`
        cmd = [sys.executable, "-m", "yt_dlp"] + common_args + list(args)
        r = subprocess.run(cmd, capture_output=True, text=True, shell=os.name == "nt")
    
    if r.returncode != 0:
        error_msg = r.stderr or r.stdout
        print(f"yt-dlp error: {error_msg}")
        raise RuntimeError(error_msg.strip())
    return r.stdout.strip()


def ytdlp_json(url):
    raw = ytdlp("-j", "--no-playlist", url)
    return json.loads(raw)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"ok": True, "message": "YTForge backend is running 🚀"})


@app.route("/api/info", methods=["POST"])
def video_info():
    url = request.json.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL required"}), 400
    try:
        info = ytdlp_json(url)
        return jsonify({
            "title": info.get("title"),
            "channel": info.get("channel") or info.get("uploader"),
            "duration": info.get("duration"),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "upload_date": info.get("upload_date"),
            "description": (info.get("description") or "")[:500],
            "thumbnail": info.get("thumbnail"),
            "webpage_url": info.get("webpage_url"),
            "formats": [
                {
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "resolution": f.get("resolution") or f.get("format_note"),
                    "filesize": f.get("filesize"),
                    "vcodec": f.get("vcodec"),
                    "acodec": f.get("acodec"),
                }
                for f in info.get("formats", [])
                if f.get("vcodec") != "none" or f.get("acodec") != "none"
            ][-10:],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download", methods=["POST"])
def download_video():
    data = request.json
    url = data.get("url", "").strip()
    fmt = data.get("format", "bestvideo+bestaudio/best")
    if not url:
        return jsonify({"error": "URL required"}), 400

    job_id = str(uuid.uuid4())
    out_tmpl = str(DOWNLOAD_DIR / f"{job_id}_%(title)s.%(ext)s")

    def do_download():
        ytdlp("-f", fmt, "--merge-output-format", "mp4", "-o", out_tmpl, url)
        files = list(DOWNLOAD_DIR.glob(f"{job_id}_*"))
        if not files:
            raise RuntimeError("Download produced no file")
        return {"filename": files[0].name}

    jobs[job_id] = {"status": "queued"}
    t = threading.Thread(target=run_job, args=(job_id, do_download))
    t.daemon = True
    t.start()
    return jsonify({"job_id": job_id})


@app.route("/api/audio", methods=["POST"])
def extract_audio():
    data = request.json
    url = data.get("url", "").strip()
    audio_fmt = data.get("audio_format", "mp3")
    if not url:
        return jsonify({"error": "URL required"}), 400

    job_id = str(uuid.uuid4())
    out_tmpl = str(DOWNLOAD_DIR / f"{job_id}_%(title)s.%(ext)s")

    def do_audio():
        ytdlp(
            "-x", "--audio-format", audio_fmt,
            "--audio-quality", "0",
            "-o", out_tmpl, url
        )
        files = list(DOWNLOAD_DIR.glob(f"{job_id}_*"))
        if not files:
            raise RuntimeError("No audio file produced")
        return {"filename": files[0].name}

    jobs[job_id] = {"status": "queued"}
    t = threading.Thread(target=run_job, args=(job_id, do_audio))
    t.daemon = True
    t.start()
    return jsonify({"job_id": job_id})


@app.route("/api/thumbnail", methods=["POST"])
def get_thumbnail():
    url = request.json.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL required"}), 400
    try:
        info = ytdlp_json(url)
        thumbnails = info.get("thumbnails", [])
        # Return all thumbnails sorted by resolution
        thumb_list = sorted(
            [t for t in thumbnails if t.get("url")],
            key=lambda t: (t.get("width") or 0) * (t.get("height") or 0),
            reverse=True
        )
        return jsonify({
            "thumbnails": thumb_list[:5],
            "best": thumb_list[0]["url"] if thumb_list else info.get("thumbnail")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/job/<job_id>")
def get_job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/download_file/<filename>")
def download_file(filename):
    # Security: ensure the filename is just a name, not a path
    safe_name = os.path.basename(filename)
    file_path = DOWNLOAD_DIR / safe_name
    if not file_path.exists():
        return "File not found", 404
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    print("YTForge backend starting on http://localhost:5000")
    app.run(port=5000, debug=True)
