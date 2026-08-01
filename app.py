import os
import re
import shutil
import tempfile
import zipfile
import uuid
import threading
import time
import base64
import json
import subprocess
import io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename

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
  .nav { display: flex; gap: 8px; margin-bottom: 20px; }
  .nav a {
    flex: 1; text-align: center; padding: 10px; border-radius: 8px;
    text-decoration: none; font-size: 13px; font-weight: 600; color: #888;
    background: #1a1a1a; border: 1px solid #262626;
  }
  .nav a.ativo { color: #000; background: linear-gradient(135deg, #ff2d55, #25f4ee); border: none; }
</style>
</head>
<body>
  <div class="card">
    <div class="nav">
      <a href="/" class="ativo">Baixador</a>
      <a href="/editor">Editor</a>
      <a href="/gerador">Gerador</a>
      <a href="/config">Config</a>
    </div>
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

PAGINA_EDITOR_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Auto-editor</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<link rel="apple-touch-icon" href="/icon-192.png">
<meta name="theme-color" content="#0f0f0f">
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
  p.sub { color: #a0a0a0; font-size: 14px; margin-top: 0; margin-bottom: 20px; }
  .nav { display: flex; gap: 8px; margin-bottom: 20px; }
  .nav a {
    flex: 1; text-align: center; padding: 10px; border-radius: 8px;
    text-decoration: none; font-size: 13px; font-weight: 600; color: #888;
    background: #1a1a1a; border: 1px solid #262626;
  }
  .nav a.ativo { color: #000; background: linear-gradient(135deg, #ff2d55, #25f4ee); border: none; }
  label { font-size: 13px; color: #ccc; display: block; margin-bottom: 6px; font-weight: 600; }
  .campo { margin-bottom: 18px; }
  .ajuda { font-size: 11px; color: #666; margin-top: 4px; line-height: 1.4; }
  input[type="file"] {
    width: 100%; padding: 12px; border-radius: 10px; border: 1px dashed #333;
    background: #1a1a1a; color: #ccc; font-size: 13px;
  }
  input[type="number"], input[type="range"] {
    width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #333;
    background: #1a1a1a; color: #fff; font-size: 16px;
  }
  input[type="range"] { padding: 0; height: 40px; }
  .valor-brilho { text-align: center; font-size: 13px; color: #25f4ee; margin-top: 4px; }
  button {
    width: 100%; padding: 14px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #ff2d55, #25f4ee);
    color: #000; font-weight: 700; font-size: 16px; cursor: pointer;
  }
  button:disabled { opacity: 0.4; }
  #status-box { margin-top: 20px; padding: 16px; border-radius: 10px; background: #1a1a1a; display: none; }
  #status-text { font-size: 14px; margin-bottom: 8px; }
  .bar-bg { background: #333; border-radius: 6px; height: 8px; overflow: hidden; }
  .bar-fill { background: linear-gradient(135deg, #ff2d55, #25f4ee); height: 100%; width: 0%; transition: width 0.3s; }
  #download-link {
    display: none; margin-top: 16px; text-align: center; padding: 14px;
    border-radius: 10px; background: #16a34a; color: #fff; text-decoration: none; font-weight: 700;
  }
  .aviso { font-size: 12px; color: #777; margin-top: 24px; line-height: 1.5; }
</style>
</head>
<body>
  <div class="card">
    <div class="nav">
      <a href="/">Baixador</a>
      <a href="/editor" class="ativo">Editor</a>
      <a href="/gerador">Gerador</a>
      <a href="/config">Config</a>
    </div>
    <h1>Auto-editor</h1>
    <p class="sub">Filtro de brilho + CTA em massa no final dos seus vídeos</p>

    <div class="campo">
      <label>Seus vídeos (pode escolher vários)</label>
      <input id="videos" type="file" accept="video/*" multiple />
      <p class="ajuda">Máximo de 15 vídeos por vez. Vídeos grandes (4K) são reduzidos automaticamente pra processar mais rápido.</p>
    </div>

    <div class="campo">
      <label>Imagem do CTA</label>
      <input id="cta" type="file" accept="image/*" />
      <p class="ajuda">Essa imagem vai aparecer no final de cada vídeo.</p>
    </div>

    <div class="campo">
      <label>Filtro de brilho</label>
      <input id="brilho" type="range" min="-50" max="50" value="0" oninput="atualizarBrilho()" />
      <p class="valor-brilho" id="valor-brilho">Neutro (0)</p>
    </div>

    <div class="campo">
      <label>Duração do CTA (segundos)</label>
      <input id="duracao" type="number" value="5" min="1" max="15" />
    </div>

    <div class="campo" style="display:flex; align-items:center; gap:8px;">
      <input id="usar-legenda" type="checkbox" style="width:auto;" onchange="alternarLegenda()" />
      <label style="margin-bottom:0;" for="usar-legenda">Adicionar legenda no vídeo</label>
    </div>

    <div id="campos-legenda" style="display:none;">
      <div class="campo" style="display:flex; gap:16px;">
        <label style="display:flex; align-items:center; gap:6px; margin-bottom:0; font-weight:400;">
          <input type="radio" name="modo-legenda" value="automatica" checked onchange="alternarModoLegenda()" style="width:auto;" /> Automática (transcreve o áudio)
        </label>
      </div>
      <div class="campo" style="display:flex; gap:16px; margin-top:-10px;">
        <label style="display:flex; align-items:center; gap:6px; margin-bottom:0; font-weight:400;">
          <input type="radio" name="modo-legenda" value="manual" onchange="alternarModoLegenda()" style="width:auto;" /> Digitar o texto
        </label>
      </div>

      <div id="status-chave-editor" class="campo" style="background:#1a1a1a; border:1px solid #262626; border-radius:10px; padding:10px 12px; font-size:12px;">
        Verificando chave da API...
      </div>

      <div id="campo-texto-manual" class="campo" style="display:none;">
        <label>Texto da legenda</label>
        <input id="texto-legenda" type="text" placeholder="Ex: Não perca essa dica!" style="padding:12px; border-radius:10px; border:1px solid #333; background:#1a1a1a; color:#fff; font-size:15px;" />
      </div>

      <div class="campo">
        <label>Modelo da legenda</label>
        <select id="modelo-legenda" onchange="alternarCorFundo()" style="width:100%; padding:12px; border-radius:10px; border:1px solid #333; background:#1a1a1a; color:#fff; font-size:15px;">
          <option value="classico">Clássico — branco, embaixo</option>
          <option value="impacto">Impacto — amarelo, no topo</option>
          <option value="neon">Neon — ciano, no centro</option>
          <option value="minimalista">Minimalista — pequeno, canto</option>
          <option value="citacao">Citação — faixa colorida, centro</option>
        </select>
      </div>

      <div id="campo-cor-fundo" style="display:none;">
        <div class="campo">
          <label>Cor da faixa</label>
          <select id="cor-fundo-citacao" style="width:100%; padding:12px; border-radius:10px; border:1px solid #333; background:#1a1a1a; color:#fff; font-size:15px;">
            <option value="branco">Branco (texto preto)</option>
            <option value="preto">Preto (texto branco)</option>
            <option value="vermelho">Vermelho (texto branco)</option>
          </select>
        </div>
      </div>
    </div>

    <button id="btn-processar" onclick="processar()">Processar vídeos</button>

    <div id="status-box">
      <div id="status-text">Preparando...</div>
      <div class="bar-bg"><div id="bar-fill" class="bar-fill"></div></div>
    </div>

    <a id="download-link" href="#">Baixar ZIP com os vídeos prontos</a>

    <p class="aviso">
      Use só com vídeos que são seus (ou que você tem autorização de editar).
      Processamento é pesado — no plano gratuito pode demorar alguns minutos
      por vídeo. Vídeos muito grandes podem falhar por limite de memória.
    </p>
  </div>

<script>
let jobId = null;
let poller = null;

function atualizarBrilho() {
  const v = document.getElementById('brilho').value;
  const label = v == 0 ? 'Neutro (0)' : (v > 0 ? `Mais claro (+${v})` : `Mais escuro (${v})`);
  document.getElementById('valor-brilho').textContent = label;
}

function alternarLegenda() {
  const marcado = document.getElementById('usar-legenda').checked;
  document.getElementById('campos-legenda').style.display = marcado ? 'block' : 'none';
  if (marcado) { atualizarStatusChaveEditor(); alternarModoLegenda(); }
}

function alternarModoLegenda() {
  const modo = document.querySelector('input[name="modo-legenda"]:checked').value;
  document.getElementById('campo-texto-manual').style.display = modo === 'manual' ? 'block' : 'none';
  document.getElementById('status-chave-editor').style.display = modo === 'automatica' ? 'block' : 'none';
}

function atualizarStatusChaveEditor() {
  const chave = localStorage.getItem('api_key_openai') || '';
  const div = document.getElementById('status-chave-editor');
  if (chave) {
    div.innerHTML = '✅ Chave OpenAI configurada — a legenda vai ser transcrita automaticamente';
  } else {
    div.innerHTML = '⚠️ Precisa configurar a chave OpenAI — <a href="/config" style="color:#ff2d55; font-weight:700;">configurar agora</a>';
  }
}

function alternarCorFundo() {
  const modelo = document.getElementById('modelo-legenda').value;
  document.getElementById('campo-cor-fundo').style.display = modelo === 'citacao' ? 'block' : 'none';
}

async function processar() {
  const videos = document.getElementById('videos').files;
  const cta = document.getElementById('cta').files[0];
  const brilho = document.getElementById('brilho').value;
  const duracao = document.getElementById('duracao').value || 5;
  const usarLegenda = document.getElementById('usar-legenda').checked;
  const modoLegenda = usarLegenda ? document.querySelector('input[name="modo-legenda"]:checked').value : 'manual';
  const textoLegenda = document.getElementById('texto-legenda').value.trim();
  const modeloLegenda = document.getElementById('modelo-legenda').value;
  const corFundoCitacao = document.getElementById('cor-fundo-citacao').value;
  const apiKey = localStorage.getItem('api_key_openai') || '';

  if (videos.length === 0) { alert('Escolhe pelo menos 1 vídeo'); return; }
  if (!cta) { alert('Escolhe a imagem do CTA'); return; }
  if (videos.length > 15) { alert('Máximo de 15 vídeos por vez'); return; }
  if (usarLegenda && modoLegenda === 'manual' && !textoLegenda) { alert('Digite o texto da legenda ou escolhe "Automática"'); return; }
  if (usarLegenda && modoLegenda === 'automatica' && !apiKey) { alert('Configura sua chave OpenAI na aba Config primeiro'); return; }

  const formData = new FormData();
  for (const v of videos) formData.append('videos', v);
  formData.append('cta', cta);
  formData.append('brilho', brilho);
  formData.append('duracao', duracao);
  formData.append('usar_legenda', usarLegenda ? '1' : '0');
  formData.append('modo_legenda', modoLegenda);
  formData.append('texto_legenda', textoLegenda);
  formData.append('modelo_legenda', modeloLegenda);
  formData.append('cor_fundo_citacao', corFundoCitacao);
  formData.append('api_key', apiKey);

  document.getElementById('btn-processar').disabled = true;
  document.getElementById('status-box').style.display = 'block';
  document.getElementById('download-link').style.display = 'none';
  document.getElementById('status-text').textContent = 'Enviando arquivos...';
  document.getElementById('bar-fill').style.width = '5%';

  let resp;
  try {
    resp = await fetch('/api/editor/iniciar', { method: 'POST', body: formData });
  } catch (e) {
    document.getElementById('status-text').textContent = 'Erro ao enviar. Tenta de novo.';
    document.getElementById('btn-processar').disabled = false;
    return;
  }
  const data = await resp.json();

  if (data.erro) {
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-processar').disabled = false;
    return;
  }

  jobId = data.job_id;
  localStorage.setItem('editor_job_ativo', jobId);
  poller = setInterval(checarStatus, 3000);
}

async function checarStatus() {
  const resp = await fetch('/api/editor/status/' + jobId);
  const data = await resp.json();

  if (data.status === 'processando') {
    const extra = data.arquivo_atual && data.arquivo_atual.startsWith('transcrevendo') ? ' — transcrevendo áudio...' : '';
    document.getElementById('status-text').textContent = `Processando... (${data.concluidos}/${data.total} prontos)${extra}`;
    const pct = Math.min(90, 10 + (data.concluidos / Math.max(data.total,1)) * 80);
    document.getElementById('bar-fill').style.width = pct + '%';
  } else if (data.status === 'na_fila') {
    document.getElementById('status-text').textContent = 'Preparando...';
  } else if (data.status === 'concluido') {
    clearInterval(poller);
    localStorage.removeItem('editor_job_ativo');
    document.getElementById('status-text').textContent = `Pronto! ${data.total} vídeo(s) processado(s).`;
    document.getElementById('bar-fill').style.width = '100%';
    const link = document.getElementById('download-link');
    link.href = '/api/editor/baixar/' + jobId;
    link.style.display = 'block';
    document.getElementById('btn-processar').disabled = false;
  } else if (data.status === 'erro') {
    clearInterval(poller);
    localStorage.removeItem('editor_job_ativo');
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-processar').disabled = false;
  }
}

// Retoma automaticamente um processamento que ficou rodando em segundo
// plano no servidor (ex: você trocou de app e a tela "esqueceu" o job).
(function retomarJobAtivo() {
  const jobSalvo = localStorage.getItem('editor_job_ativo');
  if (!jobSalvo) return;
  jobId = jobSalvo;
  document.getElementById('status-box').style.display = 'block';
  document.getElementById('status-text').textContent = 'Retomando processamento anterior...';
  document.getElementById('btn-processar').disabled = true;
  poller = setInterval(checarStatus, 3000);
  checarStatus();
})();
</script>
</body>
</html>
"""


PAGINA_GERADOR_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gerador IA</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<link rel="apple-touch-icon" href="/icon-192.png">
<meta name="theme-color" content="#0f0f0f">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, Roboto, Arial, sans-serif;
    background: #0f0f0f;
    color: #f5f5f5;
    display: flex;
    justify-content: center;
    padding: 24px 16px 60px;
    min-height: 100vh;
  }
  .card { width: 100%; max-width: 420px; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  h2 { font-size: 15px; margin: 28px 0 10px; color: #ddd; }
  p.sub { color: #a0a0a0; font-size: 14px; margin-top: 0; margin-bottom: 20px; }
  .nav { display: flex; gap: 8px; margin-bottom: 20px; }
  .nav a {
    flex: 1; text-align: center; padding: 10px; border-radius: 8px;
    text-decoration: none; font-size: 13px; font-weight: 600; color: #888;
    background: #1a1a1a; border: 1px solid #262626;
  }
  .nav a.ativo { color: #000; background: linear-gradient(135deg, #ff2d55, #25f4ee); border: none; }
  label { font-size: 13px; color: #ccc; display: block; margin-bottom: 6px; font-weight: 600; }
  .campo { margin-bottom: 16px; }
  .ajuda { font-size: 11px; color: #666; margin-top: 4px; line-height: 1.4; }
  input[type="text"], input[type="password"], input[type="number"], textarea, select {
    width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #333;
    background: #1a1a1a; color: #fff; font-size: 15px; font-family: inherit;
  }
  textarea { resize: vertical; min-height: 70px; }
  button {
    width: 100%; padding: 14px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #ff2d55, #25f4ee);
    color: #000; font-weight: 700; font-size: 16px; cursor: pointer;
  }
  button.secundario {
    background: #1a1a1a; color: #ccc; border: 1px solid #333; font-weight: 600; font-size: 14px; padding: 10px;
  }
  button:disabled { opacity: 0.4; }
  .exemplo-item {
    display: flex; gap: 8px; align-items: flex-start; background: #1a1a1a;
    border: 1px solid #262626; border-radius: 8px; padding: 10px; margin-bottom: 8px;
  }
  .exemplo-texto { flex: 1; font-size: 13px; color: #ccc; white-space: pre-wrap; }
  .exemplo-del { color: #ff2d55; background: none; border: none; font-size: 13px; width: auto; padding: 4px 8px; }
  #status-box { margin-top: 20px; padding: 16px; border-radius: 10px; background: #1a1a1a; display: none; }
  #status-text { font-size: 14px; margin-bottom: 8px; }
  .bar-bg { background: #333; border-radius: 6px; height: 8px; overflow: hidden; }
  .bar-fill { background: linear-gradient(135deg, #ff2d55, #25f4ee); height: 100%; width: 0%; transition: width 0.3s; }
  #download-link {
    display: none; margin-top: 16px; text-align: center; padding: 14px;
    border-radius: 10px; background: #16a34a; color: #fff; text-decoration: none; font-weight: 700;
  }
  .aviso { font-size: 12px; color: #777; margin-top: 24px; line-height: 1.5; }
  .linha { display: flex; gap: 10px; }
  .linha > div { flex: 1; }
</style>
</head>
<body>
  <div class="card">
    <div class="nav">
      <a href="/">Baixador</a>
      <a href="/editor">Editor</a>
      <a href="/gerador" class="ativo">Gerador</a>
      <a href="/config">Config</a>
    </div>
    <h1>Gerador IA</h1>
    <p class="sub">Copies + imagens geradas por IA, no seu funil, alimentado pelos seus exemplos</p>

    <h2>⚙️ Configuração</h2>

    <div id="status-chave" class="campo" style="background:#1a1a1a; border:1px solid #262626; border-radius:10px; padding:12px 14px; font-size:13px;">
      Verificando chave da API...
    </div>

    <div class="campo">
      <label>Funil / nicho atual</label>
      <input id="funil" type="text" placeholder="Ex: Chama gêmea, reconciliação amorosa" onchange="salvarConfig()" />
    </div>

    <h2>📌 Exemplos que estão convertendo</h2>
    <p class="ajuda" style="margin-top:-6px; margin-bottom:12px;">
      Cole aqui o texto de copies que estão funcionando bem (as suas ou de referência).
      A IA vai se inspirar nesses exemplos — sem copiar — pra criar frases novas no mesmo estilo.
    </p>

    <div class="campo">
      <textarea id="novo-exemplo" placeholder="Ex: A pessoa que você está pensando também está pensando em você..."></textarea>
      <button class="secundario" style="margin-top:8px;" onclick="adicionarExemplo()">+ Adicionar exemplo</button>
    </div>

    <div id="lista-exemplos"></div>

    <h2>🎨 Geração</h2>

    <div class="campo">
      <label>Estilo visual</label>
      <select id="estilo">
        <option value="foto_livro">Foto realista — mão segurando livro/celular</option>
        <option value="ilustrado_cosmico">Ilustrado — cósmico/místico</option>
      </select>
    </div>

    <div class="linha campo">
      <div>
        <label>Quantas imagens</label>
        <input id="quantidade" type="number" value="8" min="4" max="40" step="4" />
      </div>
    </div>
    <p class="ajuda" style="margin-top:-10px;">Sempre em múltiplos de 4 (arredonda pra cima).</p>

    <div class="campo" style="display:flex; align-items:center; gap:8px;">
      <input id="gerar-reels" type="checkbox" style="width:auto;" />
      <label style="margin-bottom:0;" for="gerar-reels">Também criar Reels (vídeo 6s + som ambiente)</label>
    </div>

    <button id="btn-gerar" onclick="gerar()">Gerar</button>

    <div id="status-box">
      <div id="status-text">Preparando...</div>
      <div class="bar-bg"><div id="bar-fill" class="bar-fill"></div></div>
    </div>

    <a id="download-link" href="#">Baixar ZIP com o resultado</a>

    <p class="aviso">
      Isso consome créditos da sua conta OpenAI (texto + imagem). Cada grupo de 4 imagens
      = 1 chamada de imagem. Processamento pode levar alguns minutos no plano gratuito.
      Conteúdo gerado é original — inspirado no estilo dos seus exemplos, não uma cópia deles.
    </p>
  </div>

<script>
let jobId = null;
let poller = null;
let exemplos = [];

function carregarConfig() {
  atualizarStatusChave();
  document.getElementById('funil').value = localStorage.getItem('gerador_funil') || '';
  exemplos = JSON.parse(localStorage.getItem('gerador_exemplos') || '[]');
  renderizarExemplos();
}

function atualizarStatusChave() {
  const chave = localStorage.getItem('api_key_openai') || '';
  const div = document.getElementById('status-chave');
  if (chave) {
    div.innerHTML = '✅ Chave OpenAI configurada — <a href="/config" style="color:#25f4ee;">trocar</a>';
  } else {
    div.innerHTML = '⚠️ Nenhuma chave configurada — <a href="/config" style="color:#ff2d55; font-weight:700;">configurar agora</a>';
  }
}

function salvarConfig() {
  localStorage.setItem('gerador_funil', document.getElementById('funil').value);
}

function adicionarExemplo() {
  const texto = document.getElementById('novo-exemplo').value.trim();
  if (!texto) return;
  exemplos.push(texto);
  localStorage.setItem('gerador_exemplos', JSON.stringify(exemplos));
  document.getElementById('novo-exemplo').value = '';
  renderizarExemplos();
}

function removerExemplo(i) {
  exemplos.splice(i, 1);
  localStorage.setItem('gerador_exemplos', JSON.stringify(exemplos));
  renderizarExemplos();
}

function renderizarExemplos() {
  const div = document.getElementById('lista-exemplos');
  div.innerHTML = '';
  exemplos.forEach((ex, i) => {
    const item = document.createElement('div');
    item.className = 'exemplo-item';
    const p = document.createElement('div');
    p.className = 'exemplo-texto';
    p.textContent = ex;
    const btn = document.createElement('button');
    btn.className = 'exemplo-del';
    btn.textContent = '✕';
    btn.onclick = () => removerExemplo(i);
    item.appendChild(p);
    item.appendChild(btn);
    div.appendChild(item);
  });
}

async function gerar() {
  const apiKey = localStorage.getItem('api_key_openai') || '';
  const funil = document.getElementById('funil').value.trim();
  const estilo = document.getElementById('estilo').value;
  const quantidade = document.getElementById('quantidade').value || 8;
  const gerarReels = document.getElementById('gerar-reels').checked;

  if (!apiKey) { alert('Configura sua chave da API OpenAI na aba Config primeiro'); return; }
  if (!funil) { alert('Descreve o funil/nicho atual'); return; }

  salvarConfig();

  document.getElementById('btn-gerar').disabled = true;
  document.getElementById('status-box').style.display = 'block';
  document.getElementById('download-link').style.display = 'none';
  document.getElementById('status-text').textContent = 'Gerando as frases...';
  document.getElementById('bar-fill').style.width = '5%';

  let resp;
  try {
    resp = await fetch('/api/gerador/iniciar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey, funil, exemplos, estilo, quantidade, gerar_reels: gerarReels })
    });
  } catch (e) {
    document.getElementById('status-text').textContent = 'Erro de conexão. Tenta de novo.';
    document.getElementById('btn-gerar').disabled = false;
    return;
  }
  const data = await resp.json();

  if (data.erro) {
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-gerar').disabled = false;
    return;
  }

  jobId = data.job_id;
  poller = setInterval(checarStatus, 3000);
}

async function checarStatus() {
  const resp = await fetch('/api/gerador/status/' + jobId);
  const data = await resp.json();

  if (data.status === 'gerando_copies') {
    document.getElementById('status-text').textContent = 'Criando as frases com IA...';
    document.getElementById('bar-fill').style.width = '15%';
  } else if (data.status === 'gerando_imagens') {
    document.getElementById('status-text').textContent = `Gerando imagens... (${data.concluidos}/${data.total})`;
    const pct = Math.min(85, 20 + (data.concluidos / Math.max(data.total,1)) * 50);
    document.getElementById('bar-fill').style.width = pct + '%';
  } else if (data.status === 'gerando_reels') {
    document.getElementById('status-text').textContent = `Animando reels... (${data.concluidos_reels || 0}/${data.total})`;
    document.getElementById('bar-fill').style.width = '90%';
  } else if (data.status === 'concluido') {
    clearInterval(poller);
    document.getElementById('status-text').textContent = `Pronto! ${data.total} imagem(ns) geradas.`;
    document.getElementById('bar-fill').style.width = '100%';
    const link = document.getElementById('download-link');
    link.href = '/api/gerador/baixar/' + jobId;
    link.style.display = 'block';
    document.getElementById('btn-gerar').disabled = false;
  } else if (data.status === 'erro') {
    clearInterval(poller);
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-gerar').disabled = false;
  }
}

carregarConfig();
</script>
</body>
</html>
"""

PAGINA_CONFIG_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Configurações</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<link rel="apple-touch-icon" href="/icon-192.png">
<meta name="theme-color" content="#0f0f0f">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, Roboto, Arial, sans-serif;
    background: #0f0f0f;
    color: #f5f5f5;
    display: flex;
    justify-content: center;
    padding: 24px 16px 60px;
    min-height: 100vh;
  }
  .card { width: 100%; max-width: 420px; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  p.sub { color: #a0a0a0; font-size: 14px; margin-top: 0; margin-bottom: 24px; }
  .nav { display: flex; gap: 8px; margin-bottom: 20px; }
  .nav a {
    flex: 1; text-align: center; padding: 10px; border-radius: 8px;
    text-decoration: none; font-size: 13px; font-weight: 600; color: #888;
    background: #1a1a1a; border: 1px solid #262626;
  }
  .nav a.ativo { color: #000; background: linear-gradient(135deg, #ff2d55, #25f4ee); border: none; }
  .servico {
    background: #1a1a1a; border: 1px solid #262626; border-radius: 12px;
    padding: 16px; margin-bottom: 16px;
  }
  .servico-titulo { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-weight: 700; font-size: 15px; }
  .servico-desc { font-size: 12px; color: #888; margin-bottom: 12px; line-height: 1.4; }
  label { font-size: 13px; color: #ccc; display: block; margin-bottom: 6px; font-weight: 600; }
  input[type="password"], input[type="text"] {
    width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #333;
    background: #0f0f0f; color: #fff; font-size: 15px; font-family: inherit;
  }
  .status-badge {
    display: inline-block; font-size: 11px; font-weight: 700; padding: 3px 10px;
    border-radius: 20px; margin-left: 6px;
  }
  .badge-ok { background: #16a34a33; color: #4ade80; }
  .badge-vazio { background: #ff2d5533; color: #ff6b8a; }
  .ajuda { font-size: 11px; color: #666; margin-top: 6px; line-height: 1.4; }
  .ajuda a { color: #25f4ee; }
  button.salvar {
    width: 100%; padding: 12px; border-radius: 10px; border: none; margin-top: 10px;
    background: linear-gradient(135deg, #ff2d55, #25f4ee); color: #000; font-weight: 700; font-size: 14px; cursor: pointer;
  }
  .toast {
    display: none; position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    background: #16a34a; color: white; padding: 12px 20px; border-radius: 10px; font-size: 14px; font-weight: 600;
  }
</style>
</head>
<body>
  <div class="card">
    <div class="nav">
      <a href="/">Baixador</a>
      <a href="/editor">Editor</a>
      <a href="/gerador">Gerador</a>
      <a href="/config" class="ativo">Config</a>
    </div>
    <h1>Configurações</h1>
    <p class="sub">Suas chaves de API, usadas por todas as ferramentas do app</p>

    <div class="servico">
      <div class="servico-titulo">
        🤖 OpenAI <span id="badge-openai" class="status-badge badge-vazio">não configurada</span>
      </div>
      <div class="servico-desc">
        Usada no Gerador IA (copies + imagens) e no Auto-editor (legenda automática por transcrição).
      </div>
      <label>Chave da API</label>
      <input id="chave-openai" type="password" placeholder="sk-..." />
      <p class="ajuda">Pega a sua em <a href="https://platform.openai.com/api-keys" target="_blank">platform.openai.com/api-keys</a></p>
      <button class="salvar" onclick="salvar('openai')">Salvar</button>
    </div>

    <div class="servico">
      <div class="servico-titulo">
        🎵 ElevenLabs <span id="badge-elevenlabs" class="status-badge badge-vazio">não configurada</span>
      </div>
      <div class="servico-desc">
        Reservada pra quando ativarmos música de meditação gerada por IA de verdade (hoje o app usa som ambiente sintetizado, sem precisar dessa chave).
      </div>
      <label>Chave da API</label>
      <input id="chave-elevenlabs" type="password" placeholder="Sua chave da ElevenLabs" />
      <p class="ajuda">Pega a sua em <a href="https://elevenlabs.io" target="_blank">elevenlabs.io</a></p>
      <button class="salvar" onclick="salvar('elevenlabs')">Salvar</button>
    </div>

    <p class="ajuda" style="margin-top:20px;">
      As chaves ficam salvas só no seu navegador (localStorage), nunca no servidor.
      Se trocar de celular ou limpar os dados do navegador, precisa cadastrar de novo.
    </p>
  </div>

  <div id="toast" class="toast">Chave salva ✓</div>

<script>
function carregarStatus() {
  ['openai', 'elevenlabs'].forEach(servico => {
    const chave = localStorage.getItem('api_key_' + servico) || '';
    document.getElementById('chave-' + servico).value = chave;
    const badge = document.getElementById('badge-' + servico);
    if (chave) {
      badge.textContent = 'configurada';
      badge.className = 'status-badge badge-ok';
    } else {
      badge.textContent = 'não configurada';
      badge.className = 'status-badge badge-vazio';
    }
  });
}

function salvar(servico) {
  const valor = document.getElementById('chave-' + servico).value.trim();
  localStorage.setItem('api_key_' + servico, valor);
  carregarStatus();
  const toast = document.getElementById('toast');
  toast.style.display = 'block';
  setTimeout(() => { toast.style.display = 'none'; }, 2000);
}

carregarStatus();
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


# ---------------------------------------------------------
# Auto-editor: filtro de brilho + CTA no final, em lote
# ---------------------------------------------------------
EDITOR_BASE_TMP = Path(tempfile.gettempdir()) / "editor_jobs"
EDITOR_BASE_TMP.mkdir(exist_ok=True)
EDITOR_JOBS = {}
MAX_VIDEOS_EDITOR = 15
MAX_TAMANHO_VIDEO_MB = 150
FONTE_PADRAO = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONTE_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

# Modelos visuais de legenda: cada um define posição, cor e fundo.
# {w}/{h}/{th} são substituídos pelos valores reais do vídeo em tempo de execução.
MODELOS_LEGENDA = {
    "classico": "fontcolor=white:fontsize=h/22:box=1:boxcolor=black@0.55:boxborderw=10:x=(w-text_w)/2:y=h-th-40",
    "impacto": "fontcolor=yellow:fontsize=h/18:box=1:boxcolor=black@0.7:boxborderw=14:x=(w-text_w)/2:y=50",
    "neon": "fontcolor=#25f4ee:fontsize=h/20:borderw=3:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2",
    "minimalista": "fontcolor=white@0.9:fontsize=h/28:box=1:boxcolor=black@0.35:boxborderw=6:x=30:y=h-th-30",
}

# Modelo "citação": faixa colorida full-width com texto serifado centralizado.
# Diferente dos outros, precisa de um filtro extra (drawbox) antes do drawtext,
# por isso é tratado separado dos demais no processar_video_com_cta.
# IMPORTANTE: drawbox usa as variáveis ih/iw (altura/largura de entrada),
# já o drawtext usa h/w — são filtros diferentes com convenções diferentes.
FAIXA_Y_INICIO_BOX = "ih*0.42"     # usado no drawbox
FAIXA_ALTURA_BOX = "ih*0.18"       # usado no drawbox
FAIXA_Y_INICIO_TXT = "h*0.42"      # usado no drawtext
FAIXA_ALTURA_TXT = "h*0.18"        # usado no drawtext
CORES_FAIXA_CITACAO = {
    "branco": ("white@1", "black"),
    "preto": ("black@1", "white"),
    "vermelho": ("0xD62828@1", "white"),
}


LIMITE_DIMENSAO_VIDEO = 1920  # baixa a resolução se passar disso, pra processar mais rápido


def probe_video(path: str):
    """Retorna (largura, altura, fps, tem_audio) de um vídeo via ffprobe."""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width,height,r_frame_rate",
           "-of", "json", path]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    info = json.loads(out.stdout)["streams"][0]
    w, h = info["width"], info["height"]
    num, den = info["r_frame_rate"].split("/")
    fps = float(num) / float(den) if float(den) != 0 else 30.0

    cmd_audio = ["ffprobe", "-v", "error", "-select_streams", "a",
                 "-show_entries", "stream=index", "-of", "csv=p=0", path]
    out_audio = subprocess.run(cmd_audio, capture_output=True, text=True, timeout=30)
    tem_audio = bool(out_audio.stdout.strip())

    # Reduz vídeos muito grandes (ex: 4K de celular) — acelera bastante o
    # processamento, já que menos pixels = menos trabalho em todo o pipeline.
    maior_lado = max(w, h)
    if maior_lado > LIMITE_DIMENSAO_VIDEO:
        fator = LIMITE_DIMENSAO_VIDEO / maior_lado
        w = int(w * fator) // 2 * 2   # precisa ser par pro codec h264
        h = int(h * fator) // 2 * 2

    return w, h, fps, tem_audio


def extrair_audio_para_transcricao(input_path: str, saida_path: str):
    """Extrai só o áudio (comprimido, mono) pra mandar pra API — bem menor
    que o vídeo inteiro, o que acelera o upload e evita o limite de 25MB."""
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vn", "-ac", "1", "-ar", "16000",
           "-b:a", "64k", saida_path]
    subprocess.run(cmd, capture_output=True, timeout=60, check=True)


def transcrever_segmentos(api_key: str, input_path: str, pasta_trabalho: Path,
                           max_duracao_segmento: float = 4.0) -> list:
    """Transcreve o áudio do vídeo via Whisper (OpenAI) e devolve uma lista
    de segmentos [{start, end, text}], já quebrados em pedaços curtos (estilo
    legenda de Reels/TikTok) mesmo quando a fala original vem em frases longas."""
    audio_path = pasta_trabalho / "audio_transcricao.mp3"
    extrair_audio_para_transcricao(input_path, str(audio_path))

    with open(audio_path, "rb") as f:
        resp = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (audio_path.name, f, "audio/mpeg")},
            data={"model": "whisper-1", "response_format": "verbose_json"},
            timeout=180,
        )
    resp.raise_for_status()
    dados = resp.json()

    segmentos = []
    for seg in dados.get("segments", []):
        inicio, fim = seg["start"], seg["end"]
        texto = seg["text"].strip()
        if not texto:
            continue
        duracao_seg = fim - inicio

        if duracao_seg > max_duracao_segmento:
            # Quebra frases longas em pedaços menores, dividindo o tempo
            # proporcionalmente pelo número de palavras de cada pedaço.
            palavras = texto.split()
            n_partes = max(2, int(duracao_seg // max_duracao_segmento) + 1)
            tam_parte = max(1, len(palavras) // n_partes)
            for i in range(0, len(palavras), tam_parte):
                bloco = palavras[i:i + tam_parte]
                if not bloco:
                    continue
                frac_ini = i / len(palavras)
                frac_fim = min(1.0, (i + tam_parte) / len(palavras))
                segmentos.append({
                    "start": inicio + frac_ini * duracao_seg,
                    "end": inicio + frac_fim * duracao_seg,
                    "text": " ".join(bloco),
                })
        else:
            segmentos.append({"start": inicio, "end": fim, "text": texto})

    return segmentos


def _filtro_segmento_texto(idx: int, label_entrada: str, label_saida: str, txt_path: Path,
                            modelo: str, cor_fundo_citacao: str,
                            inicio: float = None, fim: float = None) -> str:
    """Monta o pedaço do filtro ffmpeg pra desenhar UM trecho de texto,
    opcionalmente só visível entre 'inicio' e 'fim' segundos (pra legenda
    automática sincronizada com a fala)."""
    enable_clause = f":enable='between(t,{inicio:.2f},{fim:.2f})'" if inicio is not None else ""

    if modelo == "citacao":
        cor_fundo, cor_texto = CORES_FAIXA_CITACAO.get(cor_fundo_citacao, CORES_FAIXA_CITACAO["branco"])
        return (
            f"[{label_entrada}]drawbox=x=0:y={FAIXA_Y_INICIO_BOX}:w=iw:h={FAIXA_ALTURA_BOX}:"
            f"color={cor_fundo}:t=fill{enable_clause}[vb{idx}]"
            f";[vb{idx}]drawtext=fontfile={FONTE_SERIF}:textfile={txt_path}:"
            f"fontcolor={cor_texto}:fontsize=h/24:line_spacing=8:"
            f"x=(w-text_w)/2:y=({FAIXA_Y_INICIO_TXT})+({FAIXA_ALTURA_TXT}-text_h)/2{enable_clause}[{label_saida}]"
        )
    estilo = MODELOS_LEGENDA.get(modelo, MODELOS_LEGENDA["classico"])
    return (
        f"[{label_entrada}]drawtext=fontfile={FONTE_PADRAO}:textfile={txt_path}:"
        f"{estilo}{enable_clause}[{label_saida}]"
    )


def construir_filtro_legenda(pasta_trabalho: Path, legenda_modelo: str, cor_fundo_citacao: str,
                              label_inicial: str, texto_manual: str = "", segmentos: list = None):
    """Monta a cadeia de filtros de legenda: um drawtext por segmento (modo
    automático, sincronizado no tempo) ou um único drawtext fixo (modo manual)."""
    partes = []
    label_atual = label_inicial

    if segmentos:
        for i, seg in enumerate(segmentos):
            txt_path = pasta_trabalho / f"legenda_{i}.txt"
            txt_path.write_text(seg["text"], encoding="utf-8")
            label_saida = f"vtxt{i}"
            partes.append(_filtro_segmento_texto(
                i, label_atual, label_saida, txt_path, legenda_modelo, cor_fundo_citacao,
                seg["start"], seg["end"],
            ))
            label_atual = label_saida
    elif texto_manual:
        txt_path = pasta_trabalho / "legenda.txt"
        txt_path.write_text(texto_manual, encoding="utf-8")
        label_saida = "vtxtM"
        partes.append(_filtro_segmento_texto(
            0, label_atual, label_saida, txt_path, legenda_modelo, cor_fundo_citacao,
        ))
        label_atual = label_saida

    return ";".join(partes), label_atual


def processar_video_com_cta(input_path: str, cta_path: str, brilho: float,
                             duracao: float, output_path: str,
                             legenda_texto: str = "", legenda_modelo: str = "classico",
                             cor_fundo_citacao: str = "branco",
                             legenda_segmentos: list = None,
                             pasta_trabalho: Path = None):
    """Aplica filtro de brilho, legenda opcional (manual ou por segmentos
    sincronizados), e cola a imagem de CTA no final."""
    w, h, fps, tem_audio = probe_video(input_path)

    # Se o vídeo original é maior que o limite, redimensiona antes de tudo —
    # isso é o que mais acelera o processamento (menos pixels em cada filtro).
    filtro_video = f"[0:v]scale={w}:{h}[v0scaled];[v0scaled]eq=brightness={brilho}[v0eq]"
    label_apos_brilho = "v0eq"

    if legenda_segmentos or legenda_texto:
        pedacos, label_apos_brilho = construir_filtro_legenda(
            pasta_trabalho, legenda_modelo, cor_fundo_citacao,
            label_inicial="v0eq", texto_manual=legenda_texto, segmentos=legenda_segmentos,
        )
        filtro_video += ";" + pedacos

    filtro = (
        f"{filtro_video};"
        f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v1];"
        f"[{label_apos_brilho}][v1]concat=n=2:v=1:a=0[outv]"
    )

    cmd = ["ffmpeg", "-y", "-i", input_path, "-loop", "1", "-t", str(duracao), "-i", cta_path]

    # "ultrafast" prioriza velocidade — importante no plano gratuito (CPU
    # bem limitada). O ganho de qualidade de presets mais lentos não compensa
    # o tempo extra aqui.
    if tem_audio:
        filtro += f";[0:a]apad=pad_dur={duracao}[outa]"
        cmd += ["-filter_complex", filtro, "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-c:a", "aac"]
    else:
        cmd += ["-filter_complex", filtro, "-map", "[outv]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"]

    cmd += ["-movflags", "+faststart", output_path]

    resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=280)
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr[-800:])


# Quantos vídeos processar ao mesmo tempo. No plano Free/Starter (menos de
# 1 CPU inteiro) o ganho é pequeno — vem principalmente das partes que
# esperam rede/disco (upload, chamada da API de transcrição), não do
# processamento de vídeo em si. A partir do plano Standard (1 CPU+) o ganho
# fica bem mais real. Ajuste esse número conforme o plano do Render.
EDITOR_WORKERS_PARALELOS = 2


def _processar_um_video(v: Path, pasta_saida: Path, cta_path: str, brilho: float,
                         duracao: float, legenda_texto: str, legenda_modelo: str,
                         cor_fundo_citacao: str, modo_legenda: str, api_key: str,
                         job: dict, lock: threading.Lock):
    """Processa 1 vídeo isoladamente — cada vídeo ganha sua própria pasta de
    trabalho temporária, pra não colidir com os outros rodando em paralelo."""
    pasta_temp_video = pasta_saida.parent / f"tmp_{v.stem}"
    pasta_temp_video.mkdir(exist_ok=True)

    try:
        legenda_segmentos = None
        texto_para_video = legenda_texto

        if modo_legenda == "automatica" and legenda_texto == "__AUTO__":
            with lock:
                job["arquivo_atual"] = f"transcrevendo {v.name}"
            legenda_segmentos = transcrever_segmentos(api_key, str(v), pasta_temp_video)
            texto_para_video = ""  # usa os segmentos, não texto fixo

        saida = pasta_saida / f"editado_{v.stem}.mp4"
        processar_video_com_cta(
            str(v), cta_path, brilho, duracao, str(saida),
            legenda_texto=texto_para_video, legenda_modelo=legenda_modelo,
            cor_fundo_citacao=cor_fundo_citacao, legenda_segmentos=legenda_segmentos,
            pasta_trabalho=pasta_temp_video,
        )
        with lock:
            job["concluidos"] += 1
        return ("ok", saida, None)
    except Exception as e:
        return ("erro", v.name, str(e))
    finally:
        shutil.rmtree(pasta_temp_video, ignore_errors=True)


def editor_job_worker(job_id: str, pasta_videos: Path, cta_path: str, brilho: float,
                       duracao: float, legenda_texto: str, legenda_modelo: str,
                       cor_fundo_citacao: str, modo_legenda: str, api_key: str):
    job = EDITOR_JOBS[job_id]
    pasta_saida = pasta_videos / "saida"
    pasta_saida.mkdir(exist_ok=True)

    videos = sorted(pasta_videos.glob("video_*"))
    job["total"] = len(videos)
    job["status"] = "processando"

    processados = []
    erros = []
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=EDITOR_WORKERS_PARALELOS) as executor:
        futuros = [
            executor.submit(
                _processar_um_video, v, pasta_saida, cta_path, brilho, duracao,
                legenda_texto, legenda_modelo, cor_fundo_citacao, modo_legenda,
                api_key, job, lock,
            )
            for v in videos
        ]
        for futuro in as_completed(futuros):
            status, resultado, detalhe = futuro.result()
            if status == "ok":
                processados.append(resultado)
            else:
                erros.append(f"{resultado}: {detalhe}")

    if not processados:
        job["status"] = "erro"
        job["erro"] = "Nenhum vídeo processado com sucesso. " + (erros[0] if erros else "")
        shutil.rmtree(pasta_videos, ignore_errors=True)
        return

    zip_path = EDITOR_BASE_TMP / f"{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in processados:
            zf.write(f, arcname=f.name)

    job["status"] = "concluido"
    job["zip_path"] = str(zip_path)
    job["total"] = len(processados)
    job["criado_em"] = time.time()

    shutil.rmtree(pasta_videos, ignore_errors=True)


# ---------------------------------------------------------
# Gerador IA: copies + imagens via OpenAI, cortadas em 9:16,
# com opção de virar reels animados com som ambiente
# ---------------------------------------------------------
GERADOR_BASE_TMP = Path(tempfile.gettempdir()) / "gerador_jobs"
GERADOR_BASE_TMP.mkdir(exist_ok=True)
GERADOR_JOBS = {}
MAX_IMAGENS_GERADOR = 40

PROMPTS_ESTILO = {
    "foto_livro": (
        "A realistic photo of a hand holding an open book, warm natural sunlight, "
        "shadows of leaves across the page, cozy aesthetic desk or balcony background, "
        "no text or letters anywhere in the image, empty blank page, photorealistic"
    ),
    "ilustrado_cosmico": (
        "A dreamy illustrated cosmic night sky scene, galaxy, stars, soft silhouette "
        "of a person looking at the stars, purple and pink nebula colors, no text or "
        "letters anywhere in the image, digital painting style"
    ),
}


def chamar_openai_copies(api_key: str, funil: str, exemplos: list, quantidade: int) -> list:
    """Pede pra OpenAI gerar N copies (título/apoio/cta) originais, inspiradas
    no funil e nos exemplos de referência fornecidos pelo usuário."""
    exemplos_txt = "\n".join(f"- {e}" for e in exemplos[:15]) if exemplos else "(nenhum exemplo fornecido ainda)"

    prompt_sistema = (
        "Você é um copywriter especialista em conteúdo viral para Instagram/Facebook "
        "no nicho de conteúdo espiritual/motivacional/relacionamentos. Sua tarefa é criar "
        "frases curtas, originais e emocionalmente impactantes — nunca copie os exemplos "
        "literalmente, apenas se inspire no tom, estrutura e nível de impacto deles."
    )
    prompt_usuario = (
        f"Funil/nicho atual: {funil}\n\n"
        f"Exemplos de copies que estão convertendo bem nesse nicho:\n{exemplos_txt}\n\n"
        f"Crie {quantidade} copies ORIGINAIS e diferentes entre si, no mesmo espírito "
        f"emocional dos exemplos. Cada copy deve ter:\n"
        f"- titulo: frase principal, curta e impactante (máx 8 palavras)\n"
        f"- apoio: uma segunda frase complementar (máx 12 palavras)\n"
        f"- cta: uma chamada pra ação curta, ex: 'leia o primeiro comentário'\n\n"
        f'Responda SOMENTE em JSON válido, no formato: '
        f'{{"copies": [{{"titulo": "...", "apoio": "...", "cta": "..."}}]}}'
    )

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.9,
        },
        timeout=60,
    )
    resp.raise_for_status()
    conteudo = resp.json()["choices"][0]["message"]["content"]
    dados = json.loads(conteudo)
    return dados.get("copies", [])


def chamar_openai_imagem_grade(api_key: str, estilo: str) -> Image.Image:
    """Pede pra OpenAI gerar 1 imagem retrato dividida em grade 2x2 (4 cenas
    diferentes, sem texto), pra depois cortar em 4 imagens 9:16 separadas."""
    base_prompt = PROMPTS_ESTILO.get(estilo, PROMPTS_ESTILO["foto_livro"])
    prompt = (
        f"A single image split into an even 2x2 grid by a thin visible white "
        f"dividing line (2 columns, 2 rows). Each of the 4 quadrants shows a "
        f"different variation of this scene: {base_prompt}. "
        f"Absolutely no text, letters, numbers or writing anywhere in the image."
    )

    resp = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-image-1",
            "prompt": prompt,
            "size": "1024x1536",
            "n": 1,
        },
        timeout=120,
    )
    resp.raise_for_status()
    dados = resp.json()["data"][0]

    if "b64_json" in dados and dados["b64_json"]:
        img_bytes = base64.b64decode(dados["b64_json"])
    else:
        img_resp = requests.get(dados["url"], timeout=60)
        img_resp.raise_for_status()
        img_bytes = img_resp.content

    return Image.open(io.BytesIO(img_bytes)).convert("RGB")


def cortar_grade_em_quatro(img: Image.Image) -> list:
    """Corta uma imagem 1024x1536 (grade 2x2) em 4 imagens 9:16 (1080x1920)."""
    w, h = img.size
    qw, qh = w // 2, h // 2

    quadrantes = []
    for i in range(4):
        x = (i % 2) * qw
        y = (i // 2) * qh
        quad = img.crop((x, y, x + qw, y + qh))
        largura_alvo = int(qh * 9 / 16)
        offset_x = max(0, (qw - largura_alvo) // 2)
        quad_916 = quad.crop((offset_x, 0, offset_x + largura_alvo, qh))
        quad_final = quad_916.resize((1080, 1920), Image.LANCZOS)
        quadrantes.append(quad_final)
    return quadrantes


def _quebrar_texto(draw, texto, fonte, largura_max):
    palavras = texto.split()
    linhas, linha_atual = [], ""
    for palavra in palavras:
        teste = (linha_atual + " " + palavra).strip()
        bbox = draw.textbbox((0, 0), teste, font=fonte)
        if bbox[2] - bbox[0] <= largura_max:
            linha_atual = teste
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra
    if linha_atual:
        linhas.append(linha_atual)
    return linhas


def aplicar_texto_quote(img: Image.Image, titulo: str, apoio: str, cta: str,
                         cor_destaque=(255, 45, 85)) -> Image.Image:
    """Sobrepõe título + apoio (topo) e CTA (base) na imagem, com gradientes
    escuros por trás pra garantir legibilidade em qualquer fundo."""
    img = img.convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for y in range(int(h * 0.42)):
        alpha = int(190 * (1 - y / (h * 0.42)) ** 0.6)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    faixa_baixo = int(h * 0.20)
    for y in range(faixa_baixo):
        yy = h - faixa_baixo + y
        alpha = int(200 * (y / faixa_baixo) ** 0.6)
        draw.line([(0, yy), (w, yy)], fill=(0, 0, 0, alpha))

    fonte_titulo = ImageFont.truetype(FONTE_SERIF, 58)
    fonte_apoio = ImageFont.truetype(FONTE_SERIF, 34)
    fonte_cta = ImageFont.truetype(FONTE_PADRAO, 36)

    margem = 70
    y_cursor = 90

    for linha in _quebrar_texto(draw, titulo, fonte_titulo, w - margem * 2):
        draw.text((w / 2, y_cursor), linha, font=fonte_titulo, fill=(255, 255, 255, 255), anchor="ma")
        bbox = draw.textbbox((0, 0), linha, font=fonte_titulo)
        y_cursor += (bbox[3] - bbox[1]) + 14

    if apoio:
        y_cursor += 16
        for linha in _quebrar_texto(draw, apoio, fonte_apoio, w - margem * 2):
            draw.text((w / 2, y_cursor), linha, font=fonte_apoio, fill=(230, 230, 230, 255), anchor="ma")
            bbox = draw.textbbox((0, 0), linha, font=fonte_apoio)
            y_cursor += (bbox[3] - bbox[1]) + 10

    if cta:
        texto_cta = cta.upper()
        y_cta = h - 130
        draw.text((w / 2, y_cta), texto_cta, font=fonte_cta, fill=cor_destaque + (255,), anchor="ma")
        draw.text((w / 2, y_cta + 55), "\U0001F447", font=fonte_cta, fill=(255, 255, 255, 255), anchor="ma")

    return Image.alpha_composite(img, overlay).convert("RGB")


def gerar_som_ambiente(caminho_saida: str, duracao: float = 6.0):
    """Sintetiza um som ambiente suave (acorde de 3 tons com fade), sem
    depender de nenhuma API — usado como música de fundo dos reels."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=196:duration={duracao}",
        "-f", "lavfi", "-i", f"sine=frequency=246.94:duration={duracao}",
        "-f", "lavfi", "-i", f"sine=frequency=293.66:duration={duracao}",
        "-filter_complex",
        "[0][1][2]amix=inputs=3:duration=longest:weights='0.5 0.4 0.35',"
        "volume=0.35,afade=t=in:d=1.5,afade=t=out:st=" + str(max(0, duracao - 1.5)) + ":d=1.5,lowpass=f=2000",
        "-ar", "44100", caminho_saida,
    ]
    subprocess.run(cmd, capture_output=True, timeout=60, check=True)


def criar_reel_de_imagem(caminho_imagem: str, caminho_audio: str, caminho_saida: str, duracao: float = 6.0):
    """Anima a imagem com um zoom lento (Ken Burns) e junta com o som ambiente."""
    frames = int(duracao * 25)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", caminho_imagem,
        "-i", caminho_audio,
        "-vf", f"zoompan=z='min(zoom+0.0008,1.15)':d={frames}:s=1080x1920:fps=25",
        "-t", str(duracao),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        caminho_saida,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120, check=True)


def gerador_job_worker(job_id: str, api_key: str, funil: str, exemplos: list,
                        estilo: str, quantidade: int, gerar_reels: bool):
    job = GERADOR_JOBS[job_id]
    pasta_job = GERADOR_BASE_TMP / job_id
    pasta_job.mkdir(exist_ok=True)

    try:
        job["status"] = "gerando_copies"
        copies = chamar_openai_copies(api_key, funil, exemplos, quantidade)
        if not copies:
            job["status"] = "erro"
            job["erro"] = "A IA não retornou nenhuma copy. Tenta de novo."
            return

        job["status"] = "gerando_imagens"
        job["total"] = len(copies)
        job["concluidos"] = 0

        imagens_finais = []
        for i in range(0, len(copies), 4):
            lote = copies[i:i + 4]
            grade = chamar_openai_imagem_grade(api_key, estilo)
            quadrantes = cortar_grade_em_quatro(grade)

            for quad, copy in zip(quadrantes, lote):
                final = aplicar_texto_quote(
                    quad, copy.get("titulo", ""), copy.get("apoio", ""), copy.get("cta", "")
                )
                caminho = pasta_job / f"imagem_{len(imagens_finais):02d}.png"
                final.save(caminho)
                imagens_finais.append(caminho)
                job["concluidos"] += 1

        arquivos_finais = list(imagens_finais)

        if gerar_reels:
            job["status"] = "gerando_reels"
            job["concluidos_reels"] = 0
            audio_path = pasta_job / "som_ambiente.mp3"
            gerar_som_ambiente(str(audio_path), duracao=6.0)

            for img_path in imagens_finais:
                reel_path = pasta_job / f"{img_path.stem}_reel.mp4"
                try:
                    criar_reel_de_imagem(str(img_path), str(audio_path), str(reel_path), duracao=6.0)
                    arquivos_finais.append(reel_path)
                except Exception:
                    pass  # se um reel falhar, mantém a imagem estática e segue
                job["concluidos_reels"] += 1

        zip_path = GERADOR_BASE_TMP / f"{job_id}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in arquivos_finais:
                zf.write(f, arcname=f.name)

        job["status"] = "concluido"
        job["zip_path"] = str(zip_path)
        job["total"] = len(imagens_finais)
        job["criado_em"] = time.time()

    except requests.exceptions.HTTPError as e:
        job["status"] = "erro"
        detalhe = ""
        try:
            detalhe = e.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        job["erro"] = f"Erro na API da OpenAI: {detalhe or str(e)}"
    except Exception as e:
        job["status"] = "erro"
        job["erro"] = str(e)
    finally:
        # Mantém as imagens/vídeos zipados, mas limpa os arquivos soltos
        for f in pasta_job.glob("*"):
            if f.suffix != ".zip":
                try:
                    f.unlink()
                except Exception:
                    pass


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


@app.route("/editor")
def editor_page():
    return PAGINA_EDITOR_HTML


@app.route("/api/editor/iniciar", methods=["POST"])
def editor_iniciar():
    videos = request.files.getlist("videos")
    cta = request.files.get("cta")

    if not videos:
        return jsonify({"erro": "Envie pelo menos 1 vídeo"}), 400
    if len(videos) > MAX_VIDEOS_EDITOR:
        return jsonify({"erro": f"Máximo de {MAX_VIDEOS_EDITOR} vídeos por vez"}), 400
    if not cta:
        return jsonify({"erro": "Envie a imagem do CTA"}), 400

    try:
        brilho_bruto = float(request.form.get("brilho", 0))
    except (TypeError, ValueError):
        brilho_bruto = 0
    brilho = max(-1.0, min(brilho_bruto / 100.0, 1.0))  # escala -50..50 -> -0.5..0.5

    try:
        duracao = float(request.form.get("duracao", 5))
    except (TypeError, ValueError):
        duracao = 5
    duracao = max(1, min(duracao, 15))

    usar_legenda = request.form.get("usar_legenda", "0") == "1"
    modo_legenda = request.form.get("modo_legenda", "manual").strip()
    api_key = request.form.get("api_key", "").strip()

    if usar_legenda and modo_legenda == "automatica":
        if not api_key:
            return jsonify({"erro": "Configura sua chave OpenAI na aba Config primeiro"}), 400
        legenda_texto = "__AUTO__"  # sinaliza pro worker que é modo automático
    else:
        legenda_texto = request.form.get("texto_legenda", "").strip() if usar_legenda else ""

    legenda_modelo = request.form.get("modelo_legenda", "classico").strip()
    modelos_validos = set(MODELOS_LEGENDA.keys()) | {"citacao"}
    if legenda_modelo not in modelos_validos:
        legenda_modelo = "classico"

    cor_fundo_citacao = request.form.get("cor_fundo_citacao", "branco").strip()
    if cor_fundo_citacao not in CORES_FAIXA_CITACAO:
        cor_fundo_citacao = "branco"

    job_id = uuid.uuid4().hex[:12]
    pasta_job = EDITOR_BASE_TMP / job_id
    pasta_job.mkdir(exist_ok=True)

    for i, v in enumerate(videos):
        nome_seguro = secure_filename(v.filename or f"video_{i}.mp4")
        v.save(str(pasta_job / f"video_{i:02d}_{nome_seguro}"))

    nome_cta = secure_filename(cta.filename or "cta.png")
    cta_path = pasta_job / f"cta_{nome_cta}"
    cta.save(str(cta_path))

    EDITOR_JOBS[job_id] = {
        "status": "na_fila",
        "concluidos": 0,
        "total": len(videos),
        "criado_em": time.time(),
    }

    t = threading.Thread(
        target=editor_job_worker,
        args=(job_id, pasta_job, str(cta_path), brilho, duracao, legenda_texto,
              legenda_modelo, cor_fundo_citacao, modo_legenda, api_key),
        daemon=True,
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/editor/status/<job_id>")
def editor_status(job_id):
    job = EDITOR_JOBS.get(job_id)
    if not job:
        return jsonify({"erro": "job não encontrado"}), 404
    resposta = {
        "status": job["status"],
        "concluidos": job.get("concluidos", 0),
        "total": job.get("total", 0),
        "arquivo_atual": job.get("arquivo_atual", ""),
    }
    if job["status"] == "erro":
        resposta["erro"] = job.get("erro")
    return jsonify(resposta)


@app.route("/api/editor/baixar/<job_id>")
def editor_baixar(job_id):
    job = EDITOR_JOBS.get(job_id)
    if not job or job["status"] != "concluido":
        return jsonify({"erro": "arquivo ainda não está pronto"}), 400
    return send_file(job["zip_path"], as_attachment=True, download_name=f"editados_{job_id}.zip")


@app.route("/gerador")
def gerador_page():
    return PAGINA_GERADOR_HTML


@app.route("/config")
def config_page():
    return PAGINA_CONFIG_HTML


@app.route("/api/gerador/iniciar", methods=["POST"])
def gerador_iniciar():
    data = request.get_json(force=True)
    api_key = data.get("api_key", "").strip()
    funil = data.get("funil", "").strip()
    exemplos = data.get("exemplos", [])
    estilo = data.get("estilo", "foto_livro")
    gerar_reels = bool(data.get("gerar_reels", False))

    if not api_key:
        return jsonify({"erro": "Informe sua chave da API OpenAI"}), 400
    if not funil:
        return jsonify({"erro": "Descreva o funil/nicho atual"}), 400
    if estilo not in PROMPTS_ESTILO:
        estilo = "foto_livro"

    try:
        quantidade = int(data.get("quantidade", 8))
    except (TypeError, ValueError):
        quantidade = 8
    quantidade = max(4, min(quantidade, MAX_IMAGENS_GERADOR))
    quantidade = (quantidade + 3) // 4 * 4  # arredonda pra múltiplo de 4

    job_id = uuid.uuid4().hex[:12]
    GERADOR_JOBS[job_id] = {
        "status": "gerando_copies",
        "concluidos": 0,
        "total": quantidade,
        "criado_em": time.time(),
    }

    t = threading.Thread(
        target=gerador_job_worker,
        args=(job_id, api_key, funil, exemplos, estilo, quantidade, gerar_reels),
        daemon=True,
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/gerador/status/<job_id>")
def gerador_status(job_id):
    job = GERADOR_JOBS.get(job_id)
    if not job:
        return jsonify({"erro": "job não encontrado"}), 404
    resposta = {
        "status": job["status"],
        "concluidos": job.get("concluidos", 0),
        "concluidos_reels": job.get("concluidos_reels", 0),
        "total": job.get("total", 0),
    }
    if job["status"] == "erro":
        resposta["erro"] = job.get("erro")
    return jsonify(resposta)


@app.route("/api/gerador/baixar/<job_id>")
def gerador_baixar(job_id):
    job = GERADOR_JOBS.get(job_id)
    if not job or job["status"] != "concluido":
        return jsonify({"erro": "arquivo ainda não está pronto"}), 400
    return send_file(job["zip_path"], as_attachment=True, download_name=f"gerado_{job_id}.zip")


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

    expirados_editor = [jid for jid, j in EDITOR_JOBS.items() if agora - j.get("criado_em", agora) > 3600]
    for jid in expirados_editor:
        zip_path = EDITOR_BASE_TMP / f"{jid}.zip"
        if zip_path.exists():
            zip_path.unlink()
        pasta = EDITOR_BASE_TMP / jid
        if pasta.exists():
            shutil.rmtree(pasta, ignore_errors=True)
        EDITOR_JOBS.pop(jid, None)

    expirados_gerador = [jid for jid, j in GERADOR_JOBS.items() if agora - j.get("criado_em", agora) > 3600]
    for jid in expirados_gerador:
        zip_path = GERADOR_BASE_TMP / f"{jid}.zip"
        if zip_path.exists():
            zip_path.unlink()
        pasta = GERADOR_BASE_TMP / jid
        if pasta.exists():
            shutil.rmtree(pasta, ignore_errors=True)
        GERADOR_JOBS.pop(jid, None)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
