# exemplo: memória em RAM (troque por Redis/DB no prod)
SESSIONS = {}
STAGE = {}  # NEW: dict[user_id] = etapa atual (string)
# DOCS = {}

def get_stage(user_id: str) -> str:
    return STAGE.get(user_id, BOAS)

def set_stage(user_id: str, etapa: str) -> None:
    STAGE[user_id] = etapa
  # dict[user_id] = List[Message]

MAX_MSGS = 16

import re, unicodedata
import os, json, time
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import logging
from config import HIGH, MED, TOPK, PORT
import kb
from llm import ask_chatgpt
from whatsapp import bp as whatsapp_bp, _send_document_email
from playbook import build_snippet, proxima_etapa, BOAS, FILTRAR_CIDADE, cidade_valida, is_creci_question, creci_resposta, canonizar_cidades_no_texto

def limpa_negacoes_creci(txt: str) -> str:
    if not txt:
        return txt

    linhas = txt.splitlines()
    out = []
    viu_bloco_creci = False

    for linha in linhas:
        s = linha.strip()

        # --- manter o BLOCO OFICIAL ---
        if re.search(r"(?i)esse é o nosso creci", s):
            viu_bloco_creci = True
            out.append(s)
            continue
        if "28339" in s or "Gênesis" in s:
            viu_bloco_creci = True
            out.append(s)
            continue

        # --- cortar qualquer outra menção a creci ---
        if re.search(r"(?i)\bcreci\b", s):
            continue

        # --- logo após o bloco oficial, cortar reconduções tipo "desculpe, preciso..." ---
        if viu_bloco_creci and re.search(r"(?i)(desculp|precis|para poder|me diga|infelizmente)", s):
            continue

        out.append(s)

    t = "\n".join(out)
    t = re.sub(r"\n{2,}", "\n\n", t).strip()
    return t


DOC_ACK = "Perfeito!"
_DOC_VERBS = (
    "vou", "vamos", "envio", "enviar", "enviei", "enviarei", "enviando",
    "mandei", "mandar", "mandando", "encaminho", "encaminhar", "encaminhei",
    "subo", "subir", "subindo", "anexo", "anexei", "anexar", "segue", "seguirei",
)
_DOC_KEYWORDS = (
    "doc", "documento", "documentos", "arquivo", "arquivos",
    "rg", "cnh", "holerite", "contracheque", "comprovante", "comprovantes",
    "extrato", "extratos", "foto", "fotos", "imagem", "imagens",
    "residencia", "residência", "renda", "ft", "cpf"
)
_DOC_ALWAYS = (
    "segue anexo", "segue doc", "segue documento", "segue os docs",
    "anexo os documentos", "documentos em anexo",
)

def _normalize_for_docs(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFD", text)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t

def is_document_intent(msg: str) -> bool:
    norm = _normalize_for_docs(msg)
    if not norm:
        return False

    if any(token in norm for token in _DOC_ALWAYS):
        return True

    if "anexo" in norm or "anexei" in norm or "anexar" in norm:
        return True

    has_keyword = any(k in norm for k in _DOC_KEYWORDS)
    has_verb = any(v in norm for v in _DOC_VERBS)

    if has_keyword and has_verb:
        return True

    if norm.startswith(("enviei", "mandei", "segue")) and has_keyword:
        return True

    return False

app = Flask(__name__)
app.register_blueprint(whatsapp_bp)
# remover parametros do cors para a prod
CORS(app,
     resources={r"/*": {"origins": "*"}},
     supports_credentials=False,
     methods=["GET","POST","OPTIONS"],
     allow_headers=["Content-Type","Authorization"])
########

logging.basicConfig(level=logging.INFO)

def _trunc(s, n=2000):
    if not isinstance(s, str): return s
    return s if len(s) <= n else s[:n] + "…"

# remover na prod
@app.route("/chat", methods=["OPTIONS"])
def chat_preflight():
    return ("", 204, {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Vary": "Origin",
    })
#######

@app.get("/healthz")
def healthz():
    return {"status": "ok"}, 200


@app.get("/")
def home():
    return render_template("index.html")

# resetar sessão e etapa de um user_id - REMOVER NA PROD
@app.post("/reset")
def reset():
    try:
        data = request.get_json(force=True) or {}
        user_id = (data.get("user_id") or "anon").strip()

        if user_id in SESSIONS:
            del SESSIONS[user_id]
        if user_id in STAGE:
            del STAGE[user_id]

        return jsonify({"status": "ok", "msg": f"sessão resetada para {user_id}"}), 200
    except Exception as e:
        app.logger.exception("erro no /reset")
        return jsonify({"erro": "falha ao resetar", "detalhe": str(e)}), 500


@app.post("/upload-test")
def upload_test():
    if not request.files:
        return jsonify({"ok": False, "erro": "nenhum arquivo recebido"}), 400

    user_id = (request.form.get("user_id") or "webchat_teste").strip() or "webchat_teste"
    caption = request.form.get("caption", "")

    results = []
    for file in request.files.getlist("files"):
        filename = file.filename or "anexo"
        content_type = file.mimetype or "application/octet-stream"
        try:
            content_bytes = file.read()
            if not content_bytes:
                raise ValueError("arquivo vazio")

            sent = _send_document_email(
                user_id=user_id,
                attachment_name=filename,
                content_type=content_type,
                content_bytes=content_bytes,
                caption=caption,
                media_kind="web_upload",
            )

            status = "enviado" if sent else "ignorado"
            detail = None if sent else "Resend não configurado (verifique variáveis RESEND_*)."
        except Exception as e:
            status = "erro"
            detail = str(e)

        entry = {"arquivo": filename, "status": status}
        if detail:
            entry["detalhe"] = detail
        results.append(entry)

    ok = all(item["status"] == "enviado" for item in results)
    return jsonify({"ok": ok, "results": results, "user_id": user_id}), 200

# logica de chatbot
@app.post("/chat")
def chat():
    llm_trace = None
    topk_idx = None
    t0 = time.time()
    ctx = None 

    try:
        data = request.get_json(force=True) or {}
        pergunta = (data.get("pergunta") or "").strip()
        debug = bool(data.get("debug") or os.getenv("DEBUG_LLM") == "1")
        if not pergunta:
            return jsonify({"erro": "Pergunta não fornecida"}), 400

        pergunta = canonizar_cidades_no_texto(pergunta)

        # identificação e histórico
        user_id = (data.get("user_id") or "anon").strip()
        hist = SESSIONS.get(user_id, [])

        # --- etapa atual + overrides simples ---
        # etapa atual do lead
        stage = get_stage(user_id)

        if is_document_intent(pergunta):
            ack = DOC_ACK
            hist += [
                {"role": "user", "content": pergunta},
                {"role": "assistant", "content": ack},
            ]
            SESSIONS[user_id] = hist[-MAX_MSGS:]
            app.logger.info("[APP DOC ACK] %s", json.dumps({
                "user_id": user_id,
                "stage": stage,
                "pergunta": pergunta,
            }, ensure_ascii=False))
            return jsonify({
                "source": "doc_ack",
                "similaridade": 0.0,
                "resposta": ack,
                "match_index": None,
                "topk": [],
                "etapa": stage,
            }), 200

        # calcula próxima etapa com base no que o usuário respondeu
        nova_etapa = proxima_etapa(pergunta, stage)

        mensagem_extra = None
        if "|lista_cidades:" in nova_etapa:
            partes = nova_etapa.split("|lista_cidades:")
            nova_etapa = partes[0].strip()
            mensagem_extra = partes[1].strip()


        # snippet da etapa nova (é ela que será usada como system message)
        snippet = build_snippet(nova_etapa)

        # já atualiza o estágio para a nova etapa
        set_stage(user_id, nova_etapa)


        # --- regra determinística para cidades na etapa FILTRAR ---
        cidade_status = None
        if nova_etapa == FILTRAR_CIDADE:
            if cidade_valida(pergunta):
                cidade_status = "VALIDA"
            else:
                cidade_status = "INVALIDA"



        # playbook snippet
        snippet = build_snippet(nova_etapa)

        # try:
        #     snippet_docs = docs_snippet(user_id)
        # except Exception:
        #     snippet_docs = ""

        combined_snippet = (
            snippet
        )

        snippet_dict = json.loads(build_snippet(nova_etapa))
        if cidade_status == "VALIDA":
            snippet_dict["regra_extra"] = "Confirme positivamente e pergunte se é o primeiro imóvel."
        elif cidade_status == "INVALIDA":
            snippet_dict["regra_extra"] = "Explique que não atendemos essa cidade."

        combined_snippet = json.dumps(snippet_dict, ensure_ascii=False, indent=2)





        # --- busca semântica ---
        # só usar semântica se ainda estamos na etapa BOAS_VINDAS
        use_semantic = (stage == BOAS)
        q_emb = kb.encode_query(pergunta)
        best_idx, best_score = kb.top_match(q_emb)

        # confiança alta: responde direto do FAQ
        if use_semantic and best_score >= HIGH:
            ans = kb.get_answer(best_idx)

            # prefixo determinístico de CRECI
            if is_creci_question(pergunta):
                creci_txt = creci_resposta()
                if creci_txt:
                    ans = f"{creci_txt}\n\n{ans}"
                    ans = limpa_negacoes_creci(ans)

            
            # histórico
            hist += [
                {"role": "user", "content": pergunta},
                {"role": "assistant", "content": ans},
            ]
            SESSIONS[user_id] = hist[-MAX_MSGS:]

            # LOG do lado do app (o que FOI MONTADO ANTES do LLM)
            app.logger.info("[APP TRACE] %s", json.dumps({
                "user_id": user_id,
                "pergunta": pergunta,
                "stage_before": stage,
                "nova_etapa": nova_etapa,
                "cidade_status": cidade_status,
                "combined_snippet": _trunc(combined_snippet, 2000),  # helper já existe
                "use_semantic": use_semantic,
                "best_idx": best_idx,
                "best_score": best_score,
                "topk_idx": topk_idx,
                "ctx_preview": (ctx[:2] if isinstance(ctx, list) else None),
            }, ensure_ascii=False))

            resp = {
                "source": "chatgpt_ctx",
                "similaridade": round(best_score, 4),
                "resposta": ans,
                "match_index": best_idx,
                "topk": topk_idx if topk_idx else [],
                "etapa": nova_etapa
            }

            # Se debug=true E o LLM retornou trace, devolve também no JSON
            if debug and llm_trace:
                resp["trace"] = llm_trace  # <- aqui você enxerga final_messages (todos os prompts)

            return jsonify(resp), 200


        # confiança média/baixa: monta ctx e consulta GPT
        topk_idx, _ = kb.topk(q_emb, TOPK)
        ctx = kb.get_ctx(topk_idx) if best_score >= MED else None

        try:
            res = ask_chatgpt(
                pergunta,
                ctx,
                history=hist,
                playbook_snippet=combined_snippet,  # playbook + status_docs
                debug=debug  # <<< LIGA O TRACE POR REQUISIÇÃO
            )
            if isinstance(res, tuple):
                ans, llm_trace = res
            else:
                ans, llm_trace = res, None
        except Exception as e:
            app.logger.warning(f"llm falhou: {e}")
            ans, llm_trace = "", None

        # fallback se vier vazio
        if not ans or not ans.strip():
            try:
                ans = kb.get_answer(best_idx)
            except Exception:
                ans = "tive um problema para responder. pode reformular em uma frase?"
        
        # adiciona lista de cidades se a etapa pediu
        if mensagem_extra:
            ans = (ans or "") + "\n\n" + mensagem_extra

        # prefixo determinístico de CRECI (independente da etapa)
        if is_creci_question(pergunta):
            creci_txt = creci_resposta()
            if creci_txt:
                ans = f"{creci_txt}\n\n{ans}"
                ans = limpa_negacoes_creci(ans)


        # histórico
        hist += [
            {"role": "user", "content": pergunta},
            {"role": "assistant", "content": ans},
        ]
        SESSIONS[user_id] = hist[-MAX_MSGS:]

        return jsonify({
            "source": "chatgpt_ctx",
            "similaridade": round(best_score, 4),
            "resposta": ans,
            "match_index": best_idx,
            "topk": topk_idx if topk_idx else [],
            "etapa": nova_etapa
        }), 200

    except Exception as e:
        app.logger.exception("erro no /chat")
        return jsonify({"erro": "Falha interna no servidor", "detalhe": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
