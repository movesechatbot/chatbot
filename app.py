# exemplo: memória em RAM (troque por Redis/DB no prod)
SESSIONS = {}
STAGE = {}  # NEW: dict[user_id] = etapa atual (string)
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

# uma validação para saber se a api ta rodando (deve retornar tamanho 30 ou relevante ao tamanho da base)
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

# logica de chatbot
@app.post("/chat")
def chat():
    try:
        data = request.get_json(force=True) or {}
        pergunta = (data.get("pergunta") or "").strip()
        if not pergunta:
            return jsonify({"erro":"Pergunta não fornecida"}), 400
        
        # pega um identificador do usuário
        user_id = (data.get("user_id") or "anon").strip()  # no WhatsApp use o número
        hist = SESSIONS.get(user_id, [])
        
        # etapa atual + snippet do playbook
        stage = get_stage(user_id)                 # <- tua função/estado de etapa
        snippet = build_snippet(stage)             # <- do playbook.py

        q_emb = kb.encode_query(pergunta)
        best_idx, best_score = kb.top_match(q_emb)

        if best_score >= HIGH:
            ans = kb.get_answer(best_idx)
            hist += [
                 {"role":"user","content": pergunta},
                 {"role":"assistant","content": ans}
             ]
            SESSIONS[user_id] = hist[-MAX_MSGS:]

            # avança etapa
            new_stage = proxima_etapa(pergunta, stage)
            set_stage(user_id, new_stage)

            return jsonify({
                "source": "local",
                "similaridade": round(best_score, 4),
                "resposta": ans,
                "match_index": best_idx
            }), 200

        topk_idx, _ = kb.topk(q_emb, TOPK)
        ctx = kb.get_ctx(topk_idx) if best_score >= MED else None

        # blindagem contra falha da OpenAI (sem 500)
        try:
            ans = ask_chatgpt(
                pergunta, 
                ctx, 
                history=hist,
                playbook_snippet=snippet
                )
        except Exception as e:
            app.logger.warning(f"llm falhou: {e}")
            ans = "tive um problema ao consultar o modelo externo; respondo com base no FAQ."
            # ans = kb.get_answer(best_idx)

        hist += [
            {"role":"user","content": pergunta}, 
            {"role":"assistant","content": ans}]
        
        SESSIONS[user_id] = hist[-MAX_MSGS:]
        
         # avança etapa
        new_stage = proxima_etapa(pergunta, stage)
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
        return jsonify({"erro":"Falha interna no servidor", "detalhe": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
