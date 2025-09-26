# exemplo: memória em RAM (troque por Redis/DB no prod)
SESSIONS = {}
STAGE = {}  # NEW: dict[user_id] = etapa atual (string)
DOCS = {}

def get_stage(user_id: str) -> str:
    return STAGE.get(user_id, BOAS)

def set_stage(user_id: str, etapa: str) -> None:
    STAGE[user_id] = etapa
  # dict[user_id] = List[Message]

MAX_MSGS = 40

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from config import HIGH, MED, TOPK, PORT
import kb
from llm import ask_chatgpt
from whatsapp import bp as whatsapp_bp
from playbook import build_snippet, proxima_etapa, BOAS

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

@app.get("/ping")
def ping():
    return f"API ativa! base={kb.size()}"

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

def get_docs(user_id: str):
    return DOCS.setdefault(user_id, {"rg_cnh": False, "residencia": False, "renda": False, "email": ""})

def docs_snippet(user_id: str) -> str:
    d = get_docs(user_id)
    faltando = []
    if not d["rg_cnh"]: faltando.append("RG/CNH")
    if not d["residencia"]: faltando.append("comprovante de residência")
    if not d["renda"]: faltando.append("comprovante de renda")
    email_status = d["email"] or "não informado"
    return (
        "status_docs:\n"
        f"- rg_cnh: {d['rg_cnh']}\n- residencia: {d['residencia']}\n- renda: {d['renda']}\n- email: {email_status}\n"
        f"- faltando: {', '.join(faltando) if faltando else 'nenhum'}"
    )

@app.post("/docs")
def docs_update():
    try:
        data = request.get_json(force=True) or {}
        user_id = (data.get("user_id") or "anon").strip()
        kind = (data.get("kind") or "").lower()
        label = (data.get("label") or "").lower()
        email = (data.get("email") or "").strip()

        d = get_docs(user_id)
        if kind == "rg_cnh":
            d["rg_cnh"] = True
        elif kind == "residencia":
            d["residencia"] = True
        elif kind == "renda":
            d["renda"] = True
        elif kind == "email" and email:
            d["email"] = email

        return jsonify({"ok": True, "docs": d}), 200
    except Exception as e:
        app.logger.exception("erro no /docs")
        return jsonify({"ok": False, "erro": str(e)}), 500

# logica de chatbot
@app.post("/chat")
def chat():
    try:
        data = request.get_json(force=True) or {}
        pergunta = (data.get("pergunta") or "").strip()
        if not pergunta:
            return jsonify({"erro": "Pergunta não fornecida"}), 400

        # identificação e histórico
        user_id = (data.get("user_id") or "anon").strip()
        hist = SESSIONS.get(user_id, [])

        # --- etapa atual + overrides simples ---
        def wants_contextualizacao(txt: str) -> bool:
            m = (txt or "").lower()
            gatilhos = ("explica", "como funciona", "programa", "minha casa minha vida", "mcmv")
            return any(g in m for g in gatilhos)

        stage = get_stage(user_id)
        stage_for_this_turn = "CONTEXTUALIZACAO" if wants_contextualizacao(pergunta) else stage

        # playbook snippet
        snippet = build_snippet(stage_for_this_turn)

        # status de documentos (opcional; se não existir, ignora)
        try:
            snippet_docs = docs_snippet(user_id)  # ex.: status_docs: rg_cnh/residencia/renda/email
        except Exception:
            snippet_docs = ""

        combined_snippet = snippet + (("\n\n" + snippet_docs) if snippet_docs else "")

        # --- busca semântica ---
        q_emb = kb.encode_query(pergunta)
        best_idx, best_score = kb.top_match(q_emb)

        # confiança alta: responde direto do FAQ
        if best_score >= HIGH:
            ans = kb.get_answer(best_idx)

            # histórico
            hist += [
                {"role": "user", "content": pergunta},
                {"role": "assistant", "content": ans},
            ]
            SESSIONS[user_id] = hist[-MAX_MSGS:]

            # avança etapa
            new_stage = proxima_etapa(pergunta, stage_for_this_turn)
            set_stage(user_id, new_stage)

            return jsonify({
                "source": "local",
                "similaridade": round(best_score, 4),
                "resposta": ans,
                "match_index": best_idx
            }), 200

        # confiança média/baixa: monta ctx e consulta GPT
        topk_idx, _ = kb.topk(q_emb, TOPK)
        ctx = kb.get_ctx(topk_idx) if best_score >= MED else None

        try:
            ans = ask_chatgpt(
                pergunta,
                ctx,
                history=hist,
                playbook_snippet=combined_snippet  # playbook + status_docs
            )
        except Exception as e:
            app.logger.warning(f"llm falhou: {e}")
            ans = ""

        # fallback se vier vazio
        if not ans or not ans.strip():
            try:
                ans = kb.get_answer(best_idx)
            except Exception:
                ans = "tive um problema para responder. pode reformular em uma frase?"

        # histórico
        hist += [
            {"role": "user", "content": pergunta},
            {"role": "assistant", "content": ans},
        ]
        SESSIONS[user_id] = hist[-MAX_MSGS:]

        # avança etapa
        new_stage = proxima_etapa(pergunta, stage_for_this_turn)
        set_stage(user_id, new_stage)

        return jsonify({
            "source": "chatgpt_ctx",
            "similaridade": round(best_score, 4),
            "resposta": ans,
            "match_index": best_idx,
            "topk": topk_idx
        }), 200

    except Exception as e:
        app.logger.exception("erro no /chat")
        return jsonify({"erro": "Falha interna no servidor", "detalhe": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
