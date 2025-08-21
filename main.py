from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer, util
import json
import torch
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# logs simples
logging.basicConfig(level=logging.INFO)

# ===== LOAD BASE =====
model = SentenceTransformer('all-MiniLM-L6-v2')

with open("base_faq.json", "r", encoding="utf-8") as f:
    base = json.load(f)

perguntas = [item["pergunta"] for item in base]
respostas = [item["resposta"] for item in base]

# garante dtype/shape corretos (N, D) em float32
emb_list = [item["embedding"] for item in base]
embeddings = torch.tensor(emb_list, dtype=torch.float32)  # (N, 384)

@app.route("/ping")
def ping():
    return "API MiniLM ativa!"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True, silent=False)
        pergunta_usuario = (data.get("pergunta") or "").strip()
        if not pergunta_usuario:
            return jsonify({"erro": "Pergunta não fornecida"}), 400

        # embedding do usuário -> tensor (1, D)
        emb_user = model.encode(pergunta_usuario, convert_to_tensor=True, normalize_embeddings=False)
        if emb_user.dtype != embeddings.dtype:
            emb_user = emb_user.to(dtype=embeddings.dtype)

        # cosine similarity com toda a base (1, N)
        scores = util.cos_sim(emb_user, embeddings)[0]  # shape: (N,)
        best_idx = int(torch.argmax(scores).item())
        best_score = float(scores[best_idx].item())
        best_answer = respostas[best_idx]

        return jsonify({
            "pergunta": pergunta_usuario,
            "resposta": best_answer,
            "similaridade": round(best_score, 4),
            "match_index": best_idx
        })
    except Exception as e:
        app.logger.exception("Erro no /chat")
        return jsonify({"erro": "Falha interna no servidor", "detalhe": str(e)}), 500

if __name__ == "__main__":
    # porta 10000 combinando com Dockerfile/Render
    app.run(host="0.0.0.0", port=10000)
