# whatsapp.py
import tempfile, os, mimetypes, hmac, hashlib, requests
from typing import Optional, Any
from flask import Blueprint, request, abort
from openai import OpenAI
from config import WHATSAPP_TOKEN, PHONE_NUMBER_ID, VERIFY_TOKEN, PORT

bp = Blueprint("whatsapp", __name__)

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def _verify_signature(raw: bytes) -> bool:
#     if not APP_SECRET:
#         return True  # se não quiser validar assinatura agora
#     sig = request.headers.get("X-Hub-Signature-256", "")
#     if not sig.startswith("sha256="): 
#         return False
#     digest = hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
#     return hmac.compare_digest(sig, f"sha256={digest}")

@bp.get("/whatsapp")
def verify():
    # validação do webhook no painel da Meta
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge", ""), 200
    return "forbidden", 403

@bp.post("/whatsapp")
def incoming():
    raw = request.get_data()
    # if not _verify_signature(raw):
    #     return "invalid signature", 403

    data = request.get_json() or {}
    entries = data.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages") or []
            for msg in messages:
                user = msg.get("from")
                t = msg.get("type")
                if not user or not t:
                    continue

                if t == "text":
                    txt = msg["text"]["body"].strip()

                    # --- reset session --- (remover na PROD)
                    if txt.lower() == "/reset":
                        try:
                            requests.post(
                                f"http://localhost:{PORT}/reset",
                                json={"user_id": user},
                                timeout=5
                            )
                            _send_text(user, "sessão zerada.")
                        except Exception as e:
                            _send_text(user, f"erro ao resetar: {e}")
                        continue  # pula o resto e vai pro próximo msg
                    # --- fluxo normal ---
                    reply = _pipeline(txt, user)
                    _send_text(user, reply)

                elif t in ("audio", "voice"):
                    media_id = msg[t]["id"]
                    txt = _transcribe_media(media_id)   # mp3/m4a/ogg/opus/wav ok
                    reply = _pipeline(txt, user)
                    _send_text(user, reply)

                # opcional: imagens, documentos, etc.

    return "ok", 200

def _transcribe_media(media_id: str) -> str:
    # 1) pega URL do arquivo
    meta = requests.get(
        f"https://graph.facebook.com/v20.0/{media_id}",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, timeout=15
    ).json()
    url = meta["url"]

    # 2) baixa o binário com token
    r = requests.get(url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, stream=True, timeout=30)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "audio/mpeg")
    ext = mimetypes.guess_extension(ctype) or ".mp3"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
        path = f.name

    # 3) Whisper direto (sem ffmpeg)
    try:
        with open(path, "rb") as fh:
            tr = _client.audio.transcriptions.create(
                model="whisper-1",
                file=fh,
                language="pt"  # força PT
            )
        return (tr.text or "").strip() or "[áudio vazio]"
    finally:
        try: os.remove(path)
        except: pass

# -- HELPERS --
ALT_KEYS = ("resposta", "answer", "message", "output", "text")

def _pick_first_nonempty(d: dict, keys=ALT_KEYS) -> Optional[str]:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def _humanize_error(payload: Any, status: int, where: str) -> str:
    # tenta extrair erro do backend
    if isinstance(payload, dict):
        err = payload.get("error") or payload.get("detail")
        # aceita formatos comuns: {"error": "..."} ou {"error": {"code":..., "message":...}}
        if isinstance(err, str) and err.strip():
            return f"falha {status} em {where}: {err.strip()}"
        if isinstance(err, dict):
            msg = err.get("message") or err.get("detail") or str(err)
            code = err.get("code")
            return f"falha {status} em {where}: {code or 'erro'} - {msg}"
    return f"falha {status} em {where}: resposta inválida"


def _pipeline(texto: str, user_id: str) -> str:
    """Chama teu fluxo já pronto do /chat mantendo histórico por usuário."""
    url = f"http://localhost:{PORT}/chat"
    try:
        resp = requests.post(
            url,
            json={"pergunta": texto, "user_id": user_id},
            timeout=(3, 50)
        )
        #REMOVER ESSE TRATAMENTO DE EXCECOES NA PROD (INCLUSIVE OS HELPERs)
    except requests.exceptions.ConnectTimeout:
        return "falha: timeout na conexão (servidor lento ou offline)."
    except requests.exceptions.ReadTimeout:
        return "falha: timeout lendo a resposta (modelo lento)."
    except requests.exceptions.ConnectionError:
        return "falha: não consegui conectar no servidor."
    except requests.exceptions.RequestException as e:
        return f"falha de rede: {e.__class__.__name__}"
    
    # http != 200: tenta explicar com o corpo
    if not resp.ok:
        try:
            j = resp.json()
        except ValueError:
            j = None
        return _humanize_error(j, resp.status_code, "/chat")
    
    # http 200: tenta várias chaves antes de desistir
    try:
        j = resp.json()
    except ValueError:
        return "falha: servidor retornou texto não-JSON."
    
    msg = _pick_first_nonempty(j)
    if msg:
        return msg

    # se vier um envelope de erro mesmo com 200
    if "error" in j or "detail" in j:
        return _humanize_error(j, 200, "/chat")

    # fallback com razão clara
    return "falha: payload sem campo de resposta reconhecido (esperado: resposta/answer/message)."


def _send_text(to: str, body: str):
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,                 
        "type": "text",
        "text": {"body": body[:4000]}
    }
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    r = requests.post(url, headers=headers, json=payload, timeout=15)
    print("SEND_TEXT status:", r.status_code)
    print("SEND_TEXT resp:", r.text[:1000])

    # opcional: levantar erro se não for 200
    if r.status_code >= 300:
        raise RuntimeError(f"send_text falhou: {r.status_code} {r.text}")
