# Aqui desenvolvi uma API do JSON para ficar rodando no Flask, para carregar a base_faq.json apenas uma vez na memoria RAM, assim, deixando
# o tempo de resposta extremamente rápido para o usuário. Caso não tivessemos essa API rodando no Flask, o usuario rodaria uma base_faq toda 
# vez que enviasse uma pergunta no chat.


from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
import json
import numpy as np
import os

app = Flask(__name__)

# Carrega o modelo e a base do FAQ uma única vez
print("Carregando modelo e base de dados...")
modelo = SentenceTransformer('all-MiniLM-L6-v2')

with open("dev-utils/base_faq.json", "r", encoding="utf-8") as f:
    base_faq = json.load(f)

# Pré-processa os embeddings do FAQ
faq_embeddings = [np.array(item["embedding"]) for item in base_faq]

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

@app.route("/responder", methods=["POST"])
def responder():
    pergunta = request.json.get("pergunta", "")
    if not pergunta:
        return jsonify({"erro": "Pergunta não recebida"}), 400

    embedding = modelo.encode(pergunta)

    # Busca o mais próximo
    melhor_sim = -1
    melhor_resposta = "Desculpe, não encontrei uma resposta para isso."

    for i, emb in enumerate(faq_embeddings):
        sim = cosine_similarity(embedding, emb)
        if sim > melhor_sim:
            melhor_sim = sim
            melhor_resposta = base_faq[i]["resposta"]

    return jsonify({
        "resposta": melhor_resposta,
        "similaridade": round(float(melhor_sim), 4)
    })

if __name__ == "__main__":
    app.run(debug=True)
