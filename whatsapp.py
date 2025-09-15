# whatsapp.py
import tempfile, os, mimetypes, hmac, hashlib, requests
from typing import Optional
from flask import Blueprint, request, abort
from openai import OpenAI
from config import WHATSAPP_TOKEN, ID_PHONE, APP_SECRET, PORT

bp = Blueprint("whatsapp", __name__)

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def _verify_signature(raw: bytes) -> bool:
    if not APP_SECRET:
        return True  # se não quiser validar assinatura agora
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not sig.startswith("sha256="): 
        return False
    digest = hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, f"sha256={digest}")

@bp.get("/whatsapp")
def verify():
    # validação do webhook no painel da Meta
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == WHATSAPP_TOKEN:
        return request.args.get("hub.challenge", ""), 200
    return "forbidden", 403

@bp.post("/whatsapp")
def incoming():
    raw = request.get_data()
    if not _verify_signature(raw):
        return "invalid signature", 403

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
                    txt = msg["text"]["body"]
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

def _pipeline(texto: str, user_id: str) -> str:
    """Chama teu fluxo já pronto do /chat mantendo histórico por usuário."""
    try:
        resp = requests.post(
            f"http://localhost:{PORT}/chat",
            json={"pergunta": texto, "user_id": user_id},
            timeout=15
        )
        j = resp.json()
        return j.get("resposta") or "não consegui responder agora."
    except Exception:
        return "tive um problema para processar sua mensagem. pode repetir em uma frase?"

def _send_text(to: str, body: str):
    requests.post(
        f"https://graph.facebook.com/v22.0/{ID_PHONE}/messages",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}",
                 "Content-Type":"application/json"},
        json={
            "messaging_product":"whatsapp",
            "to": to,
            "type":"text",
            "text": {"body": body[:4000]}  # corta segurança
        },
        timeout=15
    )
