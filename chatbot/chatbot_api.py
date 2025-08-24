# api flask com fallback pro chatgpt quando a similaridade for média/baixa
# deps: pip install sentence-transformers openai flask numpy

import os, json, numpy as np
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from numpy.linalg import norm
from openai import OpenAI

# thresholds
HIGH, MED = 0.78, 0.62   # ajuste depois vendo logs
TOPK = 3

app = Flask(__name__)

print("carregando modelo e base...")
modelo = SentenceTransformer('all-MiniLM-L6-v2')

with open("base_faq.json", "r", encoding="utf-8") as f:
    base_faq = json.load(f)  # [{"resposta": "...", "embedding": [...], (opcional) "pergunta": "..."}]

# matriz de embeddings normalizados (p/ cosseno)
M = np.array([np.array(item["embedding"], dtype=np.float32) for item in base_faq], dtype=np.float32)
M = M / np.clip(norm(M, axis=1, keepdims=True), 1e-9, None)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def embed(texto: str) -> np.ndarray:
    v = modelo.encode([texto], normalize_embeddings=True)[0].astype(np.float32)
    return v

def buscar_topk(qv: np.ndarray, k: int = TOPK):
    sims = M @ qv  # como tudo está normalizado, isso é cosseno
    idx = np.argpartition(-sims, range(min(k, len(sims))))[:k]
    idx = idx[np.argsort(-sims[idx])]
    return [(int(i), float(sims[i])) for i in idx]

def ask_chatgpt(pergunta: str, contexto_chunks: list[str] | None):
    sys = "seja objetivo. se não souber a partir do contexto, diga que não sabe."
    if contexto_chunks:
        user = f"pergunta: {pergunta}\n\ncontexto:\n- " + "\n- ".join(contexto_chunks)
        model = os.environ.get("OPENAI_MODEL", "gpt-5.1-mini")
    else:
        user = pergunta
        model = os.environ.get("OPENAI_MODEL", "gpt-5.1-mini")

    r = client.chat.completions.create(
        model=model,
        temperature=0.2,
        max_tokens=300,
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
    )
    return r.choices[0].message.content.strip()

@app.post("/responder")
def responder():
    data = request.get_json(silent=True) or {}
    pergunta = (data.get("pergunta") or "").strip()
    if not pergunta:
        return jsonify({"erro":"Pergunta não recebida"}), 400

    qv = embed(pergunta)
    hits = buscar_topk(qv, TOPK)
    top_idx, top_score = hits[0]
    top_resposta = base_faq[top_idx].get("resposta", "")

    # alta confiança → responde local
    if top_score >= HIGH:
        return jsonify({
            "source": "local",
            "similaridade": round(top_score, 4),
            "resposta": top_resposta,
            "ids": [i for i,_ in hits]
        })

    # média → chatgpt com contexto (top-k)
    if top_score >= MED:
        ctx = []
        for i,_ in hits:
            # use "pergunta" se existir; senão, use "resposta" como contexto
            p = base_faq[i].get("pergunta")
            r = base_faq[i].get("resposta", "")
            ctx.append((p if p else r).strip())
        ans = ask_chatgpt(pergunta, ctx)
        return jsonify({
            "source": "chatgpt_ctx",
            "similaridade": round(top_score, 4),
            "resposta": ans,
            "ids": [i for i,_ in hits]
        })

    # baixa → chatgpt aberto (ou peça esclarecimento)
    ans = ask_chatgpt(pergunta, None)
    return jsonify({
        "source": "chatgpt_open",
        "similaridade": round(top_score, 4),
        "resposta": ans,
        "ids": [i for i,_ in hits]
    })

if __name__ == "__main__":
    # defina OPENAI_API_KEY e (opcional) OPENAI_MODEL
    app.run(debug=True)
