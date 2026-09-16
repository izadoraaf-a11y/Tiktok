import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

import requests

AUTOPOST_URL = os.environ.get("AUTOPOST_URL", "").rstrip("/")
AUTOPOST_SECRET = os.environ.get("AUTOPOST_SECRET", "")
HEADERS = {"Authorization": f"Bearer {AUTOPOST_SECRET}"}


def ytdlp_json(*args):
    result = subprocess.run(
        ["yt-dlp", "--impersonate", "chrome", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "O TikTok recusou a consulta do perfil")
    return json.loads(result.stdout)


def profile_entries(profile_url):
    data = ytdlp_json("--flat-playlist", "--dump-single-json", profile_url)
    return data.get("entries") or []


def download_video(url, directory, video_id):
    output = str(Path(directory) / f"{video_id}.%(ext)s")
    subprocess.run([
        "yt-dlp", "--impersonate", "chrome", "--no-playlist",
        "--retries", "5", "--fragment-retries", "5",
        "-f", "best[ext=mp4]/best", "-o", output, url,
    ], check=True)
    files = list(Path(directory).glob(f"{video_id}.*"))
    if not files:
        raise RuntimeError(f"Arquivo do vídeo {video_id} não foi criado")
    return files[0]


def upload(source_id, video_id, filename):
    endpoint = (
        f"{AUTOPOST_URL}/api/tiktok/worker?sourceId={quote(source_id)}"
        f"&videoId={quote(video_id)}&fileName={quote(filename.name)}"
    )
    with filename.open("rb") as stream:
        response = requests.post(endpoint, headers={**HEADERS, "Content-Type": "video/mp4"}, data=stream, timeout=900)
    response.raise_for_status()
    return response.json()


def main():
    if not AUTOPOST_URL or not AUTOPOST_SECRET:
        raise RuntimeError("AUTOPOST_URL e AUTOPOST_SECRET precisam estar configurados")
    response = requests.get(f"{AUTOPOST_URL}/api/tiktok/worker", headers=HEADERS, timeout=60)
    response.raise_for_status()
    plans = response.json().get("plans", [])
    print(f"{len(plans)} vínculo(s) precisam de reposição")
    for plan in plans:
        imported = set(plan.get("importedVideoIds", []))
        candidates = []
        for entry in profile_entries(plan["profile_url"]):
            video_id = str(entry.get("id") or "")
            url = entry.get("webpage_url") or entry.get("url")
            if video_id and url and video_id not in imported:
                candidates.append((video_id, url))
            if len(candidates) >= int(plan["needed"]):
                break
        print(f"{plan.get('nickname') or plan['profile_url']}: {len(candidates)} novo(s)")
        with tempfile.TemporaryDirectory() as directory:
            for video_id, url in candidates:
                try:
                    filename = download_video(url, directory, video_id)
                    upload(str(plan["id"]), video_id, filename)
                    filename.unlink(missing_ok=True)
                    print(f"enviado: {video_id}")
                except Exception as error:
                    print(f"falha em {video_id}: {error}")


if __name__ == "__main__":
    main()
