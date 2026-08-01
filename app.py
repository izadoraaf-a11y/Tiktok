import os
import re
import shutil
import tempfile
import zipfile
import uuid
import threading
import time
from pathlib import Path

from flask import Flask, request, jsonify, send_file

import yt_dlp

app = Flask(__name__)

PAGINA_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Baixador de TikTok</title>
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
    <h1>Baixador de TikTok</h1>
    <p class="sub">Cole o @ ou o link da conta e baixe os vídeos sem marca d'água</p>

    <input id="conta" type="text" placeholder="@usuario, link do perfil ou link de 1 vídeo" />

    <div id="campo-limite">
      <label for="limite">Quantos vídeos baixar (mais recentes)</label>
      <input id="limite" type="number" value="30" min="1" max="200" style="margin-top:6px;" />
    </div>

    <button id="btn-iniciar" onclick="iniciar()">Baixar</button>

    <div id="status-box">
      <div id="status-text">Preparando...</div>
      <div class="bar-bg"><div id="bar-fill" class="bar-fill"></div></div>
    </div>

    <a id="download-link" href="#">Baixar ZIP com os vídeos</a>

    <p class="aviso">
      Cole o link de um vídeo específico pra baixar só ele, ou o @/link da conta
      pra baixar em lote. Perfis privados não funcionam. Uso pessoal — respeite
      os direitos dos criadores.
    </p>
  </div>

<script>
let jobId = null;
let poller = null;

async function iniciar() {
  const conta = document.getElementById('conta').value.trim();
  if (!conta) { alert('Digite o @ ou link da conta'); return; }
  const limite = document.getElementById('limite').value || 30;

  document.getElementById('btn-iniciar').disabled = true;
  document.getElementById('status-box').style.display = 'block';
  document.getElementById('download-link').style.display = 'none';
  document.getElementById('status-text').textContent = 'Iniciando...';
  document.getElementById('bar-fill').style.width = '5%';

  const resp = await fetch('/api/iniciar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conta, limite })
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
    usuario = entrada.lstrip("@")
    return f"https://www.tiktok.com/@{usuario}"


def eh_video_unico(url: str) -> bool:
    """Detecta se o link é de um vídeo específico (não o perfil inteiro)."""
    return bool(re.search(r"/video/\d+", url)) or "vm.tiktok.com" in url or "vt.tiktok.com" in url


def job_worker(job_id: str, url_alvo: str, limite: int):
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

    # Só aplica limite de quantidade quando for uma conta/perfil (playlist).
    # Vídeo único não usa esse parâmetro.
    if not eh_video_unico(url_alvo):
        ydl_opts["playlistend"] = limite

    try:
        job["status"] = "iniciando"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_alvo])

        arquivos = list(pasta.glob("*.mp4"))
        if not arquivos:
            job["status"] = "erro"
            job["erro"] = "Nenhum vídeo encontrado ou perfil privado/inexistente."
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


@app.route("/api/iniciar", methods=["POST"])
def iniciar():
    data = request.get_json(force=True)
    conta = data.get("conta", "").strip()
    limite_solicitado = data.get("limite", LIMITE_PADRAO)

    if not conta:
        return jsonify({"erro": "Informe o link do vídeo, o @ ou o link da conta"}), 400

    try:
        limite = int(limite_solicitado)
    except (TypeError, ValueError):
        limite = LIMITE_PADRAO
    limite = max(1, min(limite, LIMITE_MAXIMO))

    url_alvo = normalizar_url(conta)
    job_id = uuid.uuid4().hex[:12]

    JOBS[job_id] = {
        "status": "na_fila",
        "concluidos": 0,
        "arquivo_atual": "",
        "criado_em": time.time(),
        "video_unico": eh_video_unico(url_alvo),
    }

    t = threading.Thread(target=job_worker, args=(job_id, url_alvo, limite), daemon=True)
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
