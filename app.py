import os
import re
import shutil
import tempfile
import zipfile
import uuid
import threading
import time
import base64
from pathlib import Path

from flask import Flask, request, jsonify, send_file, Response

import yt_dlp

app = Flask(__name__)

# Ícone do app (estilo TikTok: nota musical cyan/pink) embutido em base64,
# pra não precisar de arquivo separado nem pasta de assets.
ICON_192_B64 = "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"
ICON_512_B64 = "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"

PAGINA_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Baixador de Vídeos</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<link rel="apple-touch-icon" href="/icon-192.png">
<meta name="theme-color" content="#0f0f0f">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Baixador">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, Roboto, Arial, sans-serif;
    background: #0f0f0f;
    color: #f5f5f5;
    display: flex;
    justify-content: center;
    padding: 24px 16px;
    min-height: 100vh;
  }
  .card { width: 100%; max-width: 420px; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  p.sub { color: #a0a0a0; font-size: 14px; margin-top: 0; margin-bottom: 24px; }
  input {
    width: 100%; padding: 14px; border-radius: 10px; border: 1px solid #333;
    background: #1a1a1a; color: #fff; font-size: 16px; margin-bottom: 12px;
  }
  button {
    width: 100%; padding: 14px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #ff2d55, #25f4ee);
    color: #000; font-weight: 700; font-size: 16px; cursor: pointer;
  }
  button:disabled { opacity: 0.5; }
  #status-box { margin-top: 20px; padding: 16px; border-radius: 10px; background: #1a1a1a; display: none; }
  #status-text { font-size: 14px; margin-bottom: 8px; }
  .bar-bg { background: #333; border-radius: 6px; height: 8px; overflow: hidden; }
  .bar-fill { background: linear-gradient(135deg, #ff2d55, #25f4ee); height: 100%; width: 0%; transition: width 0.3s; }
  #download-link {
    display: none; margin-top: 16px; text-align: center; padding: 14px;
    border-radius: 10px; background: #16a34a; color: #fff; text-decoration: none; font-weight: 700;
  }
  .aviso { font-size: 12px; color: #777; margin-top: 24px; line-height: 1.5; }
  label { font-size: 13px; color: #a0a0a0; }
</style>
</head>
<body>
  <div class="card">
    <h1>Baixador de Vídeos</h1>
    <p class="sub">TikTok, Instagram e Facebook — cole o link e baixe sem marca d'água</p>

    <input id="conta" type="text" placeholder="Link do vídeo, reel, post ou perfil" />

    <div id="campo-limite" style="display:flex; gap:10px;">
      <div style="flex:1;">
        <label for="de">Do vídeo nº</label>
        <input id="de" type="number" value="1" min="1" max="500" style="margin-top:6px;" />
      </div>
      <div style="flex:1;">
        <label for="ate">Até o nº</label>
        <input id="ate" type="number" value="10" min="1" max="500" style="margin-top:6px;" />
      </div>
    </div>
    <p style="font-size:11px; color:#666; margin-top:-6px; margin-bottom:12px;">
      Contando a partir do mais recente. Ex: 1 até 10 = os 10 mais novos. 11 até 20 = os próximos 10.
      (Intervalo só funciona pra conta do TikTok — Instagram e Facebook, use link de vídeo único.)
    </p>

    <button id="btn-iniciar" onclick="iniciar()">Baixar</button>

    <div id="status-box">
      <div id="status-text">Preparando...</div>
      <div class="bar-bg"><div id="bar-fill" class="bar-fill"></div></div>
    </div>

    <a id="download-link" href="#">Baixar ZIP com os vídeos</a>

    <p class="aviso">
      TikTok: aceita vídeo único ou conta inteira (com intervalo). Instagram e
      Facebook: funciona melhor com link de post/reel/vídeo específico —
      perfis e conteúdo privado não funcionam nessas duas plataformas sem login.
      Uso pessoal — respeite os direitos dos criadores.
    </p>
  </div>

<script>
let jobId = null;
let poller = null;

async function iniciar() {
  const conta = document.getElementById('conta').value.trim();
  if (!conta) { alert('Digite o @ ou link da conta'); return; }
  const de = document.getElementById('de').value || 1;
  const ate = document.getElementById('ate').value || 10;

  document.getElementById('btn-iniciar').disabled = true;
  document.getElementById('status-box').style.display = 'block';
  document.getElementById('download-link').style.display = 'none';
  document.getElementById('status-text').textContent = 'Iniciando...';
  document.getElementById('bar-fill').style.width = '5%';

  const resp = await fetch('/api/iniciar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conta, de, ate })
  });
  const data = await resp.json();

  if (data.erro) {
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-iniciar').disabled = false;
    return;
  }

  jobId = data.job_id;
  poller = setInterval(checarStatus, 2000);
}

async function checarStatus() {
  const resp = await fetch('/api/status/' + jobId);
  const data = await resp.json();

  if (data.status === 'baixando') {
    document.getElementById('status-text').textContent = `Baixando... (${data.concluidos} vídeos concluídos)`;
    const pct = Math.min(90, 10 + data.concluidos * 5);
    document.getElementById('bar-fill').style.width = pct + '%';
  } else if (data.status === 'na_fila' || data.status === 'iniciando') {
    document.getElementById('status-text').textContent = 'Preparando...';
  } else if (data.status === 'concluido') {
    clearInterval(poller);
    document.getElementById('status-text').textContent = `Pronto! ${data.total_videos} vídeos baixados.`;
    document.getElementById('bar-fill').style.width = '100%';
    const link = document.getElementById('download-link');
    link.href = '/api/baixar/' + jobId;
    link.style.display = 'block';
    document.getElementById('btn-iniciar').disabled = false;
  } else if (data.status === 'erro') {
    clearInterval(poller);
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-iniciar').disabled = false;
  }
}
</script>
</body>
</html>
"""

# ---------------------------------------------------------
# Configurações
# ---------------------------------------------------------
BASE_TMP = Path(tempfile.gettempdir()) / "tiktok_jobs"
BASE_TMP.mkdir(exist_ok=True)

# Guarda o status de cada job em memória (id -> dict)
JOBS = {}

# Limite de segurança padrão (o usuário pode aumentar na tela, até o teto abaixo)
LIMITE_PADRAO = 30
LIMITE_MAXIMO = 200  # teto de segurança pra não travar o servidor gratuito


def normalizar_url(entrada: str) -> str:
    entrada = entrada.strip()
    if entrada.startswith("http"):
        return entrada
    # Sem "http", assume que é @usuario do TikTok (Instagram/Facebook sempre
    # precisam vir como link completo, colado direto do app).
    usuario = entrada.lstrip("@")
    return f"https://www.tiktok.com/@{usuario}"


def eh_video_unico(url: str) -> bool:
    """Detecta se o link é de um único vídeo/post (não perfil/conta inteira)."""
    padroes = [
        r"/video/\d+",           # TikTok
        r"vm\.tiktok\.com",
        r"vt\.tiktok\.com",
        r"instagram\.com/(reel|p|tv)/",   # Instagram: reels, posts, IGTV
        r"facebook\.com/.+/videos/",      # Facebook: vídeo em página/perfil
        r"facebook\.com/watch/?\?v=",     # Facebook: watch?v=
        r"facebook\.com/reel/",           # Facebook reels
        r"fb\.watch/",                    # Facebook link curto
    ]
    return any(re.search(p, url) for p in padroes)


def job_worker(job_id: str, url_alvo: str, inicio: int, fim: int):
    job = JOBS[job_id]
    pasta = BASE_TMP / job_id
    pasta.mkdir(exist_ok=True)

    def hook(d):
        if d["status"] == "downloading":
            job["status"] = "baixando"
            job["arquivo_atual"] = d.get("info_dict", {}).get("title", "")
        elif d["status"] == "finished":
            job["concluidos"] += 1

    ydl_opts = {
        "outtmpl": str(pasta / "%(upload_date)s_%(id)s_%(title).50s.%(ext)s"),
        # "best" pega um único arquivo já pronto (vídeo+áudio juntos) quando
        # disponível, evitando o passo extra de merge via ffmpeg — mais rápido
        # que "bestvideo+bestaudio" na maioria dos vídeos do TikTok.
        "format": "best",
        "ignoreerrors": True,
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        "concurrent_fragment_downloads": 8,
        "socket_timeout": 15,
        "retries": 3,
    }

    # Só aplica intervalo quando for uma conta/perfil (playlist).
    # Vídeo único não usa esses parâmetros.
    if not eh_video_unico(url_alvo):
        ydl_opts["playliststart"] = inicio
        ydl_opts["playlistend"] = fim

    try:
        job["status"] = "iniciando"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_alvo])

        arquivos = list(pasta.glob("*.mp4"))
        if not arquivos:
            job["status"] = "erro"
            job["erro"] = ("Nenhum vídeo encontrado. Pode ser perfil/post privado, "
                            "ou o Instagram/Facebook pediu login pra esse conteúdo.")
            return

        zip_path = BASE_TMP / f"{job_id}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in arquivos:
                zf.write(f, arcname=f.name)

        job["status"] = "concluido"
        job["zip_path"] = str(zip_path)
        job["total_videos"] = len(arquivos)

    except Exception as e:
        job["status"] = "erro"
        job["erro"] = str(e)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


@app.route("/")
def index():
    return PAGINA_HTML


@app.route("/icon-192.png")
def icon_192():
    return Response(base64.b64decode(ICON_192_B64), mimetype="image/png")


@app.route("/icon-512.png")
def icon_512():
    return Response(base64.b64decode(ICON_512_B64), mimetype="image/png")


@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "Baixador de TikTok",
        "short_name": "TikTok DL",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f0f0f",
        "theme_color": "#0f0f0f",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    })


@app.route("/api/iniciar", methods=["POST"])
def iniciar():
    data = request.get_json(force=True)
    conta = data.get("conta", "").strip()

    if not conta:
        return jsonify({"erro": "Informe o link do vídeo, o @ ou o link da conta"}), 400

    try:
        inicio = int(data.get("de", 1))
    except (TypeError, ValueError):
        inicio = 1
    try:
        fim = int(data.get("ate", 10))
    except (TypeError, ValueError):
        fim = 10

    inicio = max(1, min(inicio, LIMITE_MAXIMO))
    fim = max(inicio, min(fim, LIMITE_MAXIMO))

    url_alvo = normalizar_url(conta)
    job_id = uuid.uuid4().hex[:12]

    JOBS[job_id] = {
        "status": "na_fila",
        "concluidos": 0,
        "arquivo_atual": "",
        "criado_em": time.time(),
        "video_unico": eh_video_unico(url_alvo),
    }

    t = threading.Thread(target=job_worker, args=(job_id, url_alvo, inicio, fim), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "video_unico": JOBS[job_id]["video_unico"]})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"erro": "job não encontrado"}), 404
    resposta = {
        "status": job["status"],
        "concluidos": job.get("concluidos", 0),
        "arquivo_atual": job.get("arquivo_atual", ""),
    }
    if job["status"] == "erro":
        resposta["erro"] = job.get("erro")
    if job["status"] == "concluido":
        resposta["total_videos"] = job.get("total_videos")
    return jsonify(resposta)


@app.route("/api/baixar/<job_id>")
def baixar(job_id):
    job = JOBS.get(job_id)
    if not job or job["status"] != "concluido":
        return jsonify({"erro": "arquivo ainda não está pronto"}), 400
    return send_file(job["zip_path"], as_attachment=True, download_name=f"tiktok_{job_id}.zip")


# Limpeza básica de jobs antigos (roda a cada request, suficiente pra uso pessoal)
@app.before_request
def limpar_jobs_antigos():
    agora = time.time()
    expirados = [jid for jid, j in JOBS.items() if agora - j.get("criado_em", agora) > 3600]
    for jid in expirados:
        zip_path = BASE_TMP / f"{jid}.zip"
        if zip_path.exists():
            zip_path.unlink()
        JOBS.pop(jid, None)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
