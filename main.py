from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer, util
import json
import torch

app = Flask(__name__)

# Carrega o modelo MiniLM
model = SentenceTransformer('all-MiniLM-L6-v2')

# Carrega a base de dados gerada
with open("base_faq.json", "r", encoding="utf-8") as f:
    base = json.load(f)

perguntas = [item['pergunta'] for item in base]
respostas = [item['resposta'] for item in base]
embeddings = torch.tensor([item['embedding'] for item in base])

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    pergunta_usuario = data.get("pergunta", "").strip()

    if not pergunta_usuario:
        return jsonify({"erro": "Pergunta não fornecida"}), 400

    # Gera embedding da pergunta do usuário
    embedding_usuario = model.encode(pergunta_usuario, convert_to_tensor=True)

    # Calcula similaridade
    scores = util.cos_sim(embedding_usuario, embeddings)[0]
    melhor_idx = scores.argmax().item()
    melhor_resposta = respostas[melhor_idx]
    score_val = round(scores[melhor_idx].item(), 4)

    return jsonify({
        "pergunta": pergunta_usuario,
        "resposta": melhor_resposta,
        "similaridade": score_val
    })

@app.route("/ping")
def ping():
    return "API MiniLM ativa!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
