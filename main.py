from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from sentence_transformers import SentenceTransformer, util
import json, torch, logging

app = Flask(__name__)

# Libera CORS globalmente (pode ser redundante com cross_origin, mas ajuda)
CORS(app, supports_credentials=False)

logging.basicConfig(level=logging.INFO)

# ===== Carrega base =====
model = SentenceTransformer('all-MiniLM-L6-v2')

with open("base_faq.json", "r", encoding="utf-8") as f:
    base = json.load(f)

perguntas = [item["pergunta"] for item in base]
respostas = [item["resposta"] for item in base]
embeddings = torch.tensor([item["embedding"] for item in base], dtype=torch.float32)

# Garantia extra de headers CORS
@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

# Tratamento explícito para OPTIONS
@app.route("/chat", methods=["OPTIONS"])
@cross_origin(origins="*")
def chat_options():
    return ("", 204)

@app.route("/ping", methods=["GET"])
@cross_origin(origins="*")
def ping():
    return "API MiniLM ativa!"

@app.route("/chat", methods=["POST"])
@cross_origin(origins="*")
def chat():
    try:
        data = request.get_json(force=True)
        pergunta_usuario = (data.get("pergunta") or "").strip()
        if not pergunta_usuario:
            return jsonify({"erro": "Pergunta não fornecida"}), 400

        emb_user = model.encode(pergunta_usuario, convert_to_tensor=True)
        if emb_user.dtype != embeddings.dtype:
            emb_user = emb_user.to(dtype=embeddings.dtype)

        scores = util.cos_sim(emb_user, embeddings)[0]
        best_idx = int(torch.argmax(scores).item())
        best_score = float(scores[best_idx].item())
        return jsonify({
            "pergunta": pergunta_usuario,
            "resposta": respostas[best_idx],
            "similaridade": round(best_score, 4),
            "match_index": best_idx
        })
    except Exception as e:
        app.logger.exception("Erro no /chat")
        return jsonify({"erro": "Falha interna no servidor", "detalhe": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
