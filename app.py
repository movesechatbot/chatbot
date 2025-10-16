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

import re
import os, json, time
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import logging
from config import HIGH, MED, TOPK, PORT
import kb
from llm import ask_chatgpt
from whatsapp import bp as whatsapp_bp
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

# def get_docs(user_id: str):
#     return DOCS.setdefault(user_id, {"rg_cnh": False, "residencia": False, "renda": False, "email": ""})

# def docs_snippet(user_id: str) -> str:
#     d = get_docs(user_id)
#     faltando = []
#     if not d["rg_cnh"]: faltando.append("RG/CNH")
#     if not d["residencia"]: faltando.append("comprovante de residência")
#     if not d["renda"]: faltando.append("comprovante de renda")
#     email_status = d["email"] or "não informado"
#     return (
#         "status_docs:\n"
#         f"- rg_cnh: {d['rg_cnh']}\n- residencia: {d['residencia']}\n- renda: {d['renda']}\n- email: {email_status}\n"
#         f"- faltando: {', '.join(faltando) if faltando else 'nenhum'}"
#     )

# @app.post("/docs")
# def docs_update():
#     try:
#         data = request.get_json(force=True) or {}
#         user_id = (data.get("user_id") or "anon").strip()
#         kind = (data.get("kind") or "").lower()
#         label = (data.get("label") or "").lower()
#         email = (data.get("email") or "").strip()

#         d = get_docs(user_id)
#         if kind == "rg_cnh":
#             d["rg_cnh"] = True
#         elif kind == "residencia":
#             d["residencia"] = True
#         elif kind == "renda":
#             d["renda"] = True
#         elif kind == "email" and email:
#             d["email"] = email

#         return jsonify({"ok": True, "docs": d}), 200
#     except Exception as e:
#         app.logger.exception("erro no /docs")
#         return jsonify({"ok": False, "erro": str(e)}), 500

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
