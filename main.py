from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
import json, torch, logging, os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)
logging.basicConfig(level=logging.INFO)

# ===== base =====
model = SentenceTransformer('all-MiniLM-L6-v2')
with open("base_faq.json", "r", encoding="utf-8") as f:
    base = json.load(f)

perguntas = [item.get("pergunta","") for item in base]
respostas = [item.get("resposta","") for item in base]
embeddings = torch.tensor([item["embedding"] for item in base], dtype=torch.float32)

# ===== thresholds =====
HIGH = float(os.getenv("HIGH", "0.78"))
MED  = float(os.getenv("MED",  "0.62"))
TOPK = int(os.getenv("TOPK", "3"))

# ===== openai =====
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.1-mini")

def ask_chatgpt(pergunta: str, ctx: list[str] | None):
    sys = "seja objetivo. se não souber com base no contexto, diga que não sabe."
    if ctx:
        user = f"pergunta: {pergunta}\n\ncontexto:\n- " + "\n- ".join(ctx)
    else:
        user = pergunta
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.2,
        max_tokens=300,
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
    )
    return resp.choices[0].message.content.strip()

@app.route("/ping", methods=["GET"])
def ping():
    return "API MiniLM ativa!"

@app.route("/chat", methods=["OPTIONS"])
def chat_options():
    r = app.make_response("")
    r.status_code = 204
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return r

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        pergunta_usuario = (data.get("pergunta") or "").strip()
        if not pergunta_usuario:
            return jsonify({"erro": "Pergunta não fornecida"}), 400

        emb_user = model.encode(pergunta_usuario, convert_to_tensor=True, normalize_embeddings=True)
        if embeddings.dtype != emb_user.dtype:
            emb_user = emb_user.to(dtype=embeddings.dtype)

        # similaridade (cosine)
        scores = util.cos_sim(emb_user, torch.nn.functional.normalize(embeddings, p=2, dim=1))[0]
        best_idx = int(torch.argmax(scores).item())
        best_score = float(scores[best_idx].item())

        # decisão
        if best_score >= HIGH:
            return jsonify({
                "source": "local",
                "similaridade": round(best_score, 4),
                "resposta": respostas[best_idx],
                "match_index": best_idx
            })

        # médio: top-k como contexto
        topk_vals, topk_idx = torch.topk(scores, k=min(TOPK, len(respostas)))
        ctx = []
        for i in topk_idx.tolist():
            if perguntas[i]:
                ctx.append(f"Q: {perguntas[i]}\nA: {respostas[i]}")
            else:
                ctx.append(respostas[i])

        ans = ask_chatgpt(pergunta_usuario, ctx if best_score >= MED else None)
        return jsonify({
            "source": "chatgpt_ctx" if best_score >= MED else "chatgpt_open",
            "similaridade": round(best_score, 4),
            "resposta": ans,
            "match_index": best_idx,
            "topk": topk_idx.tolist()
        })
    except Exception as e:
        app.logger.exception("Erro no /chat")
        return jsonify({"erro": "Falha interna no servidor", "detalhe": str(e)}), 500

if __name__ == "__main__":
    # respeita PORT da Render
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
