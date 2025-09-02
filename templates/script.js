 // ======= CONFIG =======
  const isLocal = ['localhost','127.0.0.1'].includes(location.hostname);
  const API_BASE = isLocal
    ? 'http://localhost:10000'                // dev: app.py rodando local
    : 'https://chatbotmovese-v2.onrender.com' // prod: Render
  const ENDPOINT = `${API_BASE}/chat`;
  const TIMEOUT_MS = 12000;

  // ======= UI =======
  const mensagensEl = document.getElementById('mensagens');
  const input = document.getElementById('pergunta');
  const btn = document.getElementById('btnEnviar');

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
        const fill = document.createElement('span'); fill.style.width = Math.max(0, Math.min(1, meta.similaridade))*100 + '%';
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
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ pergunta, user_id: localStorage.uid || (localStorage.uid = crypto.randomUUID()) }),
        signal: ac.signal
      });
      clearTimeout(t);

      const ok = resp.ok;
      let json = {};
      try { json = await resp.json(); } catch {}

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
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); enviarPergunta(); }
  });