# whatsapp.py
import base64
import tempfile, os, mimetypes, requests  # hmac, hashlib
from typing import Optional, Any
from flask import Blueprint, request, abort
from openai import OpenAI
from pathlib import Path
from config import (
    WHATSAPP_TOKEN,
    PHONE_NUMBER_ID,
    VERIFY_TOKEN,
    PORT,
    RESEND_API_KEY,
    RESEND_FROM_EMAIL,
    RESEND_TO_EMAIL,
    RESEND_SUBJECT,
)
import re, requests

import followup

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
EMAIL_RE = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.I)

# limites de anexos (válido para web e WhatsApp)
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB
IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp", "heic", "heif"}
ALLOWED_EXTS = IMAGE_EXTS | {"pdf", "docx"}

def _notify_doc(kind: str, user: str, label: str = "", email: str = ""):
    try:
        requests.post(
            f"http://localhost:{PORT}/docs",
            json={"user_id": user, "kind": kind, "label": label, "email": email},
            timeout=5,
        )
    except Exception:
        pass


@bp.get("/whatsapp")
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge", ""), 200
    return "forbidden", 403

@bp.post("/whatsapp")
def incoming():
    data = request.get_json() or {}
    entries = data.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = value.get("contacts") or []
            for c in contacts:
                wid = (c.get("wa_id") or "").strip()
                prof = c.get("profile") or {}
                name = (prof.get("name") or "").strip()
                if wid and name:
                    followup.update_profile(wid, name)
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
                                f"http://127.0.0.1:{PORT}/reset",
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

                    m = EMAIL_RE.search(txt)
                    if m:
                        _notify_doc("email", user, email=m.group(0))

                elif t in ("document", "image"):
                    media_payload = msg.get(t, {}) or {}
                    caption = (media_payload.get("caption") or "").strip()
                    filename = media_payload.get("filename")
                    media_id = media_payload.get("id")
                    caption_lower = caption.lower()
                    name_lower = (filename or "").lower()
                    meta = f"{caption_lower} {name_lower}"


                    if media_id:
                        try:
                            att_name, att_type, att_bytes = _download_media(media_id, filename)
                            _send_document_email(
                                user_id=user,
                                attachment_name=att_name,
                                content_type=att_type,
                                content_bytes=att_bytes,
                                caption=caption,
                                media_kind=t,
                            )
                        except Exception as e:
                            bp.logger.warning("falha ao enviar email via Resend: %s", e)

                    notifier = globals().get("_notify_doc")
                    if callable(notifier):
                        if any(k in meta for k in ("rg", "cnh", "carteira de motorista", "identidade")):
                            notifier("rg_cnh", user)
                        elif any(k in meta for k in ("comprovante de residencia", "residência", "luz", "agua", "água", "energia")):
                            notifier("residencia", user)
                        elif any(k in meta for k in ("holerite", "contracheque", "renda", "pro labore", "decorrente renda")):
                            notifier("renda", user)
                    else:
                        # se não souber, não marca; o GPT ainda verá a msg no histórico
                        pass

                    # segue fluxo normal (se quiser, pode responder um “recebido”)
                    reply = _pipeline(caption or "enviei um documento", user)
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
    url = f"http://127.0.0.1:{PORT}/chat"
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


def _download_media(media_id: str, preferred_name: Optional[str] = None) -> tuple[str, str, bytes]:
    meta = requests.get(
        f"https://graph.facebook.com/v22.0/{media_id}",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        timeout=15,
    ).json()
    url = meta.get("url")
    if not url:
        raise RuntimeError("media url ausente na resposta do Graph API.")

    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        timeout=30,
    )
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type") or meta.get("mime_type") or "application/octet-stream"
    filename = preferred_name or meta.get("filename") or meta.get("name")
    if not filename:
        ext = mimetypes.guess_extension(content_type) or ""
        filename = f"{media_id}{ext}"

    return filename, content_type, resp.content


def _send_document_email(
    user_id: str,
    attachment_name: str,
    content_type: str,
    content_bytes: bytes,
    caption: str,
    media_kind: str,
) -> bool:
    if not (RESEND_API_KEY and RESEND_FROM_EMAIL and RESEND_TO_EMAIL):
        bp.logger.debug("Resend não configurado; anexos não serão enviados por email.")
        return False

    size_bytes = len(content_bytes)
    if size_bytes > MAX_ATTACHMENT_BYTES:
        raise ValueError(f"arquivo excede limite de {MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB")

    suffix = Path(attachment_name).suffix.lower().lstrip(".")
    content_type = (content_type or "").lower()

    is_image = content_type.startswith("image/") or suffix in IMAGE_EXTS
    is_pdf = suffix == "pdf" or content_type == "application/pdf"
    is_docx = suffix == "docx" or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    if not (is_image or is_pdf or is_docx):
        raise ValueError("formato não permitido (somente imagens, PDF ou DOCX)")

    attachment_b64 = base64.b64encode(content_bytes).decode("ascii")
    body_lines = [
        f"Documento recebido do usuário WhatsApp: {user_id}",
        f"Tipo de mídia: {media_kind}",
        f"Nome original: {attachment_name}",
        f"Content-Type: {content_type}",
    ]
    if caption:
        body_lines.append(f"Legenda: {caption}")

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [RESEND_TO_EMAIL],
        "subject": RESEND_SUBJECT,
        "text": "\n".join(body_lines),
        "attachments": [
            {
                "filename": attachment_name,
                "content": attachment_b64,
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(
        "https://api.resend.com/emails",
        json=payload,
        headers=headers,
        timeout=15,
    )

    if resp.status_code >= 300:
        raise RuntimeError(f"Resend retornou {resp.status_code}: {resp.text[:200]}")

    return True


followup.init(_send_text)
