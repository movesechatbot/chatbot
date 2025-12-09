from __future__ import annotations
import logging, random, threading, time, json
from datetime import datetime, timedelta, date, timezone
from typing import Callable, Dict, Optional, Tuple
from zoneinfo import ZoneInfo
from config import SOCIAL_IG_URL, TIMEZONE
from db import db_query_one, db_query_all, db_execute

# --- CONFIG PRODUÇÃO ---
CFG = {
    "tz": TIMEZONE,
    "window_start_hour": 6,
    "window_end_hour": 24,
    "daily_plan": {1: 3, 2: 3},
    "max_total_attempts": 12,
    "loop_interval_secs": 5,
    "min_gap_minutes": 60,
}

DAY12_SLOTS: list[tuple[int, int]] = [
    (6 * 60, 9 * 60),
    (12 * 60, 15 * 60),
    (19 * 60, 21 * 60 + 30),
]

LATE_BANDS: list[tuple[int, int]] = [
    (6 * 60, 24 * 60),
]

FOLLOWUP_SCRIPT = [
    "Vi que você ainda não conseguiu me responder.\n\nFica tranquilo(a), estou por aqui para te ajudar e entendo que o dia a dia é corrido.\n\nQual melhor horário para conversarmos aqui?",
    "Olá!, só reforçando: meu objetivo é facilitar ao máximo para você 🏡.\nSe puder me informar a cidade onde mora e onde trabalha, já consigo saber se tenho opções para você",
    "Você já tem imóvel em vista ou está começando a olhar agora?",
    "Tudo bem!?, estou encerrando meu dia por aqui, mas deixei teu nome no topo da minha agenda pra te responder assim que você me der um retorno 😊.\nTe desejo uma ótima noite e sigo à disposição pra te ajudar",
    "Bom dia !, estou começando meu expediente, vi que você não me respondeu ainda..\nAssim que puder me dar um sinal, já seguimos com os próximos passos",
    "Você procura imóvel para morar ou para investir?",
    "Passando aqui rapidinho pra dizer que sigo à disposição!\nMesmo que o teu momento ainda não seja de compra posso te ajudar a entender as possibilidades do mercado e te ajudar a planejar os próximos passos.",
    "Você já chegou a conversar com o banco sobre financiamento ou prefere que eu te ajude a entender essa parte?\nPosso conseguir algo até 100% parcelado para você",
    "Vou aproveitar pra te mandar meu Instagram 👉 [link perfil]\nLá posto diariamente dicas, explicações sobre financiamento e oportunidades de imóveis. Vale a pena seguir para já ir se preparando 🏡✨",
    "Oi!, que tal reservar só 5 minutinhos hoje para falarmos? Pode fazer muita diferença no seu planejamento, não precisa decidir nada agora, mas entendo que ao entrar no anúncio você tenha interesse de dar esse passo a frente e entender mais como pode adquirir seu imóvel próprio",
    "[Nome cliente] ???",
    "[Nome cliente] eu errei em alguma coisa contigo? Pode ser sincero comigo..\nEstou tentando falar contigo sobre o teu projeto de ter um imóvel próprio, 100% parcelado, sem precisar de entrada, mas eu estou ficando sempre sem resposta.\nGostaria que tu fosse sincero comigo, se tem alguma coisa atrapalhando, até pra eu estar melhorando meu trabalho e meu atendimento por aqui",
]

DOC_KEYS = ("rg_cnh", "residencia", "renda", "email")
DOC_LABELS = {
    "rg_cnh": "RG ou CNH",
    "residencia": "comprovante de residencia",
    "renda": "comprovante de renda",
    "email": "email",
}

State = Dict[str, object]

_SENDER: Optional[Callable[[str, str], None]] = None
_THREAD: Optional[threading.Thread] = None
_LOGGER = logging.getLogger("followup")

# -------- helpers de tempo --------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _tz() -> ZoneInfo:
    try:
        return ZoneInfo(CFG["tz"])
    except Exception:
        return ZoneInfo("UTC")

def _to_local(dt_utc: datetime) -> datetime:
    return dt_utc.astimezone(_tz())

def _to_utc(dt_local: datetime) -> datetime:
    return dt_local.astimezone(timezone.utc)

def _in_window_local(now_utc: datetime) -> bool:
    loc = _to_local(now_utc)
    start, end = int(CFG["window_start_hour"]), int(CFG["window_end_hour"])
    h = loc.hour
    return (h >= start) and (h < end)

def _rand_time_in_band(base_day_local: date, band: tuple[int, int]) -> datetime:
    start_min, end_min = band
    if end_min <= start_min:
        minute_of_day = start_min
    else:
        minute_of_day = random.randint(start_min, end_min - 1)
    hour = minute_of_day // 60
    minute = minute_of_day % 60
    second = random.randint(0, 59)
    dt_local = datetime(
        base_day_local.year,
        base_day_local.month,
        base_day_local.day,
        hour,
        minute,
        second,
        tzinfo=_tz(),
    )
    return _to_utc(dt_local)

# -------- persistência em postgres --------
def _row_to_state(row):
    (
        user_id,
        started_on,
        last_user_ts,
        last_bot_ts,
        next_due,
        attempts_today,
        attempts_total,
        last_attempt_day,
        days_without_reply,
        paused,
        goal_reached,
        name,
        docs_raw,
    ) = row

    today = _utcnow().date()
    docs = None
    if isinstance(docs_raw, str) and docs_raw.strip():
        try:
            docs = json.loads(docs_raw)
        except Exception:
            docs = None

    st: State = {
        "user_id": user_id,
        "started_on": started_on or today,
        "last_user_ts": last_user_ts,
        "last_bot_ts": last_bot_ts,
        "next_due": next_due,
        "attempts_today": int(attempts_today or 0),
        "attempts_total": int(attempts_total or 0),
        "last_attempt_day": last_attempt_day,
        "days_without_reply": int(days_without_reply or 0),
        "paused": bool(paused),
        "goal_reached": bool(goal_reached),
        "name": (name or "").strip(),
        "docs": docs,
        "_last_day_check": today,
        "_last_band_idx": None,
    }
    return st

def _load_state(user_id: str) -> State:
    row = db_query_one(
        """
        SELECT user_id, started_on, last_user_ts, last_bot_ts, next_due,
               attempts_today, attempts_total, last_attempt_day,
               days_without_reply, paused, goal_reached, name, docs
          FROM followup_state
         WHERE user_id = %s
        """,
        (user_id,),
    )
    if row:
        return _row_to_state(row)

    # se não existe, cria
    today = _utcnow().date()
    db_execute(
        """
        INSERT INTO followup_state (
            user_id, started_on, attempts_today, attempts_total,
            days_without_reply, paused, goal_reached, next_due
        ) VALUES (%s, %s, 0, 0, 0, TRUE, FALSE, NULL)
        """,
        (user_id, today),
    )
    st: State = {
        "user_id": user_id,
        "started_on": today,
        "last_user_ts": None,
        "last_bot_ts": None,
        "next_due": None,
        "attempts_today": 0,
        "attempts_total": 0,
        "last_attempt_day": None,
        "days_without_reply": 0,
        "paused": True,
        "goal_reached": False,
        "name": "",
        "docs": None,
        "_last_day_check": today,
        "_last_band_idx": None,
    }
    return st

def _save_state(st: State) -> None:
    docs_json = None
    if isinstance(st.get("docs"), dict):
        docs_json = json.dumps(st["docs"], ensure_ascii=False)

    db_execute(
        """
        UPDATE followup_state
           SET started_on = %s,
               last_user_ts = %s,
               last_bot_ts = %s,
               next_due = %s,
               attempts_today = %s,
               attempts_total = %s,
               last_attempt_day = %s,
               days_without_reply = %s,
               paused = %s,
               goal_reached = %s,
               name = %s,
               docs = %s
         WHERE user_id = %s
        """,
        (
            st.get("started_on"),
            st.get("last_user_ts"),
            st.get("last_bot_ts"),
            st.get("next_due"),
            int(st.get("attempts_today", 0)),
            int(st.get("attempts_total", 0)),
            st.get("last_attempt_day"),
            int(st.get("days_without_reply", 0)),
            bool(st.get("paused", False)),
            bool(st.get("goal_reached", False)),
            (st.get("name") or "").strip(),
            docs_json,
            st.get("user_id"),
        ),
    )

# -------- lógica de dias / plano --------
def _day_index(st: State, today: date) -> int:
    return max(0, int(st.get("days_without_reply", 0)))

def _allowed_today(st: State, today: date) -> int:
    d = _day_index(st, today)
    if d <= 0:
        return 0
    if d in (1, 2):
        return 3
    return 1

def _script_index(st: State) -> int:
    return min(int(st.get("attempts_total", 0)), len(FOLLOWUP_SCRIPT) - 1)

def _bands_for_day(st: State, today: date) -> list[tuple[int, int]]:
    d = _day_index(st, today)
    
    # === LOG CRÍTICO 1 ===
    _LOGGER.info(f"[DEBUG-BANDS] User {st.get('user_id')}: Dia={d}, st[days_without_reply]={st.get('days_without_reply')}")
    
    if d in (1, 2):
        _LOGGER.info(f"[DEBUG-BANDS] Retornando DAY12_SLOTS: {DAY12_SLOTS}")
        return DAY12_SLOTS
    
    _LOGGER.info(f"[DEBUG-BANDS] Retornando LATE_BANDS: {LATE_BANDS}")
    return LATE_BANDS

def _pick_band(st: State, bands: list[tuple[int, int]]) -> tuple[int, int]:
    if not bands:
        return (6 * 60, 22 * 60)
    last_idx = st.get("_last_band_idx")
    idx = random.randrange(len(bands))
    if last_idx is not None and len(bands) > 1 and idx == last_idx:
        idx = (idx + 1) % len(bands)
    st["_last_band_idx"] = idx
    return bands[idx]

# -------- api pública --------
def init(sender_fn: Callable[[str, str], None]) -> None:
    global _SENDER, _THREAD
    if _SENDER is None:
        _SENDER = sender_fn
    if _THREAD is None:
        _THREAD = threading.Thread(
            target=_loop,
            name="followup-loop",
            daemon=True,
        )
        _THREAD.start()

def mark_user_reply(user_id: str) -> None:
    """Usuário respondeu. Reinicia tudo."""
    now = _utcnow()
    st = _load_state(user_id)
    
    st["last_user_ts"] = now
    st["started_on"] = now.date()    # ⬅️ RESETA A DATA DO CICLO
    st["paused"] = True
    st["next_due"] = None
    st["attempts_today"] = 0
    st["last_attempt_day"] = now.date()
    st["days_without_reply"] = 0
    
    _save_state(st)

def track_bot_reply(user_id: str) -> None:
    """Bot respondeu (resposta normal, NÃO repique)"""
    now = _utcnow()
    local_now = _to_local(now)
    
    st = _load_state(user_id)
    
    # Atualiza last_bot_ts (para gap mínimo)
    st["last_bot_ts"] = now
    
    # RESETA para novo ciclo
    st["started_on"] = local_now.date()  # Data LOCAL
    st["days_without_reply"] = 0
    st["paused"] = True
    st["next_due"] = None
    st["attempts_today"] = 0
    st["last_attempt_day"] = local_now.date()
    
    if st.get("goal_reached"):
        st["paused"] = True
        st["next_due"] = None
    
    _save_state(st)

def mark_goal(user_id: str, reached: bool = True) -> None:
    st = _load_state(user_id)
    st["goal_reached"] = bool(reached)
    if reached:
        st["paused"] = True
        st["next_due"] = None
    _save_state(st)

def update_docs_status(user_id: str, info: Dict[str, object]) -> None:
    normalized = {key: bool(info.get(key)) for key in DOC_KEYS}
    st = _load_state(user_id)
    st["docs"] = normalized
    all_done = all(normalized.get(k) for k in DOC_KEYS)
    if all_done:
        st["goal_reached"] = True
        st["paused"] = True
        st["next_due"] = None
    _save_state(st)

def update_profile(user_id: str, name: Optional[str] = None) -> None:
    if not name:
        return
    st = _load_state(user_id)
    st["name"] = (name or "").strip()
    _save_state(st)

# -------- núcleo do scheduler --------
def _eligible(st: State, now: datetime) -> bool:
    # 1. Verificações básicas de estado
    if st.get("goal_reached"):
        return False
    if st.get("paused"):
        return False
    if st.get("_sending"):
        return False
    
    # 2. Janela global de envio (06:00-24:00 local)
    if not _in_window_local(now):
        return False
    
    # 3. Verificação de dia (deve ser dia 1 ou mais)
    today = now.date()
    d = _day_index(st, today)
    
    # Dia 0 → nunca manda followup
    if d <= 0:
        return False
    
    # 4. Verifica se há um next_due agendado e se já chegou a hora
    next_due = _coerce_aware(st.get("next_due"))
    if next_due is None or now < next_due:
        return False
    
    # 5. Verifica se a última mensagem do bot existe
    last_bot_ts = _coerce_aware(st.get("last_bot_ts"))
    if last_bot_ts is None:
        return False
    
    # 6. Gap mínimo desde a última resposta do bot
    min_gap = int(CFG.get("min_gap_minutes", 0))
    if min_gap > 0:
        gap = now - last_bot_ts
        if gap < timedelta(minutes=min_gap):
            return False
    
    # 7. Teto total de repiques (máximo 12)
    if int(st.get("attempts_total", 0)) >= CFG["max_total_attempts"]:
        return False
    
    # 8. Limite diário de repiques
    allowed = _allowed_today(st, today)
    if int(st.get("attempts_today", 0)) >= allowed:
        return False
    
    # 9. Se o usuário respondeu depois da última mensagem do bot, não repica
    last_user_ts = _coerce_aware(st.get("last_user_ts"))
    if isinstance(last_user_ts, datetime) and last_user_ts > last_bot_ts:
        return False
    
    # 10. VERIFICAÇÃO CORRIGIDA: Baseada no início do ciclo (SEM converter started_on)
    started_on = st.get("started_on")
    if started_on:
        local_now = _to_local(now)
        # started_on já é um objeto date (do banco), compare diretamente
        if local_now.date() == started_on:
            # Ainda é o dia 0 (mesmo dia que o ciclo começou)
            return False
    
    # 11. Verifica se o script ainda tem mensagens disponíveis
    script_idx = _script_index(st)
    if script_idx >= len(FOLLOWUP_SCRIPT):
        return False
    
    # TODAS as condições atendidas → usuário elegível para repique
    return True

def _loop() -> None:
    _LOGGER.info("Followup loop started")
    while True:
        try:
            time.sleep(CFG["loop_interval_secs"])
            now = _utcnow()
            due: list[Tuple[str, str, datetime, State]] = []

            # CORREÇÃO: Esta é a linha que estava com erro - precisa da string SQL completa
            rows = db_query_all(
                """
                SELECT user_id, started_on, last_user_ts, last_bot_ts, next_due,
                       attempts_today, attempts_total, last_attempt_day,
                       days_without_reply, paused, goal_reached, name, docs
                  FROM followup_state
                 WHERE goal_reached = FALSE
                """
            )

            _LOGGER.debug(f"Processing {len(rows)} users in followup loop")

            for row in rows:
                try:
                    st = _row_to_state(row)
                    _daily_housekeeping(st, now)
                    if not _eligible(st, now):
                        _save_state(st)
                        continue
                    message, next_due = _prepare_followup(st, now)
                    if not message or not next_due:
                        _save_state(st)
                        continue
                    next_due = _coerce_aware(next_due)
                    if not next_due:
                        _save_state(st)
                        continue

                    st["_pending_next_due"] = next_due
                    st["_pending_attempts_today"] = int(st["attempts_today"]) + 1
                    st["_pending_attempts_total"] = int(st["attempts_total"]) + 1
                    due.append((st["user_id"], message, next_due, st))
                except Exception as e:
                    _LOGGER.error(f"Error processing user {row[0] if row else 'unknown'}: {e}", exc_info=True)

            for user_id, message, next_due, st in due:
                try:
                    _deliver_followup(user_id, message, next_due, st)
                except Exception as e:
                    _LOGGER.error(f"Error delivering followup to {user_id}: {e}", exc_info=True)

        except Exception as e:
            _LOGGER.error(f"Critical error in followup loop: {e}", exc_info=True)
            time.sleep(60)

def _pick_next_day(now_utc: datetime, bands: list[tuple[int, int]], st: State) -> datetime:
    local_now = _to_local(now_utc)
    tomorrow = local_now.date() + timedelta(days=1)
    band = _pick_band(st, bands)
    return _rand_time_in_band(tomorrow, band)

def _pick_future_today(now_utc: datetime, bands: list[tuple[int, int]], st: State) -> datetime:
    local_now = _to_local(now_utc)
    today = local_now.date()
    for _ in range(8):
        band = _pick_band(st, bands)
        cand = _rand_time_in_band(today, band)
        if cand > now_utc and _in_window_local(cand):
            return cand
    return _pick_next_day(now_utc, bands, st)

def _prepare_followup(st: State, now: datetime) -> Tuple[Optional[str], Optional[datetime]]:
    """Prepara a mensagem e o horário do próximo repique."""
    
    # === LOG INICIAL CRÍTICO ===
    _LOGGER.info(f"[PREPARE] INICIANDO para user {st.get('user_id')}")
    _LOGGER.info(f"[PREPARE] Estado base: days_without_reply={st.get('days_without_reply')}, attempts_today={st.get('attempts_today')}, attempts_total={st.get('attempts_total')}")
    
    today = now.date()
    
    # 1. Verificação de dia e limites
    day = _day_index(st, today)
    allowed = _allowed_today(st, today)
    
    _LOGGER.info(f"[PREPARE] Cálculos: day_index={day}, allowed_today={allowed}")
    
    if allowed <= 0:
        _LOGGER.info(f"[PREPARE] REJEITADO: allowed_today={allowed} (dia 0 ou limite diário)")
        return None, None
    
    if int(st.get("attempts_today", 0)) >= allowed:
        _LOGGER.info(f"[PREPARE] REJEITADO: attempts_today ({st.get('attempts_today')}) >= allowed ({allowed})")
        return None, None
    
    if int(st.get("attempts_total", 0)) >= CFG["max_total_attempts"]:
        _LOGGER.info(f"[PREPARE] REJEITADO: attempts_total ({st.get('attempts_total')}) >= max ({CFG['max_total_attempts']})")
        return None, None
    
    # 2. Obter mensagem do script
    script_idx = _script_index(st)
    if script_idx >= len(FOLLOWUP_SCRIPT):
        _LOGGER.info(f"[PREPARE] REJEITADO: script_idx ({script_idx}) >= script_len ({len(FOLLOWUP_SCRIPT)})")
        return None, None
    
    base_msg = FOLLOWUP_SCRIPT[script_idx]
    message = _compose_followup_message(st, base_msg)
    
    # === LOG DE SLOTS DETALHADO ===
    _LOGGER.info(f"[SLOT-LOGIC] ========== LÓGICA DE SLOTS ==========")
    _LOGGER.info(f"[SLOT-LOGIC] Dia atual do ciclo: {day}")
    _LOGGER.info(f"[SLOT-LOGIC] Tentativas HOJE: {st.get('attempts_today')}")
    _LOGGER.info(f"[SLOT-LOGIC] Total tentativas: {st.get('attempts_total')}")
    
    # 3. Lógica de agendamento baseada no dia
    if day in (1, 2):
        # DIAS 1 e 2: 3 slots fixos (manhã, tarde, noite)
        slots = DAY12_SLOTS
        attempts_today = int(st.get("attempts_today", 0))
        
        _LOGGER.info(f"[SLOT-LOGIC] Usando DAY12_SLOTS: {slots}")
        _LOGGER.info(f"[SLOT-LOGIC] Índice do slot baseado em attempts_today: {attempts_today}")
        
        # Segurança: se tentou mais slots que disponíveis hoje
        if attempts_today >= len(slots):
            _LOGGER.info(f"[SLOT-LOGIC] REJEITADO: attempts_today ({attempts_today}) >= slots disponíveis ({len(slots)})")
            return None, None
        
        # Pega o slot correspondente à tentativa atual
        # attempts_today=0 → slot 0 (manhã)
        # attempts_today=1 → slot 1 (tarde)  
        # attempts_today=2 → slot 2 (noite)
        band = slots[attempts_today]
        _LOGGER.info(f"[SLOT-LOGIC] Slot selecionado (índice {attempts_today}): {band}")
        
        # Converte band para horário legível
        start_hour = band[0] // 60
        start_min = band[0] % 60
        end_hour = band[1] // 60
        end_min = band[1] % 60
        _LOGGER.info(f"[SLOT-LOGIC] Janela do slot: {start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d}")
        
        # Gera horário aleatório dentro do slot
        candidate = _rand_time_in_band(today, band)
        local_candidate = _to_local(candidate)
        
        _LOGGER.info(f"[SLOT-LOGIC] Horário gerado: {candidate} (local: {local_candidate})")
        
        # Verifica se horário já passou
        if candidate < now:
            _LOGGER.info(f"[SLOT-LOGIC] AVISO: Horário gerado já passou ({candidate} < {now})")
            
            # Tenta próximo slot do mesmo dia
            next_slot_idx = attempts_today + 1
            if next_slot_idx < len(slots):
                next_band = slots[next_slot_idx]
                candidate = _rand_time_in_band(today, next_band)
                _LOGGER.info(f"[SLOT-LOGIC] Usando próximo slot (índice {next_slot_idx}): {next_band}")
                _LOGGER.info(f"[SLOT-LOGIC] Novo horário: {candidate}")
            else:
                # Não tem mais slots hoje, agenda para amanhã no primeiro slot
                bands = _bands_for_day(st, today)
                candidate = _pick_next_day(now, bands, st)
                _LOGGER.info(f"[SLOT-LOGIC] Último slot do dia usado, agendando para AMANHÃ: {candidate}")
        
        next_due = candidate
        
    else:
        # DIA 3+: 1 repique por dia na faixa ampla
        bands = LATE_BANDS
        attempts_today = int(st.get("attempts_today", 0))
        
        _LOGGER.info(f"[SLOT-LOGIC] Usando LATE_BANDS: {bands}")
        _LOGGER.info(f"[SLOT-LOGIC] Dia {day}: 1 repique/dia na faixa 06:00-24:00")
        
        if attempts_today == 0:
            # Primeiro repique do dia
            next_due = _pick_future_today(now, bands, st)
            _LOGGER.info(f"[SLOT-LOGIC] Primeiro repique do dia, agendando para HOJE: {next_due}")
        else:
            # Já fez repique hoje, agenda para amanhã
            next_due = _pick_next_day(now, bands, st)
            _LOGGER.info(f"[SLOT-LOGIC] Já fez repique hoje ({attempts_today}), agendando para AMANHÃ: {next_due}")
    
    # 4. Log final
    local_next_due = _to_local(next_due)
    _LOGGER.info(f"[PREPARE] FINALIZADO: message_len={len(message)}, next_due={next_due} (local: {local_next_due})")
    _LOGGER.info(f"[PREPARE] Próximo repique agendado para: {local_next_due.strftime('%H:%M')}")
    
    return message, next_due

def _deliver_followup(user_id: str, message: str, next_due: datetime, st: State) -> None:
    """Envia o repique e atualiza o estado no banco."""
    if _SENDER is None:
        _LOGGER.warning("followup sender not configured; skipping message to %s", user_id)
        return

    try:
        _SENDER(user_id, message)
        _LOGGER.info(f"[DELIVER] Repique enviado para {user_id}: {message[:50]}...")
    except Exception as exc:
        _LOGGER.error(f"followup send failed for {user_id}: {exc}")
        return

    now = _utcnow()
    today = now.date()

    # Usa os valores pendentes se existirem
    scheduled_due = st.get("_pending_next_due", next_due)
    if scheduled_due:
        scheduled_due = _coerce_aware(scheduled_due)
    
    # Atualiza contadores
    st["attempts_today"] = int(st.get("_pending_attempts_today", st.get("attempts_today", 0)))
    st["attempts_total"] = int(st.get("_pending_attempts_total", st.get("attempts_total", 0)))
    
    # IMPORTANTE: NÃO atualiza last_bot_ts (para não afetar cálculo de dias)
    # st["last_bot_ts"] = now  # ← NÃO FAÇA ISSO
    
    st["last_attempt_day"] = today
    st["next_due"] = scheduled_due
    st["_last_day_check"] = today

    # Limpa pendências
    st.pop("_pending_next_due", None)
    st.pop("_pending_attempts_today", None)
    st.pop("_pending_attempts_total", None)

    _save_state(st)
    
    _LOGGER.info(f"[DELIVER] Estado atualizado: attempts_today={st['attempts_today']}, attempts_total={st['attempts_total']}, next_due={st['next_due']}")

def _daily_housekeeping(st: State, now: datetime) -> None:
    """
    Atualiza estado diário: reset de contadores, cálculo de dias, e agendamento.
    """
    
    # === LOG DE ENTRADA ===
    _LOGGER.info(f"[HOUSE-ENTRY] User {st.get('user_id')}")
    _LOGGER.info(f"  Estado inicial: days={st.get('days_without_reply')}, attempts_today={st.get('attempts_today')}, next_due={st.get('next_due')}")
    
    # 1. CONVERTE PARA HORÁRIO LOCAL (CRÍTICO)
    local_now = _to_local(now)
    today_local = local_now.date()
    
    # 2. RESET DIÁRIO usando data LOCAL
    last_attempt_day = st.get("last_attempt_day")
    
    if last_attempt_day is None or today_local > last_attempt_day:
        # NOVO DIA - reseta contador diário
        old_attempts = st.get("attempts_today", 0)
        st["attempts_today"] = 0
        st["last_attempt_day"] = today_local
        _LOGGER.info(f"[RESET-DIARIO] Novo dia {today_local}. Reset: {old_attempts} → 0")
    
    # 3. CÁLCULO DE DIAS SEM RESPOSTA (usando datas LOCAIS)
    started_on = st.get("started_on")
    
    if started_on is None:
        started_on = today_local
        st["started_on"] = started_on
    
    # Garante que started_on é um date (não datetime)
    if isinstance(started_on, datetime):
        started_date = _to_local(started_on).date()
    else:
        started_date = started_on  # Já é date
    
    # Diferença em dias LOCAIS
    days_diff = (today_local - started_date).days
    st["days_without_reply"] = max(0, days_diff)
    
    # Log do cálculo
    _LOGGER.info(f"[DAY-CALC] started={started_date}, today={today_local}, diff={days_diff} dias")
    
    # 4. ATUALIZA PAUSED baseado no dia e estado
    if st["days_without_reply"] > 0 and not st.get("goal_reached"):
        st["paused"] = False
        _LOGGER.info(f"[PAUSE] Dia {st['days_without_reply']} ativo, despausado")
    else:
        st["paused"] = True
        _LOGGER.info(f"[PAUSE] Dia {st['days_without_reply']} inativo, pausado")
    
    # 5. BLOQUEIO CRÍTICO: SE DIA 1 OU 2 JÁ COMPLETO, NÃO AGENDA MAIS
    d = st["days_without_reply"]
    allowed = _allowed_today(st, today_local)
    attempts_today = int(st.get("attempts_today", 0))
    
    if d in (1, 2) and attempts_today >= allowed:
        # DIA 1 ou 2 COMPLETO - NÃO agenda mais hoje
        st["next_due"] = None
        _LOGGER.info(f"[BLOCK] Dia {d} completo: {attempts_today}/{allowed}. Bloqueando agendamento.")
        return  # ⬅️ SAI SEM AGENDAR
    
    # 6. SE JÁ TEM next_due E ainda é válido, mantém
    next_due = _coerce_aware(st.get("next_due"))
    if next_due and next_due > now and _in_window_local(next_due):
        _LOGGER.info(f"[KEEP] Next_due já válido: {next_due}")
        return
    
    # 7. SE PRECISA DE NOVO AGENDAMENTO (apenas se ativo e sem goal)
    if (st["days_without_reply"] > 0 and 
        not st.get("paused") and 
        not st.get("goal_reached") and
        st.get("next_due") is None):
        
        _LOGGER.info(f"[SCHEDULE-NEEDED] Preparando novo agendamento para Dia {d}")
        
        # DIA 1 ou 2: usa slots específicos
        if d in (1, 2):
            bands = DAY12_SLOTS
            attempts_today = int(st.get("attempts_today", 0))
            
            _LOGGER.info(f"[SLOT-CHOICE] Dia {d}, attempts_today={attempts_today}, slots={len(bands)}")
            
            # Segurança: não excede slots disponíveis
            if attempts_today >= len(bands):
                # Já usou todos slots hoje, agenda para amanhã
                st["next_due"] = _pick_next_day(now, bands, st)
                _LOGGER.info(f"[SLOT-EXHAUSTED] Todos slots usados, agenda amanhã: {st['next_due']}")
            else:
                # Pega slot correspondente à tentativa atual
                band = bands[attempts_today]
                
                # Converte band para horário legível (para logs)
                start_hour = band[0] // 60
                start_min = band[0] % 60
                end_hour = band[1] // 60
                end_min = band[1] % 60
                
                _LOGGER.info(f"[SLOT-SELECTED] Slot {attempts_today}: {start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}")
                
                # Tenta agendar neste slot HOJE
                candidate = _rand_time_in_band(today_local, band)
                
                # Se horário já passou, tenta próximo slot
                if candidate < now:
                    next_slot_idx = attempts_today + 1
                    if next_slot_idx < len(bands):
                        # Tenta próximo slot do mesmo dia
                        band = bands[next_slot_idx]
                        candidate = _rand_time_in_band(today_local, band)
                        _LOGGER.info(f"[SLOT-NEXT] Slot {attempts_today} passou, usando slot {next_slot_idx}")
                    else:
                        # Último slot já passou, agenda para amanhã
                        candidate = _pick_next_day(now, bands, st)
                        _LOGGER.info(f"[SLOT-LAST] Último slot passou, agenda amanhã")
                
                st["next_due"] = candidate
        
        # DIA 3+: 1 repique/dia na faixa ampla
        else:
            bands = LATE_BANDS
            
            if attempts_today == 0:
                # Primeiro repique do dia - agenda para hoje
                candidate = _pick_future_today(now, bands, st)
                _LOGGER.info(f"[LATE-FIRST] Primeiro repique do Dia {d}, agenda hoje")
            else:
                # Já fez repique hoje - agenda para amanhã
                candidate = _pick_next_day(now, bands, st)
                _LOGGER.info(f"[LATE-NEXT] Já fez {attempts_today} repique(s) hoje, agenda amanhã")
            
            st["next_due"] = candidate
        
        # Log do agendamento final
        if st["next_due"]:
            local_next = _to_local(st["next_due"])
            _LOGGER.info(f"[SCHEDULED] Novo next_due: {st['next_due']} (local: {local_next})")
    
    # 8. AJUSTE FINAL: se next_due cair fora da janela, recalcula
    next_due = _coerce_aware(st.get("next_due"))
    if next_due and not _in_window_local(next_due):
        _LOGGER.info(f"[WINDOW-FIX] Next_due {next_due} fora da janela, recalculando")
        
        d = st["days_without_reply"]
        bands = DAY12_SLOTS if d in (1, 2) else LATE_BANDS
        
        candidate = _pick_future_today(now, bands, st)
        if candidate <= now:
            candidate = _pick_next_day(now, bands, st)
        
        st["next_due"] = candidate
        _LOGGER.info(f"[WINDOW-FIXED] Novo: {st['next_due']}")
    
    # === LOG DE SAÍDA ===
    _LOGGER.info(f"[HOUSE-EXIT] User {st.get('user_id')}: days={st.get('days_without_reply')}, attempts_today={st.get('attempts_today')}, next_due={st.get('next_due')}")

def _compose_followup_message(st: State, base_script: str) -> str:
    docs = st.get("docs") if isinstance(st.get("docs"), dict) else None
    prefix = ""
    if docs:
        missing = [DOC_LABELS[k] for k in DOC_KEYS if not docs.get(k)]
        received = [DOC_LABELS[k] for k in DOC_KEYS if docs.get(k)]
        if received and missing:
            prefix = f"Recebi {_format_list(received)}. Ainda falta: {_format_list(missing)}.\n\n"
        elif missing and not received:
            prefix = ""
        elif received and not missing:
            prefix = "Recebi toda a documentação. Obrigado!\n\n"

    name = (st.get("name") or "").strip()
    ig = (SOCIAL_IG_URL or "").strip()

    msg = base_script.replace("[Nome cliente]", name or "").replace("[link perfil]", ig or "")

    full = f"{prefix}{msg}".strip()
    return full

def _format_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " e " + items[-1]

def _coerce_aware(value: object) -> Optional[datetime]:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None