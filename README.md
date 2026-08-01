# Baixador de TikTok — Deploy no Render (grátis)

## O que é
App web com uma telinha simples: você cola o `@usuario` ou link do perfil do
TikTok, e ele baixa os vídeos mais recentes (sem marca d'água) e te dá um
ZIP pra baixar direto no celular.

## Passo a passo pra colocar no ar (~10 min, sem custo)

### 1. Criar conta no GitHub (se não tiver)
Acesse https://github.com e crie uma conta grátis.

### 2. Subir esses arquivos pro GitHub
- No GitHub, clique em **New repository** (nome sugerido: `tiktok-downloader`)
- Marque como **Public** ou **Private**, tanto faz
- Depois de criado, clique em **uploading an existing file** e arraste
  todos os arquivos desta pasta (`app.py`, `requirements.txt`, `Dockerfile`,
  `README.md` e a pasta `templates/` com o `index.html` dentro)
- Clique em **Commit changes**

### 3. Criar conta no Render
Acesse https://render.com e crie uma conta grátis (dá pra usar login do GitHub).

### 4. Criar o serviço
- No painel do Render, clique em **New +** → **Web Service**
- Conecte sua conta do GitHub e selecione o repositório que você criou
- O Render vai detectar o `Dockerfile` automaticamente
- Em **Instance Type**, escolha **Free**
- Clique em **Create Web Service**

### 5. Esperar o build
Leva de 3 a 6 minutos na primeira vez (ele baixa o Python, instala o
ffmpeg e o yt-dlp). Você vai ver os logs subindo na tela.

### 6. Pronto
Quando terminar, o Render te dá uma URL tipo:
`https://tiktok-downloader-xxxx.onrender.com`

Abre essa URL no navegador do celular, adiciona à tela inicial (fica
igual um app), e já pode usar.

## Limitações do plano gratuito (importante saber)
- O servidor **hiberna depois de ~15 min sem uso**. Quando você abrir de
  novo, a primeira requisição demora ~30-50 segundos pra "acordar" — normal.
- Agora dá pra escolher a quantidade na tela (padrão 30, teto de 200 por
  vez), pra não estourar o tempo de processamento do plano grátis. Quantidades
  grandes (100+) demoram mais e têm mais chance de timeout no plano free —
  se acontecer, baixe em lotes menores.
- Também dá pra colar o link de **um vídeo específico** (não só a conta
  inteira) — o app detecta automaticamente e baixa só aquele.
- Perfis **privados** não funcionam (precisaria de login, o que este
  projeto não implementa).
- Se o TikTok mudar a estrutura interna deles, o yt-dlp pode parar de
  funcionar até ser atualizado — nesse caso, no Render, vá em **Manual
  Deploy → Clear build cache & deploy** depois de atualizar a versão do
  `yt-dlp` no `requirements.txt`.

## Testar localmente antes de subir (opcional)
Se quiser testar no seu computador antes:
```bash
pip install -r requirements.txt
python app.py
```
Abre `http://localhost:5000` no navegador.
