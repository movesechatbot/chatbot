# exemplo: memória em RAM (troque por Redis/DB no prod)
SESSIONS = {}
STAGE = {}  # NEW: dict[user_id] = etapa atual (string)
DOCS = {}

def get_stage(user_id: str) -> str:
    return STAGE.get(user_id, BOAS)

def set_stage(user_id: str, etapa: str) -> None:
    STAGE[user_id] = etapa
  # dict[user_id] = List[Message]

MAX_MSGS = 16

def get_docs(user_id: str) -> dict:
    return DOCS.setdefault(user_id, {
        "rg_cnh": False,
        "residencia": False,
        "renda": False,
        "email": "",
    })

def docs_completed(info: dict) -> bool:
    return bool(info.get("rg_cnh") and info.get("residencia") and info.get("renda") and info.get("email"))

from datetime import datetime, timezone
import re, unicodedata
import os, json, time
from flask import Flask, request, jsonify, render_template, Blueprint
from flask_cors import CORS
import logging
from config import HIGH, MED, TOPK, PORT, ALLOWED_ORIGINS
import kb
from llm import ask_chatgpt
from whatsapp import bp as whatsapp_bp, _send_document_email
from playbook import build_snippet, proxima_etapa, BOAS, FILTRAR_CIDADE, cidade_valida, is_creci_question, creci_resposta, canonizar_cidades_no_texto
import followup

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


DOC_ACK = "Perfeito!"
_DOC_VERBS = (
    "vou", "vamos", "envio", "enviar", "enviei", "enviarei", "enviando",
    "mandei", "mandar", "mandando", "encaminho", "encaminhar", "encaminhei",
    "subo", "subir", "subindo", "anexo", "anexei", "anexar", "segue", "seguirei",
)
_DOC_KEYWORDS = (
    "doc", "documento", "documentos", "arquivo", "arquivos",
    "rg", "cnh", "holerite", "contracheque", "comprovante", "comprovantes",
    "extrato", "extratos", "foto", "fotos", "imagem", "imagens",
    "residencia", "residência", "renda", "ft", "cpf"
)
_DOC_ALWAYS = (
    "segue anexo", "segue doc", "segue documento", "segue os docs",
    "anexo os documentos", "documentos em anexo",
)

def _normalize_for_docs(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFD", text)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t

def is_document_intent(msg: str) -> bool:
    norm = _normalize_for_docs(msg)
    if not norm:
        return False

    if any(token in norm for token in _DOC_ALWAYS):
        return True

    if "anexo" in norm or "anexei" in norm or "anexar" in norm:
        return True

    has_keyword = any(k in norm for k in _DOC_KEYWORDS)
    has_verb = any(v in norm for v in _DOC_VERBS)

    if has_keyword and has_verb:
        return True

    if norm.startswith(("enviei", "mandei", "segue")) and has_keyword:
        return True

    return False

app = Flask(__name__)
app.register_blueprint(whatsapp_bp)
# Configuração CORS segura
CORS(
    app,
    origins=ALLOWED_ORIGINS,
    supports_credentials=False,  # Mantenha False para APIs sem cookies
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"],
    max_age=600  # Cache de preflight por 10 minutos
)

logging.basicConfig(level=logging.INFO)

def _trunc(s, n=2000):
    if not isinstance(s, str): return s
    return s if len(s) <= n else s[:n] + "…"

# === Histórico completo de uma conversa ===
@app.get("/admin/conversa/<user_id>")
def admin_conversa(user_id):
    hist = SESSIONS.get(user_id, [])
    return jsonify({
        "user_id": user_id,
        "mensagens": hist,                 # [{role, content, ...}]
        "stage": get_stage(user_id)
    })

@app.get("/admin/live/<user_id>")
def admin_live(user_id):
    """
    Retorna o histórico recente (até MAX_MSGS) para exibição em tempo real na tela de testes.
    """
    hist = SESSIONS.get(user_id, [])
    return jsonify({
        "user_id": user_id,
        "mensagens": hist[-MAX_MSGS:]
    })

@app.get("/admin/conversas")
def listar_conversas():
    out = []
    for user_id, hist in SESSIONS.items():
        ultima = hist[-1]["content"] if hist else ""
        hora = time.strftime("%H:%M")
        out.append({"user_id": user_id, "ultima": ultima, "hora": hora})
    return jsonify(out)

@app.post("/admin/enviar")
def admin_enviar():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    msg = data.get("mensagem", "").strip()
    if not user_id or not msg:
        return jsonify({"erro": "faltando dados"}), 400

    hist = SESSIONS.get(user_id, [])
    agora = datetime.now().strftime("%H:%M")

    # ✅ o admin é o "assistant", pois é quem fala do lado da IA
    hist.append({"role": "assistant", "content": msg, "hora": agora})
    SESSIONS[user_id] = hist[-MAX_MSGS:]

    # não dispara o chatbot
    return jsonify({"ok": True, "mensagem": msg, "hora": agora}), 200

@app.get("/healthz")
def healthz():
    return {"status": "ok"}, 200

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/teste")
def teste():
    # Página antiga de testes
    return render_template("teste.html")

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

@app.post("/upload-test")
def upload_test():
    if not request.files:
        return jsonify({"ok": False, "erro": "nenhum arquivo recebido"}), 400

    user_id = (request.form.get("user_id") or "webchat_teste").strip() or "webchat_teste"
    caption = request.form.get("caption", "")

    results = []
    for file in request.files.getlist("files"):
        filename = file.filename or "anexo"
        content_type = file.mimetype or "application/octet-stream"
        try:
            content_bytes = file.read()
            if not content_bytes:
                raise ValueError("arquivo vazio")

            sent = _send_document_email(
                user_id=user_id,
                attachment_name=filename,
                content_type=content_type,
                content_bytes=content_bytes,
                caption=caption,
                media_kind="web_upload",
            )

            status = "enviado" if sent else "ignorado"
            detail = None if sent else "Resend não configurado (verifique variáveis RESEND_*)."
        except Exception as e:
            status = "erro"
            detail = str(e)

        entry = {"arquivo": filename, "status": status}
        if detail:
            entry["detalhe"] = detail
        results.append(entry)

    ok = all(item["status"] == "enviado" for item in results)
    return jsonify({"ok": ok, "results": results, "user_id": user_id}), 200

@app.post("/docs")
def docs_update():
    try:
        data = request.get_json(force=True) or {}
        user_id = (data.get("user_id") or "anon").strip()
        kind = (data.get("kind") or "").lower()
        label = (data.get("label") or "").lower()
        email = (data.get("email") or "").strip()

        info = get_docs(user_id)

        if kind == "rg_cnh":
            info["rg_cnh"] = True
        elif kind == "residencia":
            info["residencia"] = True
        elif kind == "renda":
            info["renda"] = True
        elif kind == "email" and email:
            info["email"] = email
        elif kind == "reset":
            info.update({"rg_cnh": False, "residencia": False, "renda": False, "email": ""})

        followup.update_docs_status(user_id, info)

        goal_reached = docs_completed(info)
        followup.mark_goal(user_id, goal_reached)

        return jsonify({"ok": True, "docs": info, "goal_reached": goal_reached}), 200
    except Exception as e:
        app.logger.exception("erro no /docs")
        return jsonify({"ok": False, "erro": str(e)}), 500

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

        followup.mark_user_reply(user_id)

        # --- etapa atual + overrides simples ---
        # etapa atual do lead
        stage = get_stage(user_id)

        if is_document_intent(pergunta):
            ack = DOC_ACK
            agora = datetime.now().strftime("%H:%M")
            hist += [
                {"role": "user", "content": pergunta, "hora": agora},
                {"role": "assistant", "content": ack, "hora": agora},
            ]
            SESSIONS[user_id] = hist[-MAX_MSGS:]
            app.logger.info("[APP DOC ACK] %s", json.dumps({
                "user_id": user_id,
                "stage": stage,
                "pergunta": pergunta,
            }, ensure_ascii=False))
            followup.track_bot_reply(user_id)
            return jsonify({
                "source": "doc_ack",
                "similaridade": 0.0,
                "resposta": ack,
                "match_index": None,
                "topk": [],
                "etapa": stage,
            }), 200


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

            agora = datetime.now().strftime("%H:%M")
            # histórico
            hist += [
                {"role": "user", "content": pergunta, "hora": agora},
                {"role": "assistant", "content": ans, "hora": agora},
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

            followup.track_bot_reply(user_id)
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
        agora = datetime.now().strftime("%H:%M")
        hist += [
            {"role": "user", "content": pergunta, "hora": agora},
            {"role": "assistant", "content": ans, "hora": agora},
        ]

        SESSIONS[user_id] = hist[-MAX_MSGS:]
        followup.track_bot_reply(user_id)

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

# endpoints de suporte ao followup
@app.get("/debug/followup/<user_id>")
def debug_followup(user_id):
    import followup
    from datetime import datetime, timezone
    
    st = followup._load_state(user_id)
    now = datetime.now(timezone.utc)
    
    # Força housekeeping para atualizar estado
    followup._daily_housekeeping(st, now)
    followup._save_state(st)
    
    # Recalcula após housekeeping
    st = followup._load_state(user_id)
    
    # Cálculos detalhados
    today = now.date()
    local_now = followup._to_local(now)
    local_last_bot = followup._to_local(st.get("last_bot_ts")) if st.get("last_bot_ts") else None
    local_last_user = followup._to_local(st.get("last_user_ts")) if st.get("last_user_ts") else None
    
    # Dias sem resposta
    days_diff = 0
    if local_last_bot:
        days_diff = (local_now.date() - local_last_bot.date()).days
    
    info = {
        "user_id": user_id,
        "timestamp": now.isoformat(),
        "timestamp_local": local_now.isoformat(),
        
        "estado_banco": {
            "days_without_reply": st.get("days_without_reply"),
            "paused": st.get("paused"),
            "goal_reached": st.get("goal_reached"),
            "next_due": st.get("next_due"),
            "attempts_today": st.get("attempts_today"),
            "attempts_total": st.get("attempts_total"),
            "last_bot_ts": st.get("last_bot_ts"),
            "last_user_ts": st.get("last_user_ts"),
            "started_on": st.get("started_on"),
        },
        
        "calculos_detalhados": {
            "dias_diferenca_calculada": days_diff,
            "local_last_bot_date": local_last_bot.date().isoformat() if local_last_bot else None,
            "local_now_date": local_now.date().isoformat(),
            "mesmo_dia": local_last_bot and local_last_bot.date() == local_now.date(),
            "ultimo_bot_local": local_last_bot.isoformat() if local_last_bot else None,
            "ultimo_user_local": (followup._to_local(st["last_user_ts"]).isoformat() if st.get("last_user_ts") else None),
        },
        
        "verificacoes": {
            "in_window": followup._in_window_local(now),
            "window": f"{followup.CFG['window_start_hour']}:00-{followup.CFG['window_end_hour']}:00",
            "day_index": followup._day_index(st, today),
            "allowed_today": followup._allowed_today(st, today),
            "bands_for_day": followup._bands_for_day(st, today),
            "max_total_attempts": followup.CFG["max_total_attempts"],
            "script_index": followup._script_index(st),
            "script_length": len(followup.FOLLOWUP_SCRIPT),
            "eligible": followup._eligible(st, now),
        },
        
        "horarios": {
            "now_utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "now_local": local_now.strftime("%Y-%m-%d %H:%M:%S"),
            "window_start": f"{followup.CFG['window_start_hour']}:00",
            "window_end": f"{followup.CFG['window_end_hour']}:00",
        }
    }
    
    return jsonify(info)

@app.post("/debug/simulate-next-day/<user_id>")
def simulate_next_day(user_id):
    """Simula que passou 1 dia (para testes)"""
    import followup
    from datetime import datetime, timedelta, timezone
    
    st = followup._load_state(user_id)
    
    if st.get("last_bot_ts"):
        # Subtrai 25 horas para garantir que passa 1 dia completo
        new_last_bot_ts = st["last_bot_ts"] - timedelta(hours=25)
        st["last_bot_ts"] = new_last_bot_ts
        
        # Limpa o last_user_ts para simular que usuário não respondeu
        st["last_user_ts"] = None
        
        # Força recálculo
        now = datetime.now(timezone.utc)
        followup._daily_housekeeping(st, now)
        followup._save_state(st)
        
        # Recarrega para ver estado atualizado
        st = followup._load_state(user_id)
        followup._daily_housekeeping(st, now)
        
        return jsonify({
            "status": "success",
            "message": "Simulado 1 dia à frente",
            "estado_atual": {
                "days_without_reply": st.get("days_without_reply"),
                "paused": st.get("paused"),
                "next_due": st.get("next_due"),
                "last_bot_ts": st.get("last_bot_ts"),
                "last_user_ts": st.get("last_user_ts"),
            },
            "verificacoes": {
                "day_index": followup._day_index(st, now.date()),
                "allowed_today": followup._allowed_today(st, now.date()),
                "eligible": followup._eligible(st, now),
            }
        })
    
    return jsonify({"status": "error", "message": "No last_bot_ts found"}), 400

@app.post("/debug/set-state/<user_id>")
def set_state(user_id):
    """Define estado manualmente para testes"""
    import followup
    from datetime import datetime, timedelta, timezone
    
    data = request.get_json() or {}
    
    st = followup._load_state(user_id)
    
    # Campos que podem ser ajustados
    if "days_without_reply" in data:
        st["days_without_reply"] = int(data["days_without_reply"])
    if "paused" in data:
        st["paused"] = bool(data["paused"])
    if "attempts_today" in data:
        st["attempts_today"] = int(data["attempts_today"])
    if "attempts_total" in data:
        st["attempts_total"] = int(data["attempts_total"])
    if "last_bot_ts" in data:
        # Suporta "now", "yesterday", ou timestamp específico
        if data["last_bot_ts"] == "now":
            st["last_bot_ts"] = datetime.now(timezone.utc)
        elif data["last_bot_ts"] == "yesterday":
            st["last_bot_ts"] = datetime.now(timezone.utc) - timedelta(days=1)
    
    followup._save_state(st)
    
    return jsonify({"status": "updated", "state": st})

@app.route("/monitor/followup")
def monitor_followup():
    import followup
    from datetime import datetime, timezone
    
    info = {
        "thread_alive": followup._THREAD and followup._THREAD.is_alive(),
        "sender_configured": followup._SENDER is not None,
        "current_time": datetime.now(timezone.utc).isoformat(),
    }
    
    # Conta usuários em followup
    from db import db_query_all
    rows = db_query_all("SELECT COUNT(*) FROM followup_state WHERE goal_reached = FALSE")
    info["active_users"] = rows[0][0] if rows else 0
    
    return jsonify(info)

@app.post("/debug/trigger-followup/<user_id>")
def trigger_followup(user_id):
    """Força a verificação de elegibilidade e envia repique se possível"""
    import followup
    from datetime import datetime, timedelta, timezone
    
    now = datetime.now(timezone.utc)
    st = followup._load_state(user_id)
    
    # Força housekeeping para atualizar estado
    followup._daily_housekeeping(st, now)
    followup._save_state(st)
    
    # Recarrega estado atualizado
    st = followup._load_state(user_id)
    
    # Verifica elegibilidade com todas as regras
    eligible = followup._eligible(st, now)
    
    if eligible:
        # Prepara mensagem e próximo agendamento
        message, next_due = followup._prepare_followup(st, now)
        
        if message and next_due:
            # Envia mensagem imediatamente
            try:
                followup._SENDER(user_id, message)
                
                # Atualiza estado no banco
                st["attempts_today"] = int(st.get("attempts_today", 0)) + 1
                st["attempts_total"] = int(st.get("attempts_total", 0)) + 1
                st["last_bot_ts"] = now  # Importante para gap mínimo
                st["last_attempt_day"] = now.date()
                st["next_due"] = next_due
                followup._save_state(st)
                
                return jsonify({
                    "status": "success",
                    "message": "Followup enviado com sucesso",
                    "message_content": message,
                    "next_due": next_due.isoformat(),
                    "next_due_local": followup._to_local(next_due).isoformat(),
                    "attempts_today": st["attempts_today"],
                    "attempts_total": st["attempts_total"],
                    "day_index": followup._day_index(st, now.date()),
                    "allowed_today": followup._allowed_today(st, now.date())
                })
            except Exception as e:
                app.logger.error(f"Erro ao enviar followup: {e}", exc_info=True)
                return jsonify({
                    "status": "error", 
                    "message": f"Falha ao enviar mensagem: {str(e)}"
                }), 500
        else:
            return jsonify({
                "status": "not_ready",
                "reason": "prepare_followup retornou None",
                "message": str(message)[:100] if message else None,
                "next_due": next_due.isoformat() if next_due else None
            })
    else:
        # Explica detalhadamente por que não é elegível
        reasons = []
        details = {}
        
        # Verificações básicas
        if st.get("goal_reached"): 
            reasons.append("goal_reached=True")
        details["goal_reached"] = st.get("goal_reached")
        
        if st.get("paused"): 
            reasons.append("paused=True")
        details["paused"] = st.get("paused")
        
        # Janela de tempo
        in_window = followup._in_window_local(now)
        if not in_window: 
            reasons.append("fora_da_janela")
        details["in_window"] = in_window
        
        # Dia do ciclo
        day_index = followup._day_index(st, now.date())
        if day_index <= 0: 
            reasons.append(f"dia_<=_0 (dia={day_index})")
        details["day_index"] = day_index
        
        # Next due
        next_due_val = st.get("next_due")
        details["next_due"] = next_due_val
        if next_due_val is None:
            reasons.append("next_due=None")
        else:
            next_due_dt = followup._coerce_aware(next_due_val)
            if next_due_dt and now < next_due_dt:
                reasons.append(f"agora < next_due ({now.strftime('%H:%M')} < {followup._to_local(next_due_dt).strftime('%H:%M')})")
        
        # Última mensagem do bot
        last_bot_ts = followup._coerce_aware(st.get("last_bot_ts"))
        details["last_bot_ts"] = last_bot_ts
        if last_bot_ts is None:
            reasons.append("last_bot_ts=None")
        
        # Gap mínimo
        min_gap = int(followup.CFG.get("min_gap_minutes", 0))
        if min_gap > 0 and last_bot_ts:
            gap = now - last_bot_ts
            details["gap_minutes"] = gap.total_seconds() / 60
            if gap < timedelta(minutes=min_gap):
                reasons.append(f"gap_minimo_{min_gap}min (gap={gap.total_seconds()/60:.1f}min)")
        
        # Limites de tentativas
        attempts_total = int(st.get("attempts_total", 0))
        details["attempts_total"] = attempts_total
        if attempts_total >= followup.CFG["max_total_attempts"]:
            reasons.append(f"max_attempts ({attempts_total}/{followup.CFG['max_total_attempts']})")
        
        allowed_today = followup._allowed_today(st, now.date())
        attempts_today = int(st.get("attempts_today", 0))
        details["allowed_today"] = allowed_today
        details["attempts_today"] = attempts_today
        if attempts_today >= allowed_today:
            reasons.append(f"limite_diario ({attempts_today}/{allowed_today})")
        
        # Verificação de mesmo dia da última resposta do bot
        if last_bot_ts:
            local_now = followup._to_local(now)
            local_last_bot = followup._to_local(last_bot_ts)
            same_bot_day = local_now.date() == local_last_bot.date()
            details["mesmo_dia_ultimo_bot"] = same_bot_day
            if same_bot_day:
                reasons.append(f"mesmo_dia_ultimo_bot (last_bot={local_last_bot.strftime('%H:%M')})")
        
        # Verificação de usuário respondeu depois do bot
        last_user_ts = followup._coerce_aware(st.get("last_user_ts"))
        details["last_user_ts"] = last_user_ts
        if last_user_ts and last_bot_ts and last_user_ts > last_bot_ts:
            reasons.append("usuario_respondeu_depois")
        
        # Script disponível
        script_idx = followup._script_index(st)
        details["script_index"] = script_idx
        if script_idx >= len(followup.FOLLOWUP_SCRIPT):
            reasons.append(f"script_esgotado ({script_idx}/{len(followup.FOLLOWUP_SCRIPT)})")
        
        started_on = st.get("started_on")
        details["started_on"] = started_on
        if started_on:
            local_now = followup._to_local(now)
            same_started_day = local_now.date() == started_on
            details["mesmo_dia_started"] = same_started_day
            if same_started_day:
                reasons.append(f"mesmo_dia_inicio_ciclo (started={started_on})")
        
        return jsonify({
            "status": "not_eligible",
            "reasons": reasons,
            "details": details,
            "now": now.isoformat(),
            "now_local": followup._to_local(now).isoformat()
        })

@app.post("/debug/reset-next-due/<user_id>")
def reset_next_due(user_id):
    import followup
    st = followup._load_state(user_id)
    st["next_due"] = None
    followup._save_state(st)
    return jsonify({"status": "success", "next_due": "cleared"})

@app.post("/debug/create-test-state/<user_id>")
def create_test_state(user_id):
    """Cria um estado PERFEITO para testes de followup"""
    import followup
    from datetime import datetime, timedelta, timezone
    
    data = request.get_json() or {}
    day = data.get("day", 1)  # Dia do ciclo (1, 2, 3...)
    
    # Data de referência: ontem para simular ciclo começado
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    
    # CONSTRÓI ESTADO CONSISTENTE
    state_data = {
        "user_id": user_id,
        "started_on": yesterday.date(),  # Ciclo começou ONTEM
        "last_bot_ts": yesterday,        # Última resposta do bot foi ONTEM
        "last_user_ts": None,            # Usuário NÃO respondeu desde então
        "days_without_reply": day,       # Força dia específico
        "paused": False if day > 0 else True,
        "goal_reached": False,
        "attempts_today": 0,
        "attempts_total": 0,
        "last_attempt_day": now.date(),
        "next_due": None,
        "name": "Test User",
        "docs": None
    }
    
    # SALVA DIRETO NO BANCO (evita lógicas intermediárias)
    from db import db_execute
    import json
    
    docs_json = json.dumps(state_data["docs"]) if state_data["docs"] else None
    
    # Primeiro, deleta se existir
    db_execute("DELETE FROM followup_state WHERE user_id = %s", (user_id,))
    
    # Insere estado perfeito
    db_execute("""
        INSERT INTO followup_state 
        (user_id, started_on, last_user_ts, last_bot_ts, next_due,
         attempts_today, attempts_total, last_attempt_day,
         days_without_reply, paused, goal_reached, name, docs)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            state_data["user_id"],
            state_data["started_on"],
            state_data["last_user_ts"],
            state_data["last_bot_ts"],
            state_data["next_due"],
            state_data["attempts_today"],
            state_data["attempts_total"],
            state_data["last_attempt_day"],
            state_data["days_without_reply"],
            state_data["paused"],
            state_data["goal_reached"],
            state_data["name"],
            docs_json
        )
    )
    
    # Carrega para verificação
    st = followup._load_state(user_id)
    
    return jsonify({
        "status": "created",
        "day": day,
        "state": st,
        "note": f"Estado criado para Dia {day}. Use /debug/trigger-followup para testar."
    })

# WEBHOOK PARA SERVIÇOS EXTERNOS
bp = Blueprint("whatsapp", __name__)

@bp.before_app_request
def block_browser_access():
    """Bloqueia acesso de navegadores ao webhook do WhatsApp"""
    if request.endpoint == 'whatsapp.incoming':
        # Verifica se é uma requisição do Meta (tem signature header)
        signature = request.headers.get('X-Hub-Signature-256')
        user_agent = request.headers.get('User-Agent', '')
        
        # Se não tem signature E parece ser navegador, bloqueia
        if not signature and any(agent in user_agent for agent in ['Mozilla', 'Chrome', 'Safari', 'Firefox']):
            app.logger.warning(f"Tentativa de acesso via navegador ao webhook: {user_agent}")
            return "Acesso não autorizado", 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
