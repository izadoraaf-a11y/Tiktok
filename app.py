import os
import re
import shutil
import tempfile
import zipfile
import uuid
import random
import threading
import time
import base64
import json
import subprocess
import io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pytesseract
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename

import yt_dlp

app = Flask(__name__)

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
  button.secundario {
    width: 100%; padding: 10px; border-radius: 10px; border: 1px solid #333;
    background: #1a1a1a; color: #ccc; font-weight: 600; font-size: 13px; cursor: pointer;
  }
  .job-recente {
    background: #1a1a1a; border: 1px solid #262626; border-radius: 10px;
    padding: 12px; margin-bottom: 8px; font-size: 13px;
  }
  .job-recente a {
    display: inline-block; margin-top: 6px; color: #25f4ee; font-weight: 700; text-decoration: none;
  }
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
  .campo { margin-bottom: 12px; }
  .conta-salva {
    background: #1a1a1a; border: 1px solid #262626; border-radius: 10px;
    padding: 12px; margin-bottom: 8px; font-size: 13px;
  }
  .conta-salva .nome { font-weight: 700; color: #fff; }
  .conta-salva .detalhe { color: #888; font-size: 12px; margin-top: 2px; }
  .conta-salva .acoes { display: flex; gap: 8px; margin-top: 8px; }
  .conta-salva button {
    width: auto; flex: 1; padding: 8px; font-size: 12px; border-radius: 8px;
    background: #262626; color: #ccc; border: 1px solid #333; font-weight: 600;
  }
  .conta-salva button.usar { background: linear-gradient(135deg, #ff2d55, #25f4ee); color: #000; border: none; }
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
      <a href="/biblioteca">Biblioteca</a>
    </div>
    <h1>Baixador de Vídeos</h1>
    <p class="sub">TikTok, Instagram e Facebook — cole o link e baixe sem marca d'água</p>

    <div id="lista-contas-salvas" style="display:none; margin-bottom:16px;"></div>

    <input id="conta" type="text" placeholder="Link do vídeo, reel, post ou perfil" oninput="verificarContaConhecida()" />

    <div class="campo" style="margin-bottom:12px;">
      <label style="font-size:12px; color:#888;">Apelido (opcional — pra lembrar de qual conta é)</label>
      <input id="apelido-conta" type="text" placeholder="Ex: Conta A - clipes motivacionais" style="margin-top:4px;" />
    </div>

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
    <p id="aviso-conta-conhecida" style="display:none; font-size:12px; color:#25f4ee; margin-top:-6px; margin-bottom:12px;"></p>
    <p style="font-size:11px; color:#666; margin-top:-6px; margin-bottom:12px;">
      Contando a partir do <b>primeiro vídeo postado</b> pela conta. Ex: 1 até 10 = os 10
      primeiros vídeos que ela já postou. 11 até 20 = os próximos 10 (mais recentes que esses).
      (Intervalo só funciona pra conta do TikTok — Instagram e Facebook, use link de vídeo único.
      Pode demorar alguns segundos a mais no início pra contar o total de vídeos da conta.)
    </p>

    <button id="btn-iniciar" onclick="iniciar()">Baixar</button>

    <button type="button" class="secundario" style="margin-top:10px;" onclick="verRecentes()">
      🕓 Ver processamentos recentes (última hora)
    </button>
    <div id="lista-recentes" style="display:none; margin-top:12px;"></div>

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
  const apelido = document.getElementById('apelido-conta').value.trim();

  document.getElementById('btn-iniciar').disabled = true;
  document.getElementById('status-box').style.display = 'block';
  document.getElementById('download-link').style.display = 'none';
  document.getElementById('status-text').textContent = 'Iniciando...';
  document.getElementById('bar-fill').style.width = '5%';

  let resp, data;
  try {
    resp = await fetch('/api/iniciar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conta, de, ate, ordem: 'antigos' })
    });
    data = await resp.json();
  } catch (e) {
    document.getElementById('status-text').textContent = 'Erro de conexão ao iniciar. Verifica a internet e tenta de novo.';
    document.getElementById('btn-iniciar').disabled = false;
    return;
  }

  if (data.erro) {
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-iniciar').disabled = false;
    return;
  }

  jobId = data.job_id;
  localStorage.setItem('baixador_job_ativo', jobId);
  // Guarda o que estava sendo baixado, pra atualizar o histórico da conta
  // quando o download terminar (não dá pra saber isso só pelo job_id).
  localStorage.setItem('baixador_job_pendente_conta', JSON.stringify({ conta, de: Number(de), ate: Number(ate), apelido }));
  poller = setInterval(checarStatus, 2000);
}

async function checarStatus() {
  let resp, data;
  try {
    resp = await fetch('/api/status/' + jobId);
    data = await resp.json();
  } catch (e) {
    document.getElementById('status-text').textContent = 'Conexão instável... tentando de novo (o processamento continua no servidor).';
    return; // não limpa o poller — tenta de novo na próxima rodada
  }

  if (data.status === 'baixando') {
    document.getElementById('status-text').textContent = `Baixando... (${data.concluidos} vídeos concluídos)`;
    const pct = Math.min(90, 10 + data.concluidos * 5);
    document.getElementById('bar-fill').style.width = pct + '%';
  } else if (data.status === 'na_fila' || data.status === 'iniciando') {
    document.getElementById('status-text').textContent = 'Preparando...';
  } else if (data.status === 'concluido') {
    clearInterval(poller);
    localStorage.removeItem('baixador_job_ativo');
    const totalTexto = data.total_videos != null ? `${data.total_videos} vídeos baixados` : 'vídeos prontos';
    document.getElementById('status-text').textContent = `Pronto! ${totalTexto}.`;
    document.getElementById('bar-fill').style.width = '100%';
    const link = document.getElementById('download-link');
    link.href = '/api/baixar/' + jobId;
    link.style.display = 'block';
    document.getElementById('btn-iniciar').disabled = false;
    registrarConclusaoNoHistorico();
  } else if (data.status === 'erro') {
    clearInterval(poller);
    localStorage.removeItem('baixador_job_ativo');
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-iniciar').disabled = false;
  } else if (data.erro || !resp.ok) {
    clearInterval(poller);
    localStorage.removeItem('baixador_job_ativo');
    document.getElementById('status-text').textContent = 'Esse processamento anterior não foi encontrado (pode ter se perdido num reinício do servidor). Pode iniciar um novo.';
    document.getElementById('btn-iniciar').disabled = false;
  }
}

async function verRecentes() {
  const div = document.getElementById('lista-recentes');
  div.style.display = 'block';
  div.innerHTML = '<p class="ajuda">Buscando...</p>';

  const resp = await fetch('/api/recentes');
  const data = await resp.json();

  if (!data.jobs || data.jobs.length === 0) {
    div.innerHTML = '<p class="ajuda">Nenhum processamento na última hora.</p>';
    return;
  }

  div.innerHTML = '';
  data.jobs.forEach(j => {
    const item = document.createElement('div');
    item.className = 'job-recente';
    let statusTexto = '';
    if (j.status === 'concluido' && j.recuperado_do_disco) statusTexto = '✅ Pronto (recuperado do disco)';
    else if (j.status === 'concluido') statusTexto = `✅ Pronto — ${j.total ?? '?'} vídeo(s)`;
    else if (j.status === 'erro') statusTexto = '❌ Erro';
    else statusTexto = '⏳ Processando';

    item.innerHTML = `
      <div>${statusTexto} — há ${j.minutos_atras} min</div>
      <div style="color:#666; font-size:11px;">ID: ${j.job_id}</div>
      ${j.status === 'concluido' ? `<a href="/api/baixar/${j.job_id}">⬇ Baixar ZIP</a>` : ''}
    `;
    div.appendChild(item);
  });
}

function normalizarChaveConta(conta) {
  return conta.trim().toLowerCase().replace(/^@/, '').replace(/\\/$/, '');
}

function carregarContasSalvas() {
  return JSON.parse(localStorage.getItem('baixador_contas') || '{}');
}

function salvarContasSalvas(contas) {
  localStorage.setItem('baixador_contas', JSON.stringify(contas));
}

function registrarConclusaoNoHistorico() {
  const pendenteRaw = localStorage.getItem('baixador_job_pendente_conta');
  if (!pendenteRaw) return;
  localStorage.removeItem('baixador_job_pendente_conta');

  const pendente = JSON.parse(pendenteRaw);
  const chave = normalizarChaveConta(pendente.conta);
  const contas = carregarContasSalvas();
  const existente = contas[chave] || { total_baixados: 0, apelido: '' };

  contas[chave] = {
    conta_original: pendente.conta,
    apelido: pendente.apelido || existente.apelido || '',
    total_baixados: Math.max(existente.total_baixados || 0, pendente.ate),
    atualizado_em: new Date().toISOString(),
  };
  salvarContasSalvas(contas);
  renderizarContasSalvas();
}

function renderizarContasSalvas() {
  const contas = carregarContasSalvas();
  const div = document.getElementById('lista-contas-salvas');
  const chaves = Object.keys(contas);

  if (chaves.length === 0) {
    div.style.display = 'none';
    return;
  }

  div.style.display = 'block';
  div.innerHTML = '<label style="margin-bottom:8px;">📋 Contas já usadas</label>';

  chaves
    .sort((a, b) => new Date(contas[b].atualizado_em) - new Date(contas[a].atualizado_em))
    .forEach(chave => {
      const c = contas[chave];
      const item = document.createElement('div');
      item.className = 'conta-salva';
      const proxDe = c.total_baixados + 1;
      const proxAte = c.total_baixados + 10;
      item.innerHTML = `
        <div class="nome">${c.apelido || c.conta_original}</div>
        <div class="detalhe">${c.conta_original} — ${c.total_baixados} vídeo(s) já baixado(s)</div>
        <div class="acoes">
          <button class="usar" onclick='baixarProximosDaConta(${JSON.stringify(chave)})'>⬇ Baixar próximos (${proxDe}-${proxAte})</button>
          <button onclick='usarContaSalva(${JSON.stringify(chave)})'>Usar</button>
          <button onclick='removerContaSalva(${JSON.stringify(chave)})'>✕</button>
        </div>
      `;
      div.appendChild(item);
    });
}

function usarContaSalva(chave) {
  const contas = carregarContasSalvas();
  const c = contas[chave];
  if (!c) return;
  document.getElementById('conta').value = c.conta_original;
  document.getElementById('apelido-conta').value = c.apelido || '';
  verificarContaConhecida();
}

function baixarProximosDaConta(chave) {
  const contas = carregarContasSalvas();
  const c = contas[chave];
  if (!c) return;
  document.getElementById('conta').value = c.conta_original;
  document.getElementById('apelido-conta').value = c.apelido || '';
  document.getElementById('de').value = c.total_baixados + 1;
  document.getElementById('ate').value = c.total_baixados + 10;
  verificarContaConhecida();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function removerContaSalva(chave) {
  const contas = carregarContasSalvas();
  delete contas[chave];
  salvarContasSalvas(contas);
  renderizarContasSalvas();
}

function verificarContaConhecida() {
  const conta = document.getElementById('conta').value.trim();
  const aviso = document.getElementById('aviso-conta-conhecida');
  if (!conta) { aviso.style.display = 'none'; return; }

  const chave = normalizarChaveConta(conta);
  const contas = carregarContasSalvas();
  const c = contas[chave];

  if (c) {
    aviso.style.display = 'block';
    aviso.textContent = `📋 Essa conta já tem ${c.total_baixados} vídeo(s) baixado(s). ` +
      `Clica em "Baixar próximos" na lista acima pra continuar de onde parou, ou ajusta o intervalo manualmente.`;
  } else {
    aviso.style.display = 'none';
  }
}

renderizarContasSalvas();

// Retoma automaticamente um processamento que ficou rodando em segundo
// plano no servidor (ex: você desligou o celular ou saiu do app).
(function retomarJobAtivo() {
  const jobSalvo = localStorage.getItem('baixador_job_ativo');
  if (!jobSalvo) return;
  jobId = jobSalvo;
  document.getElementById('status-box').style.display = 'block';
  document.getElementById('status-text').textContent = 'Retomando processamento anterior...';
  document.getElementById('btn-iniciar').disabled = true;
  poller = setInterval(checarStatus, 2000);
  checarStatus();
})();
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
  button.secundario {
    width: 100%; padding: 10px; border-radius: 10px; border: 1px solid #333;
    background: #1a1a1a; color: #ccc; font-weight: 600; font-size: 13px; cursor: pointer;
  }
  .job-recente {
    background: #1a1a1a; border: 1px solid #262626; border-radius: 10px;
    padding: 12px; margin-bottom: 8px; font-size: 13px;
  }
  .job-recente a {
    display: inline-block; margin-top: 6px; color: #25f4ee; font-weight: 700; text-decoration: none;
  }
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
      <a href="/biblioteca">Biblioteca</a>
    </div>
    <h1>Auto-editor</h1>
    <p class="sub">Filtro de brilho + CTA em massa no final dos seus vídeos</p>

    <button type="button" class="secundario" style="margin-bottom:18px;" onclick="verRecentes()">
      🕓 Ver processamentos recentes (última hora)
    </button>
    <div id="lista-recentes" style="display:none; margin-bottom:20px;"></div>

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
  let resp, data;
  try {
    resp = await fetch('/api/editor/status/' + jobId);
    data = await resp.json();
  } catch (e) {
    document.getElementById('status-text').textContent = 'Conexão instável... tentando de novo (o processamento continua no servidor).';
    return;
  }

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
  } else if (data.erro || !resp.ok) {
    // job não existe mais (perdido em algum reinício antigo do servidor) —
    // limpa e libera pra começar um processamento novo, em vez de ficar
    // perguntando pra sempre sobre um job que nunca mais vai responder.
    clearInterval(poller);
    localStorage.removeItem('editor_job_ativo');
    document.getElementById('status-text').textContent = 'Esse processamento anterior não foi encontrado (pode ter se perdido num reinício do servidor). Pode iniciar um novo.';
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

async function verRecentes() {
  const div = document.getElementById('lista-recentes');
  div.style.display = 'block';
  div.innerHTML = '<p class="ajuda">Buscando...</p>';

  const resp = await fetch('/api/editor/recentes');
  const data = await resp.json();

  if (!data.jobs || data.jobs.length === 0) {
    div.innerHTML = '<p class="ajuda">Nenhum processamento na última hora.</p>';
    return;
  }

  div.innerHTML = '';
  data.jobs.forEach(j => {
    const item = document.createElement('div');
    item.className = 'job-recente';
    let statusTexto = '';
    if (j.status === 'concluido' && j.recuperado_do_disco) statusTexto = '✅ Pronto (recuperado do disco)';
    else if (j.status === 'concluido') statusTexto = `✅ Pronto — ${j.total} vídeo(s)`;
    else if (j.status === 'erro') statusTexto = '❌ Erro';
    else statusTexto = `⏳ Processando (${j.concluidos}/${j.total})`;

    item.innerHTML = `
      <div>${statusTexto} — há ${j.minutos_atras} min</div>
      <div style="color:#666; font-size:11px;">ID: ${j.job_id}</div>
      ${j.status === 'concluido' ? `<a href="/api/editor/baixar/${j.job_id}">⬇ Baixar ZIP</a>` : ''}
    `;
    div.appendChild(item);
  });
}
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
  .job-recente {
    background: #1a1a1a; border: 1px solid #262626; border-radius: 10px;
    padding: 12px; margin-bottom: 8px; font-size: 13px;
  }
  .job-recente a {
    display: inline-block; margin-top: 6px; color: #25f4ee; font-weight: 700; text-decoration: none;
  }
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
      <a href="/biblioteca">Biblioteca</a>
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

    <p class="ajuda" style="margin: 12px 0 6px;">Ou envia prints e a IA transcreve pra você:</p>
    <div class="campo">
      <input id="imagens-copy" type="file" accept="image/*" multiple
             style="width:100%; padding:12px; border-radius:10px; border:1px dashed #333; background:#1a1a1a; color:#ccc; font-size:13px;" />
    </div>
    <button class="secundario" onclick="transcreverCopies()" id="btn-transcrever-copies">📝 Transcrever prints e adicionar</button>
    <p id="status-transcricao" class="ajuda" style="margin-top:8px; margin-bottom:16px;"></p>

    <div id="lista-exemplos"></div>

    <h2>📸 Estilo visual personalizado</h2>
    <p class="ajuda" style="margin-top:-6px; margin-bottom:12px;">
      Sobe várias fotos de referência do estilo que você quer (mesa, mão, luz,
      composição). A IA analisa o padrão visual — sem copiar texto ou marca
      das imagens — e guarda um estilo reutilizável.
    </p>

    <div class="campo">
      <input id="imagens-referencia" type="file" accept="image/*" multiple
             style="width:100%; padding:12px; border-radius:10px; border:1px dashed #333; background:#1a1a1a; color:#ccc; font-size:13px;" />
      <p class="ajuda">Até 10 imagens analisadas por vez (se enviar mais, usa as 10 primeiras).</p>
    </div>

    <button class="secundario" onclick="analisarEstilo()" id="btn-analisar-estilo">🔍 Analisar estilo com IA</button>
    <p id="status-estilo" class="ajuda" style="margin-top:8px;"></p>
    <div id="estilo-personalizado-status" class="ajuda" style="margin-top:6px; margin-bottom:20px;"></div>

    <h2>🎨 Geração</h2>

    <div class="campo">
      <label>Estilo visual</label>
      <select id="estilo">
        <option value="foto_livro">Foto realista — mão segurando livro/celular</option>
        <option value="ilustrado_cosmico">Ilustrado — cósmico/místico</option>
        <option value="personalizado">Meu estilo (dos exemplos que enviei)</option>
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

    <button type="button" class="secundario" style="margin-top:10px;" onclick="verRecentes()">
      🕓 Ver processamentos recentes (última hora)
    </button>
    <div id="lista-recentes" style="display:none; margin-top:12px;"></div>

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
  atualizarStatusEstiloPersonalizado();
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

async function analisarEstilo() {
  const apiKey = localStorage.getItem('api_key_openai') || '';
  const todasImagens = Array.from(document.getElementById('imagens-referencia').files);

  if (!apiKey) { alert('Configura sua chave OpenAI na aba Config primeiro'); return; }
  if (todasImagens.length === 0) { alert('Escolhe pelo menos 1 imagem de referência'); return; }

  const LIMITE = 10;
  const imagens = todasImagens.slice(0, LIMITE);
  const cortou = todasImagens.length > LIMITE;

  document.getElementById('btn-analisar-estilo').disabled = true;
  document.getElementById('status-estilo').textContent = cortou
    ? `Você escolheu ${todasImagens.length}, mas só as 10 primeiras são enviadas. Analisando...`
    : 'Analisando estilo (pode levar 20-30s)...';

  const formData = new FormData();
  for (const img of imagens) formData.append('imagens', img);
  formData.append('api_key', apiKey);

  try {
    const resp = await fetch('/api/gerador/analisar-estilo', { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.erro) {
      document.getElementById('status-estilo').textContent = 'Erro: ' + data.erro;
    } else {
      localStorage.setItem('estilo_personalizado_texto', data.descricao_estilo);
      document.getElementById('status-estilo').textContent =
        `✅ Estilo aprendido de ${data.imagens_analisadas} imagem(ns)! Selecione "Meu estilo" na lista abaixo.`;
      atualizarStatusEstiloPersonalizado();
    }
  } catch (e) {
    document.getElementById('status-estilo').textContent =
      'Erro de conexão (rede instável ou upload muito pesado). Tenta com menos imagens ou numa conexão melhor.';
  }
  document.getElementById('btn-analisar-estilo').disabled = false;
}

function atualizarStatusEstiloPersonalizado() {
  const texto = localStorage.getItem('estilo_personalizado_texto') || '';
  const div = document.getElementById('estilo-personalizado-status');
  if (texto) {
    div.innerHTML = '📌 Estilo salvo: <span style="color:#888;">' + texto.slice(0, 140) + '...</span> ' +
      '<a href="#" onclick="limparEstiloPersonalizado(); return false;" style="color:#ff2d55;">(limpar)</a>';
  } else {
    div.textContent = 'Nenhum estilo personalizado analisado ainda.';
  }
}

function limparEstiloPersonalizado() {
  localStorage.removeItem('estilo_personalizado_texto');
  atualizarStatusEstiloPersonalizado();
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

async function transcreverCopies() {
  const todasImagens = Array.from(document.getElementById('imagens-copy').files);

  if (todasImagens.length === 0) { alert('Escolhe pelo menos 1 print'); return; }

  const LIMITE = 10;
  const imagens = todasImagens.slice(0, LIMITE);
  const cortou = todasImagens.length > LIMITE;

  document.getElementById('btn-transcrever-copies').disabled = true;
  document.getElementById('status-transcricao').textContent = cortou
    ? `Você escolheu ${todasImagens.length}, mas só os 10 primeiros são enviados. Lendo (OCR local, sem custo)...`
    : 'Lendo os prints (OCR local, sem custo)...';

  const formData = new FormData();
  for (const img of imagens) formData.append('imagens', img);

  try {
    const resp = await fetch('/api/gerador/transcrever-copies', { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.erro) {
      document.getElementById('status-transcricao').textContent = 'Erro: ' + data.erro;
    } else {
      exemplos.push(...data.textos);
      localStorage.setItem('gerador_exemplos', JSON.stringify(exemplos));
      renderizarExemplos();
      document.getElementById('status-transcricao').textContent =
        `✅ ${data.textos.length} exemplo(s) transcrito(s) e adicionado(s) abaixo. Confere se saiu certinho — OCR pode errar em fontes estilizadas.`;
      document.getElementById('imagens-copy').value = '';
    }
  } catch (e) {
    document.getElementById('status-transcricao').textContent =
      'Erro de conexão (rede instável ou upload muito pesado). Tenta com menos imagens ou numa conexão melhor.';
  }
  document.getElementById('btn-transcrever-copies').disabled = false;
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
  const estiloCustomizado = localStorage.getItem('estilo_personalizado_texto') || '';
  const quantidade = document.getElementById('quantidade').value || 8;
  const gerarReels = document.getElementById('gerar-reels').checked;

  if (!apiKey) { alert('Configura sua chave da API OpenAI na aba Config primeiro'); return; }
  if (!funil) { alert('Descreve o funil/nicho atual'); return; }
  if (estilo === 'personalizado' && !estiloCustomizado) {
    alert('Analisa um estilo personalizado primeiro (na seção acima) ou escolhe outro estilo');
    return;
  }

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
      body: JSON.stringify({
        api_key: apiKey, funil, exemplos, estilo, estilo_customizado: estiloCustomizado,
        quantidade, gerar_reels: gerarReels,
      })
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
  localStorage.setItem('gerador_job_ativo', jobId);
  poller = setInterval(checarStatus, 3000);
}

async function checarStatus() {
  let resp, data;
  try {
    resp = await fetch('/api/gerador/status/' + jobId);
    data = await resp.json();
  } catch (e) {
    document.getElementById('status-text').textContent = 'Conexão instável... tentando de novo (o processamento continua no servidor).';
    return;
  }

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
    localStorage.removeItem('gerador_job_ativo');
    const totalTexto = data.total != null ? `${data.total} imagem(ns) geradas` : 'imagens prontas';
    document.getElementById('status-text').textContent = `Pronto! ${totalTexto}.`;
    document.getElementById('bar-fill').style.width = '100%';
    const link = document.getElementById('download-link');
    link.href = '/api/gerador/baixar/' + jobId;
    link.style.display = 'block';
    document.getElementById('btn-gerar').disabled = false;
  } else if (data.status === 'erro') {
    clearInterval(poller);
    localStorage.removeItem('gerador_job_ativo');
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-gerar').disabled = false;
  } else if (data.erro || !resp.ok) {
    clearInterval(poller);
    localStorage.removeItem('gerador_job_ativo');
    document.getElementById('status-text').textContent = 'Esse processamento anterior não foi encontrado (pode ter se perdido num reinício do servidor). Pode iniciar um novo.';
    document.getElementById('btn-gerar').disabled = false;
  }
}

async function verRecentes() {
  const div = document.getElementById('lista-recentes');
  div.style.display = 'block';
  div.innerHTML = '<p class="ajuda">Buscando...</p>';

  const resp = await fetch('/api/gerador/recentes');
  const data = await resp.json();

  if (!data.jobs || data.jobs.length === 0) {
    div.innerHTML = '<p class="ajuda">Nenhum processamento na última hora.</p>';
    return;
  }

  div.innerHTML = '';
  data.jobs.forEach(j => {
    const item = document.createElement('div');
    item.className = 'job-recente';
    let statusTexto = '';
    if (j.status === 'concluido' && j.recuperado_do_disco) statusTexto = '✅ Pronto (recuperado do disco)';
    else if (j.status === 'concluido') statusTexto = `✅ Pronto — ${j.total ?? '?'} imagem(ns)`;
    else if (j.status === 'erro') statusTexto = '❌ Erro';
    else statusTexto = '⏳ Processando';

    item.innerHTML = `
      <div>${statusTexto} — há ${j.minutos_atras} min</div>
      <div style="color:#666; font-size:11px;">ID: ${j.job_id}</div>
      ${j.status === 'concluido' ? `<a href="/api/gerador/baixar/${j.job_id}">⬇ Baixar ZIP</a>` : ''}
    `;
    div.appendChild(item);
  });
}

// Retoma automaticamente um processamento que ficou rodando em segundo
// plano no servidor (ex: você desligou o celular ou saiu do app).
(function retomarJobAtivo() {
  const jobSalvo = localStorage.getItem('gerador_job_ativo');
  if (!jobSalvo) return;
  jobId = jobSalvo;
  document.getElementById('status-box').style.display = 'block';
  document.getElementById('status-text').textContent = 'Retomando processamento anterior...';
  document.getElementById('btn-gerar').disabled = true;
  poller = setInterval(checarStatus, 3000);
  checarStatus();
})();

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
      <a href="/biblioteca">Biblioteca</a>
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

PAGINA_BIBLIOTECA_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Biblioteca</title>
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
  .nav { display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }
  .nav a {
    flex: 1; min-width: 60px; text-align: center; padding: 9px 4px; border-radius: 8px;
    text-decoration: none; font-size: 12px; font-weight: 600; color: #888;
    background: #1a1a1a; border: 1px solid #262626;
  }
  .nav a.ativo { color: #000; background: linear-gradient(135deg, #ff2d55, #25f4ee); border: none; }
  label { font-size: 13px; color: #ccc; display: block; margin-bottom: 6px; font-weight: 600; }
  .campo { margin-bottom: 16px; }
  .ajuda { font-size: 11px; color: #666; margin-top: 4px; line-height: 1.4; }
  input[type="file"], input[type="number"], select {
    width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #333;
    background: #1a1a1a; color: #ccc; font-size: 13px;
  }
  select { color: #fff; font-size: 15px; }
  button {
    width: 100%; padding: 14px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #ff2d55, #25f4ee);
    color: #000; font-weight: 700; font-size: 16px; cursor: pointer;
  }
  button.secundario {
    background: #1a1a1a; color: #ccc; border: 1px solid #333; font-weight: 600; font-size: 14px; padding: 10px;
  }
  button:disabled { opacity: 0.4; }
  .item-lib {
    display: flex; justify-content: space-between; align-items: center; gap: 8px;
    background: #1a1a1a; border: 1px solid #262626; border-radius: 8px;
    padding: 10px 12px; margin-bottom: 6px; font-size: 13px;
  }
  .item-lib .nome { color: #ccc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .item-lib .dur { color: #666; font-size: 11px; flex-shrink: 0; }
  .item-lib button {
    width: auto; padding: 4px 10px; font-size: 12px; background: #ff2d5522; color: #ff6b8a;
    border: 1px solid #ff2d5544; flex-shrink: 0;
  }
  .resumo-lib { font-size: 12px; color: #888; margin-bottom: 10px; }
  .job-recente {
    background: #1a1a1a; border: 1px solid #262626; border-radius: 10px;
    padding: 12px; margin-bottom: 8px; font-size: 13px;
  }
  .job-recente a { display: inline-block; margin-top: 6px; color: #25f4ee; font-weight: 700; text-decoration: none; }
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
      <a href="/editor">Editor</a>
      <a href="/gerador">Gerador</a>
      <a href="/biblioteca" class="ativo">Biblioteca</a>
      <a href="/config">Config</a>
    </div>
    <h1>Biblioteca</h1>
    <p class="sub">Guarda clipes curtos e áudios, e o app monta compilados aleatórios com transição e legenda</p>

    <h2 style="margin-top:0;">👤 Conta</h2>
    <div class="campo">
      <label>Biblioteca da conta</label>
      <select id="select-conta" onchange="trocarConta()"></select>
      <p class="ajuda">Cada conta tem sua própria biblioteca (vídeos, áudios, músicas) — separada das outras, pra não repetir material entre contas.</p>
    </div>
    <div class="campo" style="display:flex; gap:8px;">
      <input id="nova-conta-nome" type="text" placeholder="Nome de uma conta nova" style="flex:1; padding:12px; border-radius:10px; border:1px solid #333; background:#1a1a1a; color:#fff; font-size:14px;" />
      <button class="secundario" style="width:auto; padding:12px 16px;" onclick="criarConta()">+ Criar</button>
    </div>

    <h2>🪝 Vídeos de abertura (Hook)</h2>
    <div class="campo">
      <input id="input-hooks" type="file" accept="video/*" multiple />
      <p class="ajuda">Sempre entram <b>primeiro</b> no compilado. O app sorteia 1 desses pra abrir cada vídeo gerado.</p>
    </div>
    <button class="secundario" onclick="subirHooks()" id="btn-subir-hooks">⬆ Adicionar à biblioteca</button>
    <p id="status-upload-hooks" class="ajuda" style="margin-top:8px; margin-bottom:14px;"></p>
    <div id="lista-hooks"></div>

    <h2>🎬 Clipes do meio</h2>
    <div class="campo">
      <input id="input-videos" type="file" accept="video/*" multiple />
      <p class="ajuda">Sobe quantos clipes curtos quiser (ex: 6 segundos cada). Ficam guardados aqui até você apagar ou o servidor reiniciar. São sorteados aleatoriamente pro meio do vídeo.</p>
    </div>
    <button class="secundario" onclick="subirVideos()" id="btn-subir-videos">⬆ Adicionar à biblioteca</button>
    <p id="status-upload-videos" class="ajuda" style="margin-top:8px; margin-bottom:14px;"></p>
    <div class="resumo-lib" id="resumo-videos"></div>
    <div id="lista-videos"></div>

    <h2>🎯 Vídeos de encerramento (CTA)</h2>
    <div class="campo">
      <input id="input-ctas" type="file" accept="video/*" multiple />
      <p class="ajuda">Sempre entram <b>por último</b> no compilado. O app sorteia 1 desses pra fechar cada vídeo gerado.</p>
    </div>
    <button class="secundario" onclick="subirCtas()" id="btn-subir-ctas">⬆ Adicionar à biblioteca</button>
    <p id="status-upload-ctas" class="ajuda" style="margin-top:8px; margin-bottom:14px;"></p>
    <div id="lista-ctas"></div>

    <h2>🎵 Áudios</h2>
    <div class="campo">
      <input id="input-audios" type="file" accept="audio/*,video/*" multiple />
      <p class="ajuda">O áudio que vai tocar no compilado (ex: 1 minuto). Pode ser um arquivo de áudio ou até um vídeo (só o som é usado).</p>
    </div>
    <button class="secundario" onclick="subirAudios()" id="btn-subir-audios">⬆ Adicionar à biblioteca</button>
    <p id="status-upload-audios" class="ajuda" style="margin-top:8px; margin-bottom:14px;"></p>
    <div id="lista-audios"></div>

    <h2>🎶 Músicas de fundo (opcional)</h2>
    <div class="campo">
      <input id="input-musicas" type="file" accept="audio/*,video/*" multiple />
      <p class="ajuda">Guarda várias músicas de fundo. Quando ativado, o app sorteia uma aleatória por vídeo gerado, bem mais baixa que a voz.</p>
    </div>
    <button class="secundario" onclick="subirMusicas()" id="btn-subir-musicas">⬆ Adicionar à biblioteca</button>
    <p id="status-upload-musicas" class="ajuda" style="margin-top:8px; margin-bottom:14px;"></p>
    <div id="lista-musicas"></div>

    <h2>🎲 Gerar compilados</h2>

    <div class="campo">
      <label>Qual áudio usar</label>
      <select id="select-audio"><option value="">Nenhum áudio na biblioteca ainda</option></select>
    </div>

    <div class="campo">
      <label>Quantas versões diferentes</label>
      <input id="quantidade-compilado" type="number" value="1" min="1" max="20" />
      <p class="ajuda">Cada versão sorteia clipes diferentes da biblioteca (pode repetir clipe se precisar pra cobrir a duração do áudio).</p>
    </div>

    <div class="campo" style="display:flex; align-items:center; gap:8px;">
      <input id="usar-musica-compilado" type="checkbox" style="width:auto;" />
      <label style="margin-bottom:0;" for="usar-musica-compilado">Adicionar música de fundo aleatória (bem baixinha, atrás da voz)</label>
    </div>

    <div class="campo" style="display:flex; align-items:center; gap:8px;">
      <input id="usar-legenda-compilado" type="checkbox" style="width:auto;" onchange="alternarLegendaCompilado()" />
      <label style="margin-bottom:0;" for="usar-legenda-compilado">Adicionar legenda automática (transcreve o áudio)</label>
    </div>

    <div id="campos-legenda-compilado" style="display:none;">
      <div id="status-chave-compilado" class="campo" style="background:#1a1a1a; border:1px solid #262626; border-radius:10px; padding:10px 12px; font-size:12px;">
        Verificando chave da API...
      </div>
      <div class="campo">
        <label>Modelo da legenda</label>
        <select id="modelo-legenda-compilado" onchange="alternarCorFundoCompilado()">
          <option value="classico">Clássico — branco, embaixo</option>
          <option value="impacto">Impacto — amarelo, no topo</option>
          <option value="neon">Neon — ciano, no centro</option>
          <option value="minimalista">Minimalista — pequeno, canto</option>
          <option value="citacao">Citação — faixa colorida, centro</option>
        </select>
      </div>
      <div id="campo-cor-fundo-compilado" style="display:none;">
        <div class="campo">
          <label>Cor da faixa</label>
          <select id="cor-fundo-citacao-compilado">
            <option value="branco">Branco (texto preto)</option>
            <option value="preto">Preto (texto branco)</option>
            <option value="vermelho">Vermelho (texto branco)</option>
          </select>
        </div>
      </div>
    </div>

    <button id="btn-gerar-compilado" onclick="gerarCompilado()" style="margin-top:10px;">Gerar compilado(s)</button>

    <button type="button" class="secundario" style="margin-top:10px;" onclick="verRecentesCompilado()">
      🕓 Ver processamentos recentes (última hora)
    </button>
    <div id="lista-recentes" style="display:none; margin-top:12px;"></div>

    <div id="status-box">
      <div id="status-text">Preparando...</div>
      <div class="bar-bg"><div id="bar-fill" class="bar-fill"></div></div>
    </div>

    <a id="download-link" href="#">Baixar ZIP com os compilados</a>

    <p class="aviso">
      A biblioteca fica guardada no servidor enquanto ele não reiniciar (um novo deploy
      apaga tudo). Não é um armazenamento permanente — pense nela como uma "mesa de
      trabalho" temporária, não um HD.
    </p>
  </div>

<script>
let jobId = null;
let poller = null;
let contaAtual = localStorage.getItem('biblioteca_conta_atual') || '';

async function carregarContas() {
  const resp = await fetch('/api/biblioteca/contas');
  const data = await resp.json();
  const contas = data.contas || [];
  const select = document.getElementById('select-conta');

  if (contas.length === 0) {
    // Nenhuma conta ainda — cria a primeira automaticamente como "padrao"
    await criarContaSilenciosa('padrao');
    return;
  }

  select.innerHTML = '';
  contas.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = `${c.id} (${c.hooks} hooks, ${c.videos} meio, ${c.ctas} ctas, ${c.audios} áudios, ${c.musicas} músicas)`;
    select.appendChild(opt);
  });

  if (!contaAtual || !contas.some(c => c.id === contaAtual)) {
    contaAtual = contas[0].id;
  }
  select.value = contaAtual;
  localStorage.setItem('biblioteca_conta_atual', contaAtual);
}

async function criarContaSilenciosa(nome) {
  const resp = await fetch('/api/biblioteca/contas', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nome }),
  });
  const data = await resp.json();
  contaAtual = data.conta_criada || nome;
  localStorage.setItem('biblioteca_conta_atual', contaAtual);
  await carregarContas();
}

async function criarConta() {
  const nome = document.getElementById('nova-conta-nome').value.trim();
  if (!nome) { alert('Digite um nome pra conta nova'); return; }
  await criarContaSilenciosa(nome);
  document.getElementById('nova-conta-nome').value = '';
  await carregarBiblioteca();
}

function trocarConta() {
  contaAtual = document.getElementById('select-conta').value;
  localStorage.setItem('biblioteca_conta_atual', contaAtual);
  carregarBiblioteca();
}

async function carregarBiblioteca() {
  await Promise.all([carregarVideos(), carregarAudios(), carregarMusicas(), carregarHooks(), carregarCtas()]);
}

async function carregarHooks() {
  const resp = await fetch(`/api/biblioteca/${contaAtual}/hooks`);
  const data = await resp.json();
  const itens = data.itens || [];
  const div = document.getElementById('lista-hooks');

  if (itens.length === 0) {
    div.innerHTML = '<p class="ajuda">Nenhum vídeo de abertura ainda.</p>';
    return;
  }

  div.innerHTML = '';
  itens.forEach(item => {
    const el = document.createElement('div');
    el.className = 'item-lib';
    el.innerHTML = `
      <div class="nome">${item.nome}</div>
      <div class="dur">${item.duracao}s</div>
      <button onclick="apagarHook('${item.id}')">✕</button>
    `;
    div.appendChild(el);
  });
}

async function subirHooks() {
  const arquivos = document.getElementById('input-hooks').files;
  if (arquivos.length === 0) { alert('Escolhe pelo menos 1 vídeo de abertura'); return; }

  const formData = new FormData();
  for (const f of arquivos) formData.append('hooks', f);

  document.getElementById('btn-subir-hooks').disabled = true;
  document.getElementById('status-upload-hooks').textContent = 'Enviando...';

  try {
    const resp = await fetch(`/api/biblioteca/${contaAtual}/hooks`, { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.erro) {
      document.getElementById('status-upload-hooks').textContent = 'Erro: ' + data.erro;
    } else {
      document.getElementById('status-upload-hooks').textContent = '✅ Adicionado(s)!';
      document.getElementById('input-hooks').value = '';
      await carregarHooks();
    }
  } catch (e) {
    document.getElementById('status-upload-hooks').textContent = 'Erro de conexão. Tenta de novo.';
  }
  document.getElementById('btn-subir-hooks').disabled = false;
}

async function apagarHook(id) {
  await fetch(`/api/biblioteca/${contaAtual}/hooks/` + id, { method: 'DELETE' });
  await carregarHooks();
}

async function carregarCtas() {
  const resp = await fetch(`/api/biblioteca/${contaAtual}/ctas`);
  const data = await resp.json();
  const itens = data.itens || [];
  const div = document.getElementById('lista-ctas');

  if (itens.length === 0) {
    div.innerHTML = '<p class="ajuda">Nenhum vídeo de encerramento ainda.</p>';
    return;
  }

  div.innerHTML = '';
  itens.forEach(item => {
    const el = document.createElement('div');
    el.className = 'item-lib';
    el.innerHTML = `
      <div class="nome">${item.nome}</div>
      <div class="dur">${item.duracao}s</div>
      <button onclick="apagarCta('${item.id}')">✕</button>
    `;
    div.appendChild(el);
  });
}

async function subirCtas() {
  const arquivos = document.getElementById('input-ctas').files;
  if (arquivos.length === 0) { alert('Escolhe pelo menos 1 vídeo de encerramento'); return; }

  const formData = new FormData();
  for (const f of arquivos) formData.append('ctas', f);

  document.getElementById('btn-subir-ctas').disabled = true;
  document.getElementById('status-upload-ctas').textContent = 'Enviando...';

  try {
    const resp = await fetch(`/api/biblioteca/${contaAtual}/ctas`, { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.erro) {
      document.getElementById('status-upload-ctas').textContent = 'Erro: ' + data.erro;
    } else {
      document.getElementById('status-upload-ctas').textContent = '✅ Adicionado(s)!';
      document.getElementById('input-ctas').value = '';
      await carregarCtas();
    }
  } catch (e) {
    document.getElementById('status-upload-ctas').textContent = 'Erro de conexão. Tenta de novo.';
  }
  document.getElementById('btn-subir-ctas').disabled = false;
}

async function apagarCta(id) {
  await fetch(`/api/biblioteca/${contaAtual}/ctas/` + id, { method: 'DELETE' });
  await carregarCtas();
}

async function carregarMusicas() {
  const resp = await fetch(`/api/biblioteca/${contaAtual}/musicas`);
  const data = await resp.json();
  const itens = data.itens || [];
  const div = document.getElementById('lista-musicas');

  if (itens.length === 0) {
    div.innerHTML = '<p class="ajuda">Nenhuma música na biblioteca dessa conta ainda.</p>';
    return;
  }

  div.innerHTML = '';
  itens.forEach(item => {
    const el = document.createElement('div');
    el.className = 'item-lib';
    el.innerHTML = `
      <div class="nome">${item.nome}</div>
      <div class="dur">${item.duracao}s</div>
      <button onclick="apagarMusica('${item.id}')">✕</button>
    `;
    div.appendChild(el);
  });
}

async function subirMusicas() {
  const arquivos = document.getElementById('input-musicas').files;
  if (arquivos.length === 0) { alert('Escolhe pelo menos 1 música'); return; }

  const formData = new FormData();
  for (const f of arquivos) formData.append('musicas', f);

  document.getElementById('btn-subir-musicas').disabled = true;
  document.getElementById('status-upload-musicas').textContent = 'Enviando...';

  try {
    const resp = await fetch(`/api/biblioteca/${contaAtual}/musicas`, { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.erro) {
      document.getElementById('status-upload-musicas').textContent = 'Erro: ' + data.erro;
    } else {
      document.getElementById('status-upload-musicas').textContent = '✅ Adicionada(s)!';
      document.getElementById('input-musicas').value = '';
      await carregarMusicas();
    }
  } catch (e) {
    document.getElementById('status-upload-musicas').textContent = 'Erro de conexão. Tenta de novo.';
  }
  document.getElementById('btn-subir-musicas').disabled = false;
}

async function apagarMusica(id) {
  await fetch(`/api/biblioteca/${contaAtual}/musicas/` + id, { method: 'DELETE' });
  await carregarMusicas();
}

async function carregarVideos() {
  const resp = await fetch(`/api/biblioteca/${contaAtual}/videos`);
  const data = await resp.json();
  const itens = data.itens || [];
  const div = document.getElementById('lista-videos');
  const resumo = document.getElementById('resumo-videos');

  if (itens.length === 0) {
    div.innerHTML = '<p class="ajuda">Nenhum clipe na biblioteca dessa conta ainda.</p>';
    resumo.textContent = '';
    return;
  }

  const duracaoTotal = itens.reduce((s, i) => s + i.duracao, 0);
  resumo.textContent = `${itens.length} clipe(s) — ${duracaoTotal.toFixed(0)}s de material no total`;

  div.innerHTML = '';
  itens.forEach(item => {
    const el = document.createElement('div');
    el.className = 'item-lib';
    el.innerHTML = `
      <div class="nome">${item.nome}</div>
      <div class="dur">${item.duracao}s</div>
      <button onclick="apagarVideo('${item.id}')">✕</button>
    `;
    div.appendChild(el);
  });
}

async function carregarAudios() {
  const resp = await fetch(`/api/biblioteca/${contaAtual}/audios`);
  const data = await resp.json();
  const itens = data.itens || [];
  const div = document.getElementById('lista-audios');
  const select = document.getElementById('select-audio');

  if (itens.length === 0) {
    div.innerHTML = '<p class="ajuda">Nenhum áudio na biblioteca dessa conta ainda.</p>';
    select.innerHTML = '<option value="">Nenhum áudio na biblioteca ainda</option>';
    return;
  }

  div.innerHTML = '';
  select.innerHTML = '';
  itens.forEach(item => {
    const el = document.createElement('div');
    el.className = 'item-lib';
    el.innerHTML = `
      <div class="nome">${item.nome}</div>
      <div class="dur">${item.duracao}s</div>
      <button onclick="apagarAudio('${item.id}')">✕</button>
    `;
    div.appendChild(el);

    const opt = document.createElement('option');
    opt.value = item.id;
    opt.textContent = `${item.nome} (${item.duracao}s)`;
    select.appendChild(opt);
  });
}

async function subirVideos() {
  const arquivos = document.getElementById('input-videos').files;
  if (arquivos.length === 0) { alert('Escolhe pelo menos 1 vídeo'); return; }

  const formData = new FormData();
  for (const f of arquivos) formData.append('videos', f);

  document.getElementById('btn-subir-videos').disabled = true;
  document.getElementById('status-upload-videos').textContent = 'Enviando...';

  try {
    const resp = await fetch(`/api/biblioteca/${contaAtual}/videos`, { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.erro) {
      document.getElementById('status-upload-videos').textContent = 'Erro: ' + data.erro;
    } else {
      document.getElementById('status-upload-videos').textContent = '✅ Adicionado(s)!';
      document.getElementById('input-videos').value = '';
      await carregarVideos();
    }
  } catch (e) {
    document.getElementById('status-upload-videos').textContent = 'Erro de conexão. Tenta de novo.';
  }
  document.getElementById('btn-subir-videos').disabled = false;
}

async function subirAudios() {
  const arquivos = document.getElementById('input-audios').files;
  if (arquivos.length === 0) { alert('Escolhe pelo menos 1 áudio'); return; }

  const formData = new FormData();
  for (const f of arquivos) formData.append('audios', f);

  document.getElementById('btn-subir-audios').disabled = true;
  document.getElementById('status-upload-audios').textContent = 'Enviando...';

  try {
    const resp = await fetch(`/api/biblioteca/${contaAtual}/audios`, { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.erro) {
      document.getElementById('status-upload-audios').textContent = 'Erro: ' + data.erro;
    } else {
      document.getElementById('status-upload-audios').textContent = '✅ Adicionado(s)!';
      document.getElementById('input-audios').value = '';
      await carregarAudios();
    }
  } catch (e) {
    document.getElementById('status-upload-audios').textContent = 'Erro de conexão. Tenta de novo.';
  }
  document.getElementById('btn-subir-audios').disabled = false;
}

async function apagarVideo(id) {
  await fetch(`/api/biblioteca/${contaAtual}/videos/` + id, { method: 'DELETE' });
  await carregarVideos();
}

async function apagarAudio(id) {
  await fetch(`/api/biblioteca/${contaAtual}/audios/` + id, { method: 'DELETE' });
  await carregarAudios();
}

function alternarLegendaCompilado() {
  const marcado = document.getElementById('usar-legenda-compilado').checked;
  document.getElementById('campos-legenda-compilado').style.display = marcado ? 'block' : 'none';
  if (marcado) atualizarStatusChaveCompilado();
}

function atualizarStatusChaveCompilado() {
  const chave = localStorage.getItem('api_key_openai') || '';
  const div = document.getElementById('status-chave-compilado');
  if (chave) {
    div.innerHTML = '✅ Chave OpenAI configurada — a legenda vai ser transcrita automaticamente';
  } else {
    div.innerHTML = '⚠️ Precisa configurar a chave OpenAI — <a href="/config" style="color:#ff2d55; font-weight:700;">configurar agora</a>';
  }
}

function alternarCorFundoCompilado() {
  const modelo = document.getElementById('modelo-legenda-compilado').value;
  document.getElementById('campo-cor-fundo-compilado').style.display = modelo === 'citacao' ? 'block' : 'none';
}

async function gerarCompilado() {
  const audioId = document.getElementById('select-audio').value;
  const quantidade = document.getElementById('quantidade-compilado').value || 1;
  const usarMusica = document.getElementById('usar-musica-compilado').checked;
  const usarLegenda = document.getElementById('usar-legenda-compilado').checked;
  const legendaModelo = document.getElementById('modelo-legenda-compilado').value;
  const corFundoCitacao = document.getElementById('cor-fundo-citacao-compilado').value;
  const apiKey = localStorage.getItem('api_key_openai') || '';

  if (!audioId) { alert('Escolhe um áudio da biblioteca'); return; }
  if (usarLegenda && !apiKey) { alert('Configura sua chave OpenAI na aba Config primeiro'); return; }

  document.getElementById('btn-gerar-compilado').disabled = true;
  document.getElementById('status-box').style.display = 'block';
  document.getElementById('download-link').style.display = 'none';
  document.getElementById('status-text').textContent = 'Iniciando...';
  document.getElementById('bar-fill').style.width = '5%';

  let resp, data;
  try {
    resp = await fetch('/api/compilado/iniciar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conta_id: contaAtual, audio_id: audioId, quantidade, usar_legenda: usarLegenda, usar_musica: usarMusica,
        legenda_modelo: legendaModelo, cor_fundo_citacao: corFundoCitacao, api_key: apiKey,
      })
    });
    data = await resp.json();
  } catch (e) {
    document.getElementById('status-text').textContent = 'Erro de conexão. Tenta de novo.';
    document.getElementById('btn-gerar-compilado').disabled = false;
    return;
  }

  if (data.erro) {
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-gerar-compilado').disabled = false;
    return;
  }

  jobId = data.job_id;
  localStorage.setItem('compilado_job_ativo', jobId);
  poller = setInterval(checarStatusCompilado, 3000);
}

async function checarStatusCompilado() {
  let resp, data;
  try {
    resp = await fetch('/api/compilado/status/' + jobId);
    data = await resp.json();
  } catch (e) {
    document.getElementById('status-text').textContent = 'Conexão instável... tentando de novo (o processamento continua no servidor).';
    return;
  }

  if (data.status === 'transcrevendo') {
    document.getElementById('status-text').textContent = 'Transcrevendo o áudio pra sincronizar a legenda...';
    document.getElementById('bar-fill').style.width = '15%';
  } else if (data.status === 'gerando') {
    document.getElementById('status-text').textContent = `Montando compilado... (${data.concluidos}/${data.total})`;
    const pct = Math.min(90, 20 + (data.concluidos / Math.max(data.total,1)) * 70);
    document.getElementById('bar-fill').style.width = pct + '%';
  } else if (data.status === 'na_fila') {
    document.getElementById('status-text').textContent = 'Preparando...';
  } else if (data.status === 'concluido') {
    clearInterval(poller);
    localStorage.removeItem('compilado_job_ativo');
    document.getElementById('status-text').textContent = `Pronto! ${data.total} vídeo(s) gerado(s).`;
    document.getElementById('bar-fill').style.width = '100%';
    const link = document.getElementById('download-link');
    link.href = '/api/compilado/baixar/' + jobId;
    link.style.display = 'block';
    document.getElementById('btn-gerar-compilado').disabled = false;
  } else if (data.status === 'erro') {
    clearInterval(poller);
    localStorage.removeItem('compilado_job_ativo');
    document.getElementById('status-text').textContent = 'Erro: ' + data.erro;
    document.getElementById('btn-gerar-compilado').disabled = false;
  } else if (data.erro || !resp.ok) {
    clearInterval(poller);
    localStorage.removeItem('compilado_job_ativo');
    document.getElementById('status-text').textContent = 'Esse processamento anterior não foi encontrado (pode ter se perdido num reinício do servidor). Pode iniciar um novo.';
    document.getElementById('btn-gerar-compilado').disabled = false;
  }
}

async function verRecentesCompilado() {
  const div = document.getElementById('lista-recentes');
  div.style.display = 'block';
  div.innerHTML = '<p class="ajuda">Buscando...</p>';

  const resp = await fetch('/api/compilado/recentes');
  const data = await resp.json();

  if (!data.jobs || data.jobs.length === 0) {
    div.innerHTML = '<p class="ajuda">Nenhum processamento na última hora.</p>';
    return;
  }

  div.innerHTML = '';
  data.jobs.forEach(j => {
    const item = document.createElement('div');
    item.className = 'job-recente';
    let statusTexto = '';
    if (j.status === 'concluido' && j.recuperado_do_disco) statusTexto = '✅ Pronto (recuperado do disco)';
    else if (j.status === 'concluido') statusTexto = `✅ Pronto — ${j.total ?? '?'} vídeo(s)`;
    else if (j.status === 'erro') statusTexto = '❌ Erro';
    else statusTexto = '⏳ Processando';

    item.innerHTML = `
      <div>${statusTexto} — há ${j.minutos_atras} min</div>
      <div style="color:#666; font-size:11px;">ID: ${j.job_id}</div>
      ${j.status === 'concluido' ? `<a href="/api/compilado/baixar/${j.job_id}">⬇ Baixar ZIP</a>` : ''}
    `;
    div.appendChild(item);
  });
}

(function retomarJobAtivo() {
  const jobSalvo = localStorage.getItem('compilado_job_ativo');
  if (!jobSalvo) return;
  jobId = jobSalvo;
  document.getElementById('status-box').style.display = 'block';
  document.getElementById('status-text').textContent = 'Retomando processamento anterior...';
  document.getElementById('btn-gerar-compilado').disabled = true;
  poller = setInterval(checarStatusCompilado, 3000);
  checarStatusCompilado();
})();

(async function iniciarPagina() {
  await carregarContas();
  await carregarBiblioteca();
})();
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


def obter_duracao(path: str) -> float:
    """Duração em segundos de um vídeo ou áudio, via ffprobe."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", path]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    texto = out.stdout.strip()
    return float(texto) if texto else 0.0


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

MAX_IMAGENS_ANALISE_ESTILO = 10  # cap de imagens analisadas por chamada (custo/tamanho da requisição)


def analisar_estilo_visual(api_key: str, imagens_bytes: list) -> str:
    """Manda as imagens de referência do usuário pro GPT-4o (visão) e pede
    uma descrição REUTILIZÁVEL do padrão visual/fotográfico — explicitamente
    sem reproduzir texto, marca ou logotipo específico das imagens originais,
    só o estilo (composição, luz, materiais, enquadramento)."""
    conteudo = [{
        "type": "text",
        "text": (
            "Estas são referências visuais de um usuário para um projeto de conteúdo "
            "próprio. Descreva em inglês, em um parágrafo denso e reutilizável como "
            "prompt de geração de imagem, SOMENTE o padrão visual/fotográfico "
            "recorrente entre elas: composição, ângulo, iluminação, materiais de "
            "fundo (mesa, tecido, varanda etc.), paleta de cores, textura, e o "
            "estilo de eventual ilustração de linha (se houver).\n\n"
            "IMPORTANTE: não mencione, descreva ou tente reproduzir nenhum texto "
            "específico escrito nas imagens, nem nomes de marca, logotipos ou selos "
            "visíveis — ignore completamente esses elementos. A descrição final deve "
            "terminar deixando claro que a cena gerada não deve ter nenhum texto, "
            "letra ou logotipo, só o cenário/composição vazio pronto pra receber "
            "texto por cima depois."
        ),
    }]
    for img in imagens_bytes[:MAX_IMAGENS_ANALISE_ESTILO]:
        b64 = base64.b64encode(img).decode()
        conteudo.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": conteudo}],
            "max_tokens": 500,
        },
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


MAX_IMAGENS_TRANSCRICAO_COPY = 10


def transcrever_copies_de_imagens(imagens_bytes: list) -> list:
    """Lê o texto de cada print via OCR local (Tesseract) — de graça, sem
    chamar nenhuma API paga. Faz uma limpeza básica no texto extraído,
    já que OCR de print de rede social pode pegar ruído (curtidas, ícones)."""
    textos = []
    for img_bytes in imagens_bytes[:MAX_IMAGENS_TRANSCRICAO_COPY]:
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            texto_bruto = pytesseract.image_to_string(img, lang="eng+por")
        except Exception:
            continue

        # Limpeza básica: remove linhas muito curtas/isoladas (comuns em
        # ruído de interface: números de likes, hora, ícones mal lidos)
        linhas = [l.strip() for l in texto_bruto.split("\n")]
        linhas_uteis = [l for l in linhas if len(l) > 3]
        texto_limpo = " ".join(linhas_uteis).strip()

        if texto_limpo:
            textos.append(texto_limpo)

    return textos



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


def chamar_openai_imagem_grade(api_key: str, estilo: str, estilo_customizado: str = "") -> Image.Image:
    """Pede pra OpenAI gerar 1 imagem retrato dividida em grade 2x2 (4 cenas
    diferentes, sem texto), pra depois cortar em 4 imagens 9:16 separadas."""
    if estilo == "personalizado" and estilo_customizado:
        base_prompt = estilo_customizado
    else:
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
                        estilo: str, quantidade: int, gerar_reels: bool,
                        estilo_customizado: str = ""):
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
            grade = chamar_openai_imagem_grade(api_key, estilo, estilo_customizado)
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


def contar_videos_conta(url: str) -> int:
    """Conta quantos vídeos a conta tem no total, sem baixar nada (usa
    extração 'flat', bem mais rápida que abrir vídeo por vídeo). Necessário
    pra numerar do mais antigo pro mais novo, já que o TikTok sempre lista
    os vídeos do mais recente pro mais antigo."""
    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    entradas = info.get("entries", []) if info else []
    return len(list(entradas))


# ---------------------------------------------------------
# Biblioteca: vídeos curtos + áudios guardados, pra montar
# compilados aleatórios com transição, cortados no tamanho do
# áudio, com legenda automática sincronizada.
# ---------------------------------------------------------
BIBLIOTECA_DIR = Path(tempfile.gettempdir()) / "biblioteca"
BIBLIOTECA_DIR.mkdir(parents=True, exist_ok=True)

COMPILADO_BASE_TMP = Path(tempfile.gettempdir()) / "compilado_jobs"
COMPILADO_BASE_TMP.mkdir(exist_ok=True)
COMPILADO_JOBS = {}

MAX_CLIPES_BIBLIOTECA = 100
MAX_AUDIOS_BIBLIOTECA = 20
MAX_MUSICAS_BIBLIOTECA = 20
MAX_HOOKS_BIBLIOTECA = 50
MAX_CTAS_BIBLIOTECA = 50
TRANSICAO_DURACAO = 0.4  # segundos de sobreposição entre um clipe e outro
RESOLUCAO_COMPILADO = (1080, 1920)  # vertical, padrão Reels/TikTok
VOLUME_AUDIO_PRINCIPAL = 1.7  # +70% no áudio principal (voz)
VOLUME_MUSICA_FUNDO = 0.2     # ~20% de volume na música de fundo


def _id_conta_seguro(conta_id: str) -> str:
    return secure_filename((conta_id or "").strip().lower()) or "padrao"


def _pasta_conta(conta_id: str, tipo: str) -> Path:
    """Retorna (criando se preciso) a pasta de vídeos/áudios/músicas de UMA
    conta específica — cada conta tem sua própria biblioteca isolada, pra
    não misturar material entre contas diferentes."""
    conta_segura = _id_conta_seguro(conta_id)
    pasta = BIBLIOTECA_DIR / conta_segura / tipo
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _listar_contas() -> list:
    """Lista todas as contas que já têm alguma biblioteca criada, com a
    contagem de itens de cada uma."""
    if not BIBLIOTECA_DIR.exists():
        return []
    contas = []
    for pasta_conta in sorted(BIBLIOTECA_DIR.iterdir()):
        if not pasta_conta.is_dir():
            continue
        n_videos = len(list((pasta_conta / "videos").glob("*"))) if (pasta_conta / "videos").exists() else 0
        n_audios = len(list((pasta_conta / "audios").glob("*"))) if (pasta_conta / "audios").exists() else 0
        n_musicas = len(list((pasta_conta / "musicas").glob("*"))) if (pasta_conta / "musicas").exists() else 0
        n_hooks = len(list((pasta_conta / "hooks").glob("*"))) if (pasta_conta / "hooks").exists() else 0
        n_ctas = len(list((pasta_conta / "ctas").glob("*"))) if (pasta_conta / "ctas").exists() else 0
        contas.append({
            "id": pasta_conta.name,
            "videos": n_videos,
            "audios": n_audios,
            "musicas": n_musicas,
            "hooks": n_hooks,
            "ctas": n_ctas,
        })
    return contas


def _listar_biblioteca(pasta: Path) -> list:
    """Lista os arquivos guardados numa pasta da biblioteca, com duração."""
    itens = []
    for f in sorted(pasta.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file() and not f.name.endswith(".json"):
            try:
                duracao = obter_duracao(str(f))
            except Exception:
                duracao = 0.0
            itens.append({
                "id": f.stem,
                "nome": f.name,
                "duracao": round(duracao, 1),
                "tamanho_mb": round(f.stat().st_size / (1024 * 1024), 2),
            })
    return itens


def montar_compilado(clipes_disponiveis: list, duracao_alvo: float, pasta_trabalho: Path,
                      transicao: float = TRANSICAO_DURACAO,
                      hooks_disponiveis: list = None, ctas_disponiveis: list = None) -> tuple:
    """Monta a ordem final dos clipes — [hook (se tiver)] + [vídeos do meio,
    sorteados até cobrir a duração] + [cta (se tiver)] — e a cadeia de
    filtros xfade (transição) entre eles. Devolve
    (escolhidos, partes_filtro, label_final, duracao_total_estimada)."""
    if not clipes_disponiveis and not hooks_disponiveis and not ctas_disponiveis:
        raise ValueError("Nenhum vídeo na biblioteca ainda.")

    def duracao_segura(caminho) -> float:
        try:
            d = obter_duracao(str(caminho))
        except Exception:
            return 0.0
        return d if d and d > 0 else 0.0

    escolhidos = []  # ordem final: [hook?] + [meio...] + [cta?], cada item (path, duracao)
    total = 0.0

    def adicionar(caminho, dur):
        nonlocal total
        incremento = dur if not escolhidos else (dur - transicao)
        escolhidos.append((caminho, dur))
        total += incremento

    # 1) Hook sempre primeiro, se a conta tiver algum
    if hooks_disponiveis:
        hook = random.choice(hooks_disponiveis)
        dur_hook = duracao_segura(hook)
        if dur_hook > 0:
            adicionar(hook, dur_hook)

    # 2) Escolhe o CTA agora (mas só adiciona no final) — precisamos saber a
    # duração dele já pra calcular quanto os vídeos do meio ainda precisam cobrir.
    cta_escolhido = None
    dur_cta = 0.0
    if ctas_disponiveis:
        cta_escolhido = random.choice(ctas_disponiveis)
        dur_cta = duracao_segura(cta_escolhido)

    def contribuicao_cta() -> float:
        if not (cta_escolhido and dur_cta > 0):
            return 0.0
        return dur_cta if not escolhidos else (dur_cta - transicao)

    # 3) Preenche o meio com vídeos sorteados (repete se precisar), cuidando
    # pra NUNCA ultrapassar o espaço disponível — senão o corte final (-t)
    # cortaria o CTA fora, já que ele vem sempre por último. Se um clipe não
    # couber inteiro, ele é encurtado (trim) só o suficiente pra fechar a conta.
    pool = list(clipes_disponiveis) if clipes_disponiveis else []
    if pool:
        random.shuffle(pool)
        i = 0
        tentativas = 0
        while tentativas < 200:
            limite = duracao_alvo - contribuicao_cta()
            if total >= limite - 0.05:
                break
            if i >= len(pool):
                random.shuffle(pool)
                i = 0
            caminho = pool[i]
            i += 1
            tentativas += 1
            dur = duracao_segura(caminho)
            if dur <= 0:
                continue
            incremento_cheio = dur if not escolhidos else (dur - transicao)
            if total + incremento_cheio <= limite + 0.05:
                adicionar(caminho, dur)
            else:
                # Não cabe inteiro — encurta só o suficiente pra preencher
                # exatamente o espaço que falta, e para por aqui.
                espaco_restante = limite - total
                duracao_truncada = espaco_restante if not escolhidos else (espaco_restante + transicao)
                duracao_truncada = max(0.6, min(duracao_truncada, dur))
                adicionar(caminho, duracao_truncada)
                break

    # 4) CTA sempre por último, se a conta tiver algum
    if cta_escolhido and dur_cta > 0:
        adicionar(cta_escolhido, dur_cta)

    if not escolhidos:
        raise ValueError("Não consegui medir a duração de nenhum vídeo da biblioteca (hook, meio ou CTA).")

    w, h = RESOLUCAO_COMPILADO
    partes_filtro = []
    for idx, (_caminho, _dur) in enumerate(escolhidos):
        partes_filtro.append(
            f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1,fps=30,format=yuv420p[vs{idx}]"
        )

    label_atual = "vs0"
    acumulado = escolhidos[0][1]
    for idx in range(1, len(escolhidos)):
        dur_clipe = escolhidos[idx][1]
        offset = max(0.0, acumulado - transicao)
        label_saida = f"vx{idx}"
        partes_filtro.append(
            f"[{label_atual}][vs{idx}]xfade=transition=fade:duration={transicao:.2f}:"
            f"offset={offset:.2f}[{label_saida}]"
        )
        label_atual = label_saida
        acumulado = offset + dur_clipe

    return escolhidos, partes_filtro, label_atual, acumulado


def gerar_um_compilado(clipes_disponiveis: list, audio_path: str, duracao_audio: float,
                        segmentos_legenda: list, usar_legenda: bool, legenda_modelo: str,
                        cor_fundo_citacao: str, pasta_trabalho: Path, output_path: str,
                        musica_path: str = None, hooks_disponiveis: list = None,
                        ctas_disponiveis: list = None):
    """Gera 1 vídeo compilado: [hook] + vídeos do meio sorteados (com
    transição) + [cta], corta no tamanho do áudio escolhido, cola o áudio
    (mais alto) + música de fundo opcional (mais baixa), e adiciona legenda
    se pedido."""
    escolhidos, partes_filtro, label_video, _duracao_estimada = montar_compilado(
        clipes_disponiveis, duracao_audio, pasta_trabalho,
        hooks_disponiveis=hooks_disponiveis, ctas_disponiveis=ctas_disponiveis,
    )

    if usar_legenda and segmentos_legenda:
        pedacos, label_video = construir_filtro_legenda(
            pasta_trabalho, legenda_modelo, cor_fundo_citacao,
            label_inicial=label_video, segmentos=segmentos_legenda,
        )
        partes_filtro.append(pedacos)

    cmd = ["ffmpeg", "-y"]
    for caminho, dur_usada in escolhidos:
        # "-t" antes de cada "-i" limita esse clipe específico à duração que
        # a montagem decidiu usar (só é diferente da duração real quando o
        # clipe foi encurtado pra caber certinho antes do CTA).
        cmd += ["-t", f"{dur_usada:.2f}", "-i", str(caminho)]
    cmd += ["-i", audio_path]
    indice_audio = len(escolhidos)

    # Áudio principal (voz) mais alto que o original; limiter no final evita
    # estourar/cortar o som quando o volume é aumentado.
    partes_filtro.append(f"[{indice_audio}:a]volume={VOLUME_AUDIO_PRINCIPAL}[avoz]")
    label_audio = "avoz"

    if musica_path:
        # "-stream_loop -1" repete a música quantas vezes precisar pra cobrir
        # a duração toda, mesmo que ela seja mais curta que o áudio principal.
        cmd += ["-stream_loop", "-1", "-i", musica_path]
        indice_musica = indice_audio + 1
        partes_filtro.append(f"[{indice_musica}:a]volume={VOLUME_MUSICA_FUNDO}[amus]")
        partes_filtro.append(f"[avoz][amus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[amix0]")
        partes_filtro.append("[amix0]alimiter=limit=0.95[aout]")
        label_audio = "aout"
    else:
        partes_filtro.append("[avoz]alimiter=limit=0.95[aout]")
        label_audio = "aout"

    filtro_completo = ";".join(partes_filtro)

    cmd += [
        "-filter_complex", filtro_completo,
        "-map", f"[{label_video}]",
        "-map", f"[{label_audio}]",
        "-t", str(duracao_audio),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]

    resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=280)
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr[-800:])


def compilado_job_worker(job_id: str, conta_id: str, audio_path: str, quantidade: int,
                          usar_legenda: bool, legenda_modelo: str, cor_fundo_citacao: str,
                          api_key: str, usar_musica: bool = False):
    job = COMPILADO_JOBS[job_id]
    pasta_job = COMPILADO_BASE_TMP / job_id
    pasta_job.mkdir(exist_ok=True)

    try:
        pasta_videos_conta = _pasta_conta(conta_id, "videos")
        clipes_disponiveis = [pasta_videos_conta / f["nome"] for f in _listar_biblioteca(pasta_videos_conta)]

        pasta_hooks_conta = _pasta_conta(conta_id, "hooks")
        hooks_disponiveis = [pasta_hooks_conta / f["nome"] for f in _listar_biblioteca(pasta_hooks_conta)]

        pasta_ctas_conta = _pasta_conta(conta_id, "ctas")
        ctas_disponiveis = [pasta_ctas_conta / f["nome"] for f in _listar_biblioteca(pasta_ctas_conta)]

        if not clipes_disponiveis and not hooks_disponiveis and not ctas_disponiveis:
            job["status"] = "erro"
            job["erro"] = "A biblioteca dessa conta está vazia (sem vídeos, hooks ou ctas). Sobe alguns clipes primeiro."
            return

        musicas_disponiveis = []
        if usar_musica:
            pasta_musicas_conta = _pasta_conta(conta_id, "musicas")
            musicas_disponiveis = [pasta_musicas_conta / f["nome"] for f in _listar_biblioteca(pasta_musicas_conta)]

        duracao_audio = obter_duracao(audio_path)
        if duracao_audio <= 0:
            job["status"] = "erro"
            job["erro"] = "Não consegui ler a duração desse áudio."
            return

        segmentos_legenda = None
        if usar_legenda:
            if not api_key:
                job["status"] = "erro"
                job["erro"] = "Configura sua chave OpenAI na aba Config pra usar legenda automática."
                return
            job["status"] = "transcrevendo"
            segmentos_legenda = transcrever_segmentos(api_key, audio_path, pasta_job)

        job["status"] = "gerando"
        job["total"] = quantidade
        job["concluidos"] = 0
        gerados = []

        for i in range(quantidade):
            saida = pasta_job / f"compilado_{i+1:02d}.mp4"
            musica_escolhida = str(random.choice(musicas_disponiveis)) if musicas_disponiveis else None
            gerar_um_compilado(
                clipes_disponiveis, audio_path, duracao_audio,
                segmentos_legenda, usar_legenda, legenda_modelo, cor_fundo_citacao,
                pasta_job, str(saida), musica_path=musica_escolhida,
                hooks_disponiveis=hooks_disponiveis, ctas_disponiveis=ctas_disponiveis,
            )
            gerados.append(saida)
            job["concluidos"] += 1

        zip_path = COMPILADO_BASE_TMP / f"{job_id}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in gerados:
                zf.write(f, arcname=f.name)

        job["status"] = "concluido"
        job["zip_path"] = str(zip_path)
        job["total"] = len(gerados)
        job["criado_em"] = time.time()

    except Exception as e:
        job["status"] = "erro"
        job["erro"] = str(e)
    finally:
        for f in pasta_job.glob("*"):
            if f.suffix != ".zip":
                try:
                    f.unlink()
                except Exception:
                    pass


def job_worker(job_id: str, url_alvo: str, inicio: int, fim: int, ordem: str = "recentes"):
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
        inicio_real, fim_real = inicio, fim
        if ordem == "antigos":
            try:
                total = contar_videos_conta(url_alvo)
                if total > 0:
                    # Vídeo 1 (mais antigo) = posição 'total' na listagem do
                    # TikTok (que vem do mais recente pro mais antigo).
                    inicio_real = max(1, total - fim + 1)
                    fim_real = max(1, total - inicio + 1)
            except Exception:
                pass  # se a contagem falhar, cai pro comportamento padrão (mais recentes)
        ydl_opts["playliststart"] = inicio_real
        ydl_opts["playlistend"] = fim_real

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


def _gerar_icone(size):
    """Desenha o ícone do app na hora (nota musical estilo TikTok, ciano/
    rosa sobre fundo preto) — evita guardar uma string enorme no código,
    que era a causa mais provável do arquivo cortar ao copiar no celular."""
    bg = Image.new("RGBA", (size, size), (10, 10, 10, 255))
    radius = int(size * 0.22)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size, size], radius=radius, fill=255)

    cx, cy = size * 0.42, size * 0.5
    note_h = size * 0.62

    def desenhar_nota(draw_obj, offset_x, offset_y, color):
        ox, oy = cx + offset_x, cy + offset_y
        stem_w = size * 0.10
        draw_obj.rounded_rectangle(
            [ox, oy - note_h / 2, ox + stem_w, oy + note_h / 2 - size * 0.14],
            radius=stem_w / 2, fill=color,
        )
        head_r = size * 0.14
        draw_obj.ellipse(
            [ox - head_r + stem_w / 2, oy + note_h / 2 - head_r * 2,
             ox + head_r + stem_w / 2, oy + note_h / 2],
            fill=color,
        )
        draw_obj.polygon([
            (ox + stem_w, oy - note_h / 2),
            (ox + stem_w + size * 0.16, oy - note_h / 2 + size * 0.10),
            (ox + stem_w, oy - note_h / 2 + size * 0.16),
        ], fill=color)

    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    desenhar_nota(ld, size * 0.05, -size * 0.03, (37, 244, 238, 230))
    desenhar_nota(ld, -size * 0.05, size * 0.03, (255, 45, 85, 230))
    desenhar_nota(ld, 0, 0, (255, 255, 255, 255))

    bg = Image.alpha_composite(bg, layer)
    bg.putalpha(mask)

    buf = io.BytesIO()
    bg.convert("RGBA").save(buf, format="PNG")
    return buf.getvalue()


@app.route("/icon-192.png")
def icon_192():
    return Response(_gerar_icone(192), mimetype="image/png")


@app.route("/icon-512.png")
def icon_512():
    return Response(_gerar_icone(512), mimetype="image/png")


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
    # job_id vem da URL — valida o formato antes de usar em caminho de arquivo
    if not re.fullmatch(r"[a-f0-9]{8,32}", job_id):
        return jsonify({"erro": "id inválido"}), 400

    job = EDITOR_JOBS.get(job_id)
    if job and job["status"] == "concluido":
        return send_file(job["zip_path"], as_attachment=True, download_name=f"editados_{job_id}.zip")

    # Não está mais na memória (ex: processo reiniciou) — tenta achar o
    # zip direto no disco, que sobrevive a reinícios.
    zip_path = EDITOR_BASE_TMP / f"{job_id}.zip"
    if zip_path.exists():
        return send_file(str(zip_path), as_attachment=True, download_name=f"editados_{job_id}.zip")

    return jsonify({"erro": "arquivo ainda não está pronto ou não encontrado"}), 400


@app.route("/api/editor/recentes")
def editor_recentes():
    """Lista os processamentos das últimas horas — serve pra recuperar um
    job cuja tela (ou até a memória do servidor) foi perdida. Combina o que
    está em memória com uma varredura direta dos arquivos .zip no disco,
    porque o disco sobrevive a reinícios do processo, a memória não."""
    agora = time.time()
    recentes = {}

    for jid, job in EDITOR_JOBS.items():
        idade = agora - job.get("criado_em", agora)
        if idade > 3600:
            continue
        recentes[jid] = {
            "job_id": jid,
            "status": job["status"],
            "concluidos": job.get("concluidos", 0),
            "total": job.get("total", 0),
            "minutos_atras": round(idade / 60, 1),
        }

    # Varre o disco por .zip que a memória não conhece mais (ex: processo
    # reiniciou depois que o job terminou, mas antes de você conferir).
    for zip_path in EDITOR_BASE_TMP.glob("*.zip"):
        jid = zip_path.stem
        if jid in recentes:
            continue
        idade = agora - zip_path.stat().st_mtime
        if idade > 3600:
            continue
        recentes[jid] = {
            "job_id": jid,
            "status": "concluido",
            "concluidos": None,
            "total": None,
            "minutos_atras": round(idade / 60, 1),
            "recuperado_do_disco": True,
        }

    lista = sorted(recentes.values(), key=lambda x: x["minutos_atras"])
    return jsonify({"jobs": lista})


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
    estilo_customizado = data.get("estilo_customizado", "").strip()
    gerar_reels = bool(data.get("gerar_reels", False))

    if not api_key:
        return jsonify({"erro": "Informe sua chave da API OpenAI"}), 400
    if not funil:
        return jsonify({"erro": "Descreva o funil/nicho atual"}), 400

    estilos_validos = set(PROMPTS_ESTILO.keys()) | {"personalizado"}
    if estilo not in estilos_validos:
        estilo = "foto_livro"
    if estilo == "personalizado" and not estilo_customizado:
        return jsonify({"erro": "Analisa um estilo personalizado primeiro (ou escolhe outro estilo)"}), 400

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
        args=(job_id, api_key, funil, exemplos, estilo, quantidade, gerar_reels, estilo_customizado),
        daemon=True,
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/gerador/analisar-estilo", methods=["POST"])
def gerador_analisar_estilo():
    api_key = request.form.get("api_key", "").strip()
    imagens_files = request.files.getlist("imagens")

    if not api_key:
        return jsonify({"erro": "Configura sua chave OpenAI na aba Config primeiro"}), 400
    if not imagens_files:
        return jsonify({"erro": "Envie pelo menos 1 imagem de referência"}), 400

    try:
        imagens_bytes = [f.read() for f in imagens_files[:MAX_IMAGENS_ANALISE_ESTILO]]
        descricao = analisar_estilo_visual(api_key, imagens_bytes)
        return jsonify({"descricao_estilo": descricao, "imagens_analisadas": len(imagens_bytes)})
    except requests.exceptions.HTTPError as e:
        detalhe = ""
        try:
            detalhe = e.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        return jsonify({"erro": f"Erro na API da OpenAI: {detalhe or str(e)}"}), 400
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/api/gerador/transcrever-copies", methods=["POST"])
def gerador_transcrever_copies():
    imagens_files = request.files.getlist("imagens")

    if not imagens_files:
        return jsonify({"erro": "Envie pelo menos 1 print"}), 400

    try:
        imagens_bytes = [f.read() for f in imagens_files[:MAX_IMAGENS_TRANSCRICAO_COPY]]
        textos = transcrever_copies_de_imagens(imagens_bytes)
        if not textos:
            return jsonify({"erro": "Não consegui ler texto legível nos prints enviados"}), 400
        return jsonify({"textos": textos})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/api/gerador/status/<job_id>")
def gerador_status(job_id):
    job = GERADOR_JOBS.get(job_id)
    if not job:
        # Não está mais na memória — mas se o zip existe no disco, o
        # trabalho terminou antes do processo reiniciar; informa concluído.
        if re.fullmatch(r"[a-f0-9]{8,32}", job_id) and (GERADOR_BASE_TMP / f"{job_id}.zip").exists():
            return jsonify({"status": "concluido", "concluidos": None, "concluidos_reels": None, "total": None})
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
    if not re.fullmatch(r"[a-f0-9]{8,32}", job_id):
        return jsonify({"erro": "id inválido"}), 400

    job = GERADOR_JOBS.get(job_id)
    if job and job["status"] == "concluido":
        return send_file(job["zip_path"], as_attachment=True, download_name=f"gerado_{job_id}.zip")

    zip_path = GERADOR_BASE_TMP / f"{job_id}.zip"
    if zip_path.exists():
        return send_file(str(zip_path), as_attachment=True, download_name=f"gerado_{job_id}.zip")

    return jsonify({"erro": "arquivo ainda não está pronto ou não encontrado"}), 400


@app.route("/api/gerador/recentes")
def gerador_recentes():
    """Lista processamentos das últimas horas, combinando memória + disco
    (o disco sobrevive a reinícios do processo, a memória não)."""
    agora = time.time()
    recentes = {}

    for jid, job in GERADOR_JOBS.items():
        idade = agora - job.get("criado_em", agora)
        if idade > 3600:
            continue
        recentes[jid] = {
            "job_id": jid,
            "status": job["status"],
            "total": job.get("total", 0),
            "minutos_atras": round(idade / 60, 1),
        }

    for zip_path in GERADOR_BASE_TMP.glob("*.zip"):
        jid = zip_path.stem
        if jid in recentes:
            continue
        idade = agora - zip_path.stat().st_mtime
        if idade > 3600:
            continue
        recentes[jid] = {
            "job_id": jid,
            "status": "concluido",
            "total": None,
            "minutos_atras": round(idade / 60, 1),
            "recuperado_do_disco": True,
        }

    lista = sorted(recentes.values(), key=lambda x: x["minutos_atras"])
    return jsonify({"jobs": lista})


@app.route("/biblioteca")
def biblioteca_page():
    return PAGINA_BIBLIOTECA_HTML


@app.route("/api/biblioteca/contas", methods=["GET", "POST"])
def biblioteca_contas():
    if request.method == "GET":
        return jsonify({"contas": _listar_contas()})

    data = request.get_json(force=True)
    nome = data.get("nome", "").strip()
    if not nome:
        return jsonify({"erro": "Digite um nome pra conta"}), 400

    conta_id = _id_conta_seguro(nome)
    for tipo in ("videos", "audios", "musicas", "hooks", "ctas"):
        _pasta_conta(conta_id, tipo)

    return jsonify({"contas": _listar_contas(), "conta_criada": conta_id})


@app.route("/api/biblioteca/contas/<conta_id>", methods=["DELETE"])
def biblioteca_contas_apagar(conta_id):
    conta_segura = _id_conta_seguro(conta_id)
    pasta = BIBLIOTECA_DIR / conta_segura
    if pasta.exists():
        shutil.rmtree(pasta, ignore_errors=True)
    return jsonify({"contas": _listar_contas()})


@app.route("/api/biblioteca/<conta_id>/videos", methods=["GET", "POST"])
def biblioteca_videos(conta_id):
    pasta = _pasta_conta(conta_id, "videos")
    if request.method == "GET":
        return jsonify({"itens": _listar_biblioteca(pasta)})

    arquivos = request.files.getlist("videos")
    if not arquivos:
        return jsonify({"erro": "Envie pelo menos 1 vídeo"}), 400

    existentes = list(pasta.glob("*"))
    if len(existentes) + len(arquivos) > MAX_CLIPES_BIBLIOTECA:
        return jsonify({"erro": f"Limite de {MAX_CLIPES_BIBLIOTECA} clipes na biblioteca"}), 400

    for f in arquivos:
        nome_seguro = secure_filename(f.filename or "clipe.mp4")
        destino = pasta / f"{uuid.uuid4().hex[:10]}_{nome_seguro}"
        f.save(str(destino))

    return jsonify({"itens": _listar_biblioteca(pasta)})


@app.route("/api/biblioteca/<conta_id>/videos/<item_id>", methods=["DELETE"])
def biblioteca_videos_apagar(conta_id, item_id):
    if not re.fullmatch(r"[a-zA-Z0-9_.\-]+", item_id):
        return jsonify({"erro": "id inválido"}), 400
    pasta = _pasta_conta(conta_id, "videos")
    for f in pasta.glob(f"{item_id}*"):
        f.unlink()
    return jsonify({"itens": _listar_biblioteca(pasta)})


@app.route("/api/biblioteca/<conta_id>/hooks", methods=["GET", "POST"])
def biblioteca_hooks(conta_id):
    pasta = _pasta_conta(conta_id, "hooks")
    if request.method == "GET":
        return jsonify({"itens": _listar_biblioteca(pasta)})

    arquivos = request.files.getlist("hooks")
    if not arquivos:
        return jsonify({"erro": "Envie pelo menos 1 vídeo de abertura (hook)"}), 400

    existentes = list(pasta.glob("*"))
    if len(existentes) + len(arquivos) > MAX_HOOKS_BIBLIOTECA:
        return jsonify({"erro": f"Limite de {MAX_HOOKS_BIBLIOTECA} hooks na biblioteca"}), 400

    for f in arquivos:
        nome_seguro = secure_filename(f.filename or "hook.mp4")
        destino = pasta / f"{uuid.uuid4().hex[:10]}_{nome_seguro}"
        f.save(str(destino))

    return jsonify({"itens": _listar_biblioteca(pasta)})


@app.route("/api/biblioteca/<conta_id>/hooks/<item_id>", methods=["DELETE"])
def biblioteca_hooks_apagar(conta_id, item_id):
    if not re.fullmatch(r"[a-zA-Z0-9_.\-]+", item_id):
        return jsonify({"erro": "id inválido"}), 400
    pasta = _pasta_conta(conta_id, "hooks")
    for f in pasta.glob(f"{item_id}*"):
        f.unlink()
    return jsonify({"itens": _listar_biblioteca(pasta)})


@app.route("/api/biblioteca/<conta_id>/ctas", methods=["GET", "POST"])
def biblioteca_ctas(conta_id):
    pasta = _pasta_conta(conta_id, "ctas")
    if request.method == "GET":
        return jsonify({"itens": _listar_biblioteca(pasta)})

    arquivos = request.files.getlist("ctas")
    if not arquivos:
        return jsonify({"erro": "Envie pelo menos 1 vídeo de encerramento (cta)"}), 400

    existentes = list(pasta.glob("*"))
    if len(existentes) + len(arquivos) > MAX_CTAS_BIBLIOTECA:
        return jsonify({"erro": f"Limite de {MAX_CTAS_BIBLIOTECA} ctas na biblioteca"}), 400

    for f in arquivos:
        nome_seguro = secure_filename(f.filename or "cta.mp4")
        destino = pasta / f"{uuid.uuid4().hex[:10]}_{nome_seguro}"
        f.save(str(destino))

    return jsonify({"itens": _listar_biblioteca(pasta)})


@app.route("/api/biblioteca/<conta_id>/ctas/<item_id>", methods=["DELETE"])
def biblioteca_ctas_apagar(conta_id, item_id):
    if not re.fullmatch(r"[a-zA-Z0-9_.\-]+", item_id):
        return jsonify({"erro": "id inválido"}), 400
    pasta = _pasta_conta(conta_id, "ctas")
    for f in pasta.glob(f"{item_id}*"):
        f.unlink()
    return jsonify({"itens": _listar_biblioteca(pasta)})


@app.route("/api/biblioteca/<conta_id>/audios", methods=["GET", "POST"])
def biblioteca_audios(conta_id):
    pasta = _pasta_conta(conta_id, "audios")
    if request.method == "GET":
        return jsonify({"itens": _listar_biblioteca(pasta)})

    arquivos = request.files.getlist("audios")
    if not arquivos:
        return jsonify({"erro": "Envie pelo menos 1 áudio"}), 400

    existentes = list(pasta.glob("*"))
    if len(existentes) + len(arquivos) > MAX_AUDIOS_BIBLIOTECA:
        return jsonify({"erro": f"Limite de {MAX_AUDIOS_BIBLIOTECA} áudios na biblioteca"}), 400

    for f in arquivos:
        nome_seguro = secure_filename(f.filename or "audio.mp3")
        destino = pasta / f"{uuid.uuid4().hex[:10]}_{nome_seguro}"
        f.save(str(destino))

    return jsonify({"itens": _listar_biblioteca(pasta)})


@app.route("/api/biblioteca/<conta_id>/audios/<item_id>", methods=["DELETE"])
def biblioteca_audios_apagar(conta_id, item_id):
    if not re.fullmatch(r"[a-zA-Z0-9_.\-]+", item_id):
        return jsonify({"erro": "id inválido"}), 400
    pasta = _pasta_conta(conta_id, "audios")
    for f in pasta.glob(f"{item_id}*"):
        f.unlink()
    return jsonify({"itens": _listar_biblioteca(pasta)})


@app.route("/api/biblioteca/<conta_id>/musicas", methods=["GET", "POST"])
def biblioteca_musicas(conta_id):
    pasta = _pasta_conta(conta_id, "musicas")
    if request.method == "GET":
        return jsonify({"itens": _listar_biblioteca(pasta)})

    arquivos = request.files.getlist("musicas")
    if not arquivos:
        return jsonify({"erro": "Envie pelo menos 1 música"}), 400

    existentes = list(pasta.glob("*"))
    if len(existentes) + len(arquivos) > MAX_MUSICAS_BIBLIOTECA:
        return jsonify({"erro": f"Limite de {MAX_MUSICAS_BIBLIOTECA} músicas na biblioteca"}), 400

    for f in arquivos:
        nome_seguro = secure_filename(f.filename or "musica.mp3")
        destino = pasta / f"{uuid.uuid4().hex[:10]}_{nome_seguro}"
        f.save(str(destino))

    return jsonify({"itens": _listar_biblioteca(pasta)})


@app.route("/api/biblioteca/<conta_id>/musicas/<item_id>", methods=["DELETE"])
def biblioteca_musicas_apagar(conta_id, item_id):
    if not re.fullmatch(r"[a-zA-Z0-9_.\-]+", item_id):
        return jsonify({"erro": "id inválido"}), 400
    pasta = _pasta_conta(conta_id, "musicas")
    for f in pasta.glob(f"{item_id}*"):
        f.unlink()
    return jsonify({"itens": _listar_biblioteca(pasta)})


@app.route("/api/compilado/iniciar", methods=["POST"])
def compilado_iniciar():
    data = request.get_json(force=True)
    conta_id = data.get("conta_id", "").strip()
    audio_id = data.get("audio_id", "").strip()
    api_key = data.get("api_key", "").strip()
    usar_legenda = bool(data.get("usar_legenda", False))
    usar_musica = bool(data.get("usar_musica", False))
    legenda_modelo = data.get("legenda_modelo", "classico").strip()
    cor_fundo_citacao = data.get("cor_fundo_citacao", "branco").strip()

    if not conta_id:
        return jsonify({"erro": "Escolhe uma conta primeiro"}), 400
    if not audio_id:
        return jsonify({"erro": "Escolhe um áudio da biblioteca"}), 400
    if not re.fullmatch(r"[a-zA-Z0-9_.\-]+", audio_id):
        return jsonify({"erro": "id inválido"}), 400

    pasta_audios = _pasta_conta(conta_id, "audios")
    encontrados = list(pasta_audios.glob(f"{audio_id}*"))
    if not encontrados:
        return jsonify({"erro": "Áudio não encontrado na biblioteca dessa conta"}), 404
    audio_path = str(encontrados[0])

    try:
        quantidade = int(data.get("quantidade", 1))
    except (TypeError, ValueError):
        quantidade = 1
    quantidade = max(1, min(quantidade, 20))

    modelos_validos = set(MODELOS_LEGENDA.keys()) | {"citacao"}
    if legenda_modelo not in modelos_validos:
        legenda_modelo = "classico"
    if cor_fundo_citacao not in CORES_FAIXA_CITACAO:
        cor_fundo_citacao = "branco"

    job_id = uuid.uuid4().hex[:12]
    COMPILADO_JOBS[job_id] = {
        "status": "na_fila",
        "concluidos": 0,
        "total": quantidade,
        "criado_em": time.time(),
    }

    t = threading.Thread(
        target=compilado_job_worker,
        args=(job_id, conta_id, audio_path, quantidade, usar_legenda, legenda_modelo,
              cor_fundo_citacao, api_key, usar_musica),
        daemon=True,
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/compilado/status/<job_id>")
def compilado_status(job_id):
    job = COMPILADO_JOBS.get(job_id)
    if not job:
        return jsonify({"erro": "job não encontrado"}), 404
    resposta = {
        "status": job["status"],
        "concluidos": job.get("concluidos", 0),
        "total": job.get("total", 0),
    }
    if job["status"] == "erro":
        resposta["erro"] = job.get("erro")
    return jsonify(resposta)


@app.route("/api/compilado/baixar/<job_id>")
def compilado_baixar(job_id):
    if not re.fullmatch(r"[a-f0-9]{8,32}", job_id):
        return jsonify({"erro": "id inválido"}), 400

    job = COMPILADO_JOBS.get(job_id)
    if job and job["status"] == "concluido":
        return send_file(job["zip_path"], as_attachment=True, download_name=f"compilados_{job_id}.zip")

    zip_path = COMPILADO_BASE_TMP / f"{job_id}.zip"
    if zip_path.exists():
        return send_file(str(zip_path), as_attachment=True, download_name=f"compilados_{job_id}.zip")

    return jsonify({"erro": "arquivo ainda não está pronto ou não encontrado"}), 400


@app.route("/api/compilado/recentes")
def compilado_recentes():
    agora = time.time()
    recentes = {}
    for jid, job in COMPILADO_JOBS.items():
        idade = agora - job.get("criado_em", agora)
        if idade > 3600:
            continue
        recentes[jid] = {
            "job_id": jid, "status": job["status"],
            "concluidos": job.get("concluidos", 0), "total": job.get("total", 0),
            "minutos_atras": round(idade / 60, 1),
        }
    for zip_path in COMPILADO_BASE_TMP.glob("*.zip"):
        jid = zip_path.stem
        if jid in recentes:
            continue
        idade = agora - zip_path.stat().st_mtime
        if idade > 3600:
            continue
        recentes[jid] = {
            "job_id": jid, "status": "concluido", "concluidos": None, "total": None,
            "minutos_atras": round(idade / 60, 1), "recuperado_do_disco": True,
        }
    lista = sorted(recentes.values(), key=lambda x: x["minutos_atras"])
    return jsonify({"jobs": lista})


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

    ordem = data.get("ordem", "recentes").strip()
    if ordem not in ("recentes", "antigos"):
        ordem = "recentes"

    url_alvo = normalizar_url(conta)
    job_id = uuid.uuid4().hex[:12]

    JOBS[job_id] = {
        "status": "na_fila",
        "concluidos": 0,
        "arquivo_atual": "",
        "criado_em": time.time(),
        "video_unico": eh_video_unico(url_alvo),
    }

    t = threading.Thread(target=job_worker, args=(job_id, url_alvo, inicio, fim, ordem), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "video_unico": JOBS[job_id]["video_unico"]})


@app.route("/api/contar-videos", methods=["POST"])
def contar_videos_rota():
    """Conta o total de vídeos de uma conta — usado pra numerar do vídeo
    mais antigo pro mais novo, e pra sugerir o próximo intervalo com base
    no histórico salvo no navegador."""
    data = request.get_json(force=True)
    conta = data.get("conta", "").strip()
    if not conta:
        return jsonify({"erro": "Informe o @ ou link da conta"}), 400

    url_alvo = normalizar_url(conta)
    if eh_video_unico(url_alvo):
        return jsonify({"erro": "Isso é um link de vídeo único, não uma conta"}), 400

    try:
        total = contar_videos_conta(url_alvo)
        return jsonify({"total": total})
    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/api/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        if re.fullmatch(r"[a-f0-9]{8,32}", job_id) and (BASE_TMP / f"{job_id}.zip").exists():
            return jsonify({"status": "concluido", "concluidos": None, "arquivo_atual": ""})
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
    if not re.fullmatch(r"[a-f0-9]{8,32}", job_id):
        return jsonify({"erro": "id inválido"}), 400

    job = JOBS.get(job_id)
    if job and job["status"] == "concluido":
        return send_file(job["zip_path"], as_attachment=True, download_name=f"tiktok_{job_id}.zip")

    zip_path = BASE_TMP / f"{job_id}.zip"
    if zip_path.exists():
        return send_file(str(zip_path), as_attachment=True, download_name=f"tiktok_{job_id}.zip")

    return jsonify({"erro": "arquivo ainda não está pronto ou não encontrado"}), 400


@app.route("/api/recentes")
def baixador_recentes():
    """Lista processamentos das últimas horas, combinando memória + disco."""
    agora = time.time()
    recentes = {}

    for jid, job in JOBS.items():
        idade = agora - job.get("criado_em", agora)
        if idade > 3600:
            continue
        recentes[jid] = {
            "job_id": jid,
            "status": job["status"],
            "total": job.get("total_videos", 0),
            "minutos_atras": round(idade / 60, 1),
        }

    for zip_path in BASE_TMP.glob("*.zip"):
        jid = zip_path.stem
        if jid in recentes:
            continue
        idade = agora - zip_path.stat().st_mtime
        if idade > 3600:
            continue
        recentes[jid] = {
            "job_id": jid,
            "status": "concluido",
            "total": None,
            "minutos_atras": round(idade / 60, 1),
            "recuperado_do_disco": True,
        }

    lista = sorted(recentes.values(), key=lambda x: x["minutos_atras"])
    return jsonify({"jobs": lista})


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

