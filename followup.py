from __future__ import annotations
import logging, random, threading, time
from datetime import datetime, timedelta, date, timezone
from typing import Callable, Dict, Optional, Tuple
from zoneinfo import ZoneInfo
from config import SOCIAL_IG_URL, TIMEZONE 

# --- CONFIG NOVA ---
CFG = {
    # janela de envio (hora local)
    "tz": TIMEZONE,                 # ex: "America/Sao_Paulo"
    "window_start_hour": 8,         # 08:00
    "window_end_hour": 24,          # 00:00 (do mesmo dia)
    # plano de tentativas
    "daily_plan": {1: 3, 2: 3},     # dias 1 e 2: 3 tentativas; demais: 1/dia
    "max_total_attempts": 12,       # teto absoluto
    # agendamento
    "loop_interval_secs": 5,
}

# faixas de horário locais para distribuição (hora inteira)
# dias com 3 tentativas → manhã, tarde, noite
THREE_SLOTS = [(9, 11), (14, 16), (19, 21)]
# dias com 1 tentativa → janela ampla “business”
ONE_SLOT = [(9, 20)]

# sequência fixa (12) com placeholders
FOLLOWUP_SCRIPT = [
    # 1
    "Vi que você ainda não conseguiu me responder.\n\nFica tranquilo(a), estou por aqui para te ajudar e entendo que o dia a dia é corrido.\n\nQual melhor horário para conversarmos aqui?",
    # 2
    "Olá!, só reforçando: meu objetivo é facilitar ao máximo para você 🏡.\nSe puder me informar a cidade onde mora e onde trabalha, já consigo saber se tenho opções para você",
    # 3
    "Você já tem imóvel em vista ou está começando a olhar agora?",
    # 4
    "Tudo bem!?, estou encerrando meu dia por aqui, mas deixei teu nome no topo da minha agenda pra te responder assim que você me der um retorno 😊.\nTe desejo uma ótima noite e sigo à disposição pra te ajudar",
    # 5
    "Bom dia !, estou começando meu expediente, vi que você não me respondeu ainda..\nAssim que puder me dar um sinal, já seguimos com os próximos passos",
    # 6
    "Você procura imóvel para morar ou para investir?",
    # 7
    "Passando aqui rapidinho pra dizer que sigo à disposição!\nMesmo que o teu momento ainda não seja de compra posso te ajudar a entender as possibilidades do mercado e te ajudar a planejar os próximos passos.",
    # 8
    "Você já chegou a conversar com o banco sobre financiamento ou prefere que eu te ajude a entender essa parte?\nPosso conseguir algo até 100% parcelado para você",
    # 9
    "Vou aproveitar pra te mandar meu Instagram 👉 [link perfil]\nLá posto diariamente dicas, explicações sobre financiamento e oportunidades de imóveis. Vale a pena seguir para já ir se preparando 🏡✨",
    # 10
    "Oi!, que tal reservar só 5 minutinhos hoje para falarmos? Pode fazer muita diferença no seu planejamento, não precisa decidir nada agora, mas entendo que ao entrar no anúncio você tenha interesse de dar esse passo a frente e entender mais como pode adquirir seu imóvel próprio",
    # 11
    "[Nome cliente] ???",
    # 12
    "[Nome cliente] eu errei em alguma coisa contigo? Pode ser sincero comigo..\nEstou tentando falar contigo sobre o teu projeto de ter um imóvel próprio, 100% parcelado, sem precisar de entrada, mas eu estou ficando sempre sem resposta.\nGostaria que tu fosse sincero comigo, se tem alguma coisa atrapalhando, até pra eu estar melhorando meu trabalho e meu atendimento por aqui",
]

DOC_KEYS = ("rg_cnh", "residencia", "renda", "email")
DOC_LABELS = {
    "rg_cnh": "RG ou CNH",
    "residencia": "comprovante de residencia",
    "renda": "comprovante de renda",
    "email": "email",
}
DEFAULT_NO_DOC_MSG = (
    "Vi que você ainda não conseguiu me responder. Fica tranquilo(a), estou por aqui para te ajudar e entendo que o dia a dia é corrido.",
    "Estou aqui para ajudar com a documentação necessária."
)


State = Dict[str, object]

_STATE: Dict[str, State] = {}
_LOCK = threading.RLock()
_SENDER: Optional[Callable[[str, str], None]] = None
_THREAD: Optional[threading.Thread] = None

_LOGGER = logging.getLogger("followup")


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
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
    # janela [start, end). se end=24, aceita até 23:59
    return (h >= start) and (h < end)

def _rand_time_in_band(base_day_local: date, band: tuple[int,int]) -> datetime:
    h0, h1 = band
    hour = random.randint(h0, h1)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    dt_local = datetime(base_day_local.year, base_day_local.month, base_day_local.day, hour, minute, second, tzinfo=_tz())
    return _to_utc(dt_local)

def _day_index(st: State, today: date) -> int:
    start = st.get("started_on") or today
    return max(1, (today - start).days + 1)

def _allowed_today(st: State, today: date) -> int:
    d = _day_index(st, today)
    plan = CFG["daily_plan"]
    return plan.get(d, 1)

def _script_index(st: State) -> int:
    # 0-based para FOLLOWUP_SCRIPT
    return min(int(st.get("attempts_total", 0)), len(FOLLOWUP_SCRIPT) - 1)


def init(sender_fn: Callable[[str, str], None]) -> None:
    """Register the sender function and start the scheduler thread."""
    global _SENDER, _THREAD
    with _LOCK:
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
    now = _utcnow()
    today = now.date()
    with _LOCK:
        st = _get_state(user_id)
        st["last_user_ts"] = now
        st["paused"] = True
        st["next_due"] = None
        st["attempts_today"] = 0
        st["last_attempt_day"] = today
        st["days_without_reply"] = 0
        st["_last_day_check"] = today
        st.pop("_pending_override", None)
        st.pop("_sending", None)


def track_bot_reply(user_id: str) -> None:
    now = _utcnow()
    today = now.date()
    with _LOCK:
        st = _get_state(user_id)
        st.setdefault("started_on", today)
        st["last_bot_ts"] = now

        if st.get("goal_reached"):
            st["paused"] = True
            st["next_due"] = None
            st.pop("_pending_override", None)
            return

        # agenda próxima janela mínima válida
        st["paused"] = False
        st["next_due"] = _pick_future_today(now, THREE_SLOTS if _allowed_today(st, today) >= 3 else ONE_SLOT)
        st["_last_day_check"] = today


def mark_goal(user_id: str, reached: bool = True) -> None:
    """Stop follow-ups permanently when the lead hits the goal."""
    with _LOCK:
        st = _get_state(user_id)
        st["goal_reached"] = bool(reached)
        if reached:
            st["paused"] = True
            st["next_due"] = None
            st.pop("_pending_override", None)
        else:
            st["paused"] = False


def update_docs_status(user_id: str, info: Dict[str, object]) -> None:
    """Store the latest doc flags so follow-ups can adapt the messaging."""
    normalized = {key: bool(info.get(key)) for key in DOC_KEYS}
    with _LOCK:
        st = _get_state(user_id)
        st["docs"] = normalized

def update_profile(user_id: str, name: Optional[str] = None) -> None:
    if not name:
        return
    with _LOCK:
        st = _get_state(user_id)
        st["name"] = (name or "").strip()

def _eligible(st: State, now: datetime) -> bool:
    if st.get("goal_reached") or st.get("paused") or st.get("_sending"):
        return False

    # janela local
    if not _in_window_local(now):
        return False

    next_due = _coerce_aware(st.get("next_due"))
    if next_due is None or now < next_due:
        return False

    last_bot_ts = _coerce_aware(st.get("last_bot_ts"))
    if last_bot_ts is None:
        return False
    st["last_bot_ts"] = last_bot_ts

    # limites
    if int(st.get("attempts_total", 0)) >= CFG["max_total_attempts"]:
        return False

    today = now.date()
    allowed = _allowed_today(st, today)
    if int(st.get("attempts_today", 0)) >= allowed:
        return False

    last_user_ts = _coerce_aware(st.get("last_user_ts"))
    if isinstance(last_user_ts, datetime) and last_user_ts > last_bot_ts:
        return False

    return True


def _loop() -> None:
    while True:
        time.sleep(CFG["loop_interval_secs"])
        now = _utcnow()
        due: list[Tuple[str, str, datetime, State]] = []

        with _LOCK:
            for user_id, st in list(_STATE.items()):
                _daily_housekeeping(st, now)
                if not _eligible(st, now):
                    continue
                message, next_due = _prepare_followup(st, now)
                if not message or not next_due:
                    continue
                next_due = _coerce_aware(next_due)
                if not next_due:
                    continue
                st["_sending"] = True
                st["_pending_override"] = next_due
                # não empilhe st_ref, só os 3 valores necessários
                due.append((user_id, message, next_due))

        for user_id, message, next_due in due:
            _deliver_followup(user_id, message, next_due)


def _pick_next_day(now_utc: datetime, bands: list[tuple[int,int]]) -> datetime:
    local_now = _to_local(now_utc)
    tomorrow = local_now.date() + timedelta(days=1)
    band = random.choice(bands)
    return _rand_time_in_band(tomorrow, band)

def _pick_future_today(now_utc: datetime, bands: list[tuple[int,int]]) -> datetime:
    local_now = _to_local(now_utc)
    today = local_now.date()
    # tenta até achar um horário depois do agora
    for _ in range(8):
        band = random.choice(bands)
        cand = _rand_time_in_band(today, band)
        if cand > now_utc and _in_window_local(cand):
            return cand
    # fallback: +15 min
    return now_utc + timedelta(minutes=15)

def _prepare_followup(st: State, now: datetime) -> Tuple[Optional[str], Optional[datetime]]:
    today = now.date()

    # zera por virada já é feito no housekeeping; só garante chave
    st.setdefault("attempts_today", 0)
    st.setdefault("attempts_total", 0)

    allowed = _allowed_today(st, today)
    if int(st["attempts_today"]) >= allowed:
        return None, None

    script_idx = _script_index(st)
    if script_idx >= len(FOLLOWUP_SCRIPT):
        return None, None

    base_msg = FOLLOWUP_SCRIPT[script_idx]
    message = _compose_followup_message(st, base_msg)  # aplica docs + placeholders

    bands = THREE_SLOTS if allowed >= 3 else ONE_SLOT

    # se haverá mais mensagens hoje, escolhe um band plausível; caso contrário, próximo dia
    if st["attempts_today"] + 1 < allowed:
        # ainda hoje, em um band aleatório
        next_due = _pick_future_today(now, bands)
    else:
        # amanhã (ou próximo dia útil), 1ª janela do dia
        next_due = _pick_next_day(now, bands)

    st["_pending_next_due"] = next_due
    st["_pending_attempts_today"] = int(st["attempts_today"]) + 1
    st["_pending_attempts_total"] = int(st["attempts_total"]) + 1

    return message, next_due


def _deliver_followup(user_id: str, message: str, next_due: datetime) -> None:
    if _SENDER is None:
        _LOGGER.warning("followup sender not configured; skipping message to %s", user_id)
        with _LOCK:
            st = _STATE.get(user_id)
            if st:
                st.pop("_sending", None)
                st.pop("_pending_override", None)
                st.pop("_pending_next_due", None)
                st.pop("_pending_attempts_today", None)
                st.pop("_pending_attempts_total", None)
        return

    try:
        _SENDER(user_id, message)
    except Exception as exc:  # pragma: no cover - defensive
        _LOGGER.warning("followup send failed for %s: %s", user_id, exc)
        with _LOCK:
            st = _STATE.get(user_id)
            if st:
                st.pop("_sending", None)
                st.pop("_pending_override", None)
                st.pop("_pending_next_due", None)
                st.pop("_pending_attempts_today", None)
                st.pop("_pending_attempts_total", None)
        return

    now = _utcnow()
    today = now.date()

    with _LOCK:
        st = _STATE.get(user_id)
        if not st: return

        scheduled_due = _coerce_aware(st.pop("_pending_next_due", next_due)) or next_due
        st["attempts_today"] = int(st.pop("_pending_attempts_today", st.get("attempts_today", 0)))
        st["attempts_total"] = int(st.pop("_pending_attempts_total", st.get("attempts_total", 0)))
        st.pop("_sending", None)

        st["last_attempt_day"] = today
        st["next_due"] = scheduled_due
        st["_last_day_check"] = today
        st.setdefault("days_without_reply", 0)


def _daily_housekeeping(st: State, now: datetime) -> None:
    today = now.date()

    last_check: Optional[date] = st.get("_last_day_check")
    if last_check is None:
        st["_last_day_check"] = today
        st.setdefault("last_attempt_day", today)
        st.setdefault("attempts_today", 0)
        st.setdefault("attempts_total", 0)
        st.setdefault("started_on", today)
        return

    if today == last_check:
        return

    days_passed = (today - last_check).days
    st["_last_day_check"] = today

    st["attempts_today"] = 0
    st["last_attempt_day"] = today

    last_bot_ts = _coerce_aware(st.get("last_bot_ts"))
    last_user_ts = _coerce_aware(st.get("last_user_ts"))
    if last_bot_ts is not None:
        st["last_bot_ts"] = last_bot_ts
    if last_user_ts is not None:
        st["last_user_ts"] = last_user_ts

    user_replied = (
        isinstance(last_user_ts, datetime)
        and isinstance(last_bot_ts, datetime)
        and last_user_ts > last_bot_ts
    )

    if user_replied:
        st["days_without_reply"] = 0
    else:
        st["days_without_reply"] = int(st.get("days_without_reply", 0)) + days_passed

    # NÃO pausar automaticamente por days_without_reply; régua de 12 controla o freio
    # Ajusta next_due para a janela local se estiver fora dela
    next_due = _coerce_aware(st.get("next_due"))
    if next_due is not None and not _in_window_local(next_due):
        local_now = _to_local(now)
        band = THREE_SLOTS[0] if _allowed_today(st, today) >= 3 else ONE_SLOT[0]
        candidate = _rand_time_in_band(local_now.date(), band)
        if candidate <= now:
            candidate = _pick_next_day(now, THREE_SLOTS if _allowed_today(st, today) >= 3 else ONE_SLOT)
        st["next_due"] = candidate


def _compose_followup_message(st: State, base_script: str) -> str:
    # prefixo simples com status de docs (quando pertinente)
    docs = st.get("docs") if isinstance(st.get("docs"), dict) else None
    prefix = ""
    if docs:
        missing = [DOC_LABELS[k] for k in DOC_KEYS if not docs.get(k)]
        received = [DOC_LABELS[k] for k in DOC_KEYS if docs.get(k)]
        if received and missing:
            prefix = f"Recebi { _format_list(received) }. Ainda falta: { _format_list(missing) }.\n\n"
        elif missing and not received:
            # nada recebido ainda → sem prefixo “cobrador”; deixa o script falar
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

def _get_state(user_id: str) -> State:
    if user_id not in _STATE:
        _STATE[user_id] = {
            "last_user_ts": None,
            "last_bot_ts": None,
            "next_due": None,
            "attempts_today": 0,
            "attempts_total": 0,          # NEW
            "last_attempt_day": None,
            "started_on": _utcnow().date(),  # NEW: dia de início do funil
            "days_without_reply": 0,
            "paused": True,
            "goal_reached": False,
            "_last_day_check": _utcnow().date(),
            "docs": None,
            "name": "",                   # NEW: placeholder
        }
    return _STATE[user_id]


def _coerce_aware(value: object) -> Optional[datetime]:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None
