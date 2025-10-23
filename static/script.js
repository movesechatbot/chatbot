// ======= CONFIG =======
const isLocal = ['localhost', '127.0.0.1'].includes(location.hostname);
const API_BASE = isLocal
  ? 'http://localhost:10000'                // dev: app.py rodando local
  : 'https://chatbot-pfee.onrender.com' // prod: Render
const ENDPOINT = `${API_BASE}/chat`;
const UPLOAD_ENDPOINT = `${API_BASE}/upload-test`;
const TIMEOUT_MS = 12000;
const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024; // 10 MB
const DOC_EXTS = new Set(['pdf', 'docx']);

// ======= UI =======
const mensagensEl = document.getElementById('mensagens');
const input = document.getElementById('pergunta');
const btn = document.getElementById('btnEnviar');
const btnResetUid = document.getElementById('btnResetUid');
const attachmentsInput = document.getElementById('anexos');
const btnEnviarAnexo = document.getElementById('btnEnviarAnexo');


function adicionarMensagem(texto, classe, meta) {
  const wrap = document.createElement('div');
  wrap.className = `mensagem ${classe}`;
  const msg = document.createElement('div');
  msg.textContent = texto;
  wrap.appendChild(msg);

  if (meta) {
    const m = document.createElement('div');
    m.className = 'meta';
    const b = document.createElement('span');
    b.className = `badge ${meta.source || ''}`;
    b.textContent = meta.source || 'desconhecido';
    m.appendChild(b);

    if (typeof meta.similaridade === 'number') {
      const s = document.createElement('span');
      s.textContent = `sim: ${meta.similaridade.toFixed(3)}`;
      m.appendChild(s);

      const bar = document.createElement('div'); bar.className = 'bar';
      const fill = document.createElement('span'); fill.style.width = Math.max(0, Math.min(1, meta.similaridade)) * 100 + '%';
      bar.appendChild(fill); m.appendChild(bar);
    }
    wrap.appendChild(m);
  }

  mensagensEl.appendChild(wrap);
  mensagensEl.scrollTop = mensagensEl.scrollHeight;
  return wrap;
}

function setLoading(loading) {
  btn.disabled = loading;
  input.disabled = loading;
  if (btnEnviarAnexo) btnEnviarAnexo.disabled = loading;
  if (attachmentsInput) attachmentsInput.disabled = loading;
}

// ======= Perguntas e respostas ======

async function enviarPergunta() {
  const pergunta = input.value.trim();
  if (!pergunta) return;

  adicionarMensagem(pergunta, 'user');
  input.value = '';

  const thinking = adicionarMensagem('ia está pensando...', 'bot thinking');
  setLoading(true);

  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), TIMEOUT_MS);

  // Tratamento de exceções e erros

  try {
    const resp = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pergunta, user_id: localStorage.uid || (localStorage.uid = crypto.randomUUID()) }),
      signal: ac.signal
    });
    clearTimeout(t);

    const ok = resp.ok;
    let json = {};
    try { json = await resp.json(); } catch { }

    thinking.remove();
    if (!resp.ok || !json) {
      adicionarMensagem(`erro: ${resp.status || 0}`, 'bot');
      console.warn('[front] resp:', resp, 'json:', json);
      return;
    }

    adicionarMensagem(json.resposta || 'sem resposta.', 'bot', {
      source: json.source || 'local',
      similaridade: typeof json.similaridade === 'number' ? json.similaridade : undefined
    });

    // NOVO: mostrar etapa atual
    if (json.etapa) {
      adicionarMensagem(`(Etapa atual: ${json.etapa})`, 'bot');
    }

  }
  catch (err) {
    clearTimeout(t);
    thinking.remove();
    const msg = err.name === 'AbortError' ? 'timeout: servidor demorou a responder.' : 'erro ao contatar a api.';
    adicionarMensagem(msg, 'bot');
    console.error('[front] erro:', err);
  }
  finally {
    setLoading(false);
    input.focus();
  }
}

btn.addEventListener('click', enviarPergunta);

if (btnResetUid) {
  btnResetUid.addEventListener('click', () => {
    if (confirm('Apagar UID atual e iniciar nova sessão?')) {
      localStorage.removeItem('uid');
      adicionarMensagem(
        'UID apagado. Nova sessão iniciada automaticamente.',
        'bot'
      );
      console.log(
        '[DEBUG] UID apagado. Novo ID será criado no próximo envio.'
      );
    }
  });
}

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); enviarPergunta(); }
});

// ======= Upload real de anexos / Resend ======

function formatarTamanho(bytes) {
  if (!Number.isFinite(bytes)) return `${bytes} B`;
  const units = ['B', 'KB', 'MB', 'GB'];
  let idx = 0;
  let val = bytes;
  while (val >= 1024 && idx < units.length - 1) {
    val /= 1024;
    idx += 1;
  }
  return `${val.toFixed(val >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}

async function enviarAnexos() {
  if (!attachmentsInput) return;
  const files = Array.from(attachmentsInput.files || []);
  if (!files.length) {
    attachmentsInput.focus();
    return;
  }

  const rejeitados = [];
  const grandesDemais = [];
  const aceitos = [];

  files.forEach((file) => {
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    const isImage = file.type.startsWith('image/');
    const isDoc = DOC_EXTS.has(ext)
      || file.type === 'application/pdf'
      || file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

    if (file.size > MAX_ATTACHMENT_BYTES) {
      grandesDemais.push(file);
      return;
    }

    if (!(isImage || isDoc)) {
      rejeitados.push(file);
      return;
    }

    aceitos.push(file);
  });

  if (!aceitos.length) {
    if (grandesDemais.length) {
      adicionarMensagem(
        `Nenhum arquivo enviado: ${grandesDemais.length} excede ${formatarTamanho(MAX_ATTACHMENT_BYTES)}.`,
        'bot',
      );
    }
    if (rejeitados.length) {
      const nomes = rejeitados.map((f) => f.name).join(', ');
      adicionarMensagem(
        `Formatos nao suportados: ${nomes}. Aceitamos imagens, PDF ou DOCX.`,
        'bot',
      );
    }
    attachmentsInput.value = '';
    return;
  }

  aceitos.forEach((file) => {
    adicionarMensagem(`Enviei "${file.name}" (${formatarTamanho(file.size)})`, 'user');
  });

  if (grandesDemais.length || rejeitados.length) {
    const partes = [];
    if (grandesDemais.length) {
      partes.push(`${grandesDemais.length} ignorado(s) por tamanho > ${formatarTamanho(MAX_ATTACHMENT_BYTES)}`);
    }
    if (rejeitados.length) {
      partes.push(`${rejeitados.length} em formato nao suportado`);
    }
    adicionarMensagem(
      `Atencao: ${partes.join('; ')}.`,
      'bot',
      { source: 'resend' },
    );
  }

  setLoading(true);
  const thinking = adicionarMensagem('enviando anexos...', 'bot thinking');

  try {
    const formData = new FormData();
    const uid = localStorage.uid || (localStorage.uid = crypto.randomUUID());
    formData.append('user_id', uid);
    aceitos.forEach((file) => formData.append('files', file, file.name));

    const resp = await fetch(UPLOAD_ENDPOINT, {
      method: 'POST',
      body: formData,
    });

    let json = {};
    try { json = await resp.json(); } catch { }

    thinking.remove();

    if (!resp.ok) {
      adicionarMensagem(
        `Erro ao enviar anexos: ${json.erro || resp.statusText || resp.status}`,
        'bot',
      );
      console.error('[front] upload erro:', resp, json);
      return;
    }

    const results = (json.results || []).map((r) => {
      const status = r.status || 'desconhecido';
      const detail = r.detalhe ? ` - ${r.detalhe}` : '';
      return `- ${r.arquivo || 'arquivo'}: ${status}${detail}`;
    }).join('\n');

    adicionarMensagem(
      `Upload concluido (Resend):\n${results || '(sem detalhes retornados)'}`,
      'bot',
      { source: 'resend' },
    );
  } catch (err) {
    console.error('[front] upload anexos erro', err);
    thinking.remove();
    adicionarMensagem(`Erro ao enviar anexos: ${err.message || err}`, 'bot');
    return;
  } finally {
    setLoading(false);
    attachmentsInput.value = '';
  }
}

if (btnEnviarAnexo) {
  btnEnviarAnexo.addEventListener('click', enviarAnexos);
}
