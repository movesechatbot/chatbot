from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from config import HIGH, MED, TOPK, PORT
import kb
from llm import ask_chatgpt

app = Flask(__name__)
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

# logica de chatbot
@app.post("/chat")
def chat():
    try:
        data = request.get_json(force=True) or {}
        pergunta = (data.get("pergunta") or "").strip()
        if not pergunta:
            return jsonify({"erro":"Pergunta não fornecida"}), 400

        q_emb = kb.encode_query(pergunta)
        best_idx, best_score = kb.top_match(q_emb)

        if best_score >= HIGH:
            return jsonify({
                "source": "local",
                "similaridade": round(best_score, 4),
                "resposta": kb.get_answer(best_idx),
                "match_index": best_idx
            }), 200

        topk_idx, _ = kb.topk(q_emb, TOPK)
        ctx = kb.get_ctx(topk_idx) if best_score >= MED else None

        # blindagem contra falha da OpenAI (sem 500)
        try:
            ans = ask_chatgpt(pergunta, ctx)
        except Exception as e:
            app.logger.warning(f"llm falhou: {e}")
            ans = "tive um problema ao consultar o modelo externo; respondo com base no FAQ."
            # ans = kb.get_answer(best_idx)

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
