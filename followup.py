from __future__ import annotations
import logging, random, threading, time, json
from datetime import datetime, timedelta, date, timezone
from typing import Callable, Dict, Optional, Tuple
from zoneinfo import ZoneInfo
from config import SOCIAL_IG_URL, TIMEZONE
from db import db_query_one, db_query_all, db_execute

# --- CONFIG PRODUÇÃO ---
CFG = {
    # fuso do cliente
    "tz": TIMEZONE,          # ex: "America/Sao_Paulo"

    # janela global de envio (hora local)
    "window_start_hour": 6,  # 06:00
    "window_end_hour": 24,   # 00:00 (do mesmo dia)

    # plano de tentativas:
    # dia 1: até 3
    # dia 2: até 3
    # dia 3+: 1 por dia (default)
    "daily_plan": {1: 3, 2: 3},

    # 3 + 3 + 1/dia até 12 contatos
    "max_total_attempts": 12,

    # intervalo do loop interno
    "loop_interval_secs": 5,

    # gap mínimo entre resposta do bot e followup (em minutos)
    "min_gap_minutes": 60,
}

# bandas de horário em MINUTOS a partir de 00:00
# dias 1 e 2 → 3 repicks distribuídos nessas 4 janelas:
#  06:00–09:00
#  11:30–13:30
#  16:30–18:30
#  20:00–21:30
DAY12_BANDS: list[tuple[int, int]] = [
    (6 * 60, 9 * 60),                 # 06:00–09:00
    (11 * 60 + 30, 13 * 60 + 30),     # 11:30–13:30
    (16 * 60 + 30, 18 * 60 + 30),     # 16:30–18:30
    (20 * 60, 21 * 60 + 30),          # 20:00–21:30
]

# a partir do 3º dia → 1 repick/dia entre 06:00 e 00:00
LATE_BANDS: list[tuple[int, int]] = [
    (6 * 60, 24 * 60),                # 06:00–24:00
]

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

# colunas:
# user_id, started_on, last_user_ts, last_bot_ts, next_due,
# attempts_today, attempts_total, last_attempt_day,
# days_without_reply, paused, goal_reached, name, docs

def _row_to_state(row) -> State:
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
    start_date = st.get("started_on") or today
    return max(1, (today - start_date).days + 1)

def _allowed_today(st: State, today: date) -> int:
    d = _day_index(st, today)
    plan = CFG["daily_plan"]
    return plan.get(d, 1)

def _script_index(st: State) -> int:
    return min(int(st.get("attempts_total", 0)), len(FOLLOWUP_SCRIPT) - 1)

def _bands_for_day(st: State, today: date) -> list[tuple[int, int]]:
    d = _day_index(st, today)
    if d in (1, 2):
        return DAY12_BANDS
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
    now = _utcnow()
    today = now.date()
    st = _load_state(user_id)
    st["last_user_ts"] = now
    st["paused"] = True
    st["next_due"] = None
    st["attempts_today"] = 0
    st["last_attempt_day"] = today
    st["days_without_reply"] = 0
    st["_last_day_check"] = today
    _save_state(st)


def track_bot_reply(user_id: str) -> None:
    now = _utcnow()
    today = now.date()
    st = _load_state(user_id)
    st.setdefault("started_on", today)
    st["last_bot_ts"] = now

    if st.get("goal_reached"):
        st["paused"] = True
        st["next_due"] = None
    else:
        st["paused"] = False
        bands = _bands_for_day(st, today)
        next_due = _pick_future_today(now, bands, st)
        st["next_due"] = next_due

    st["_last_day_check"] = today
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
    _save_state(st)

def update_profile(user_id: str, name: Optional[str] = None) -> None:
    if not name:
        return
    st = _load_state(user_id)
    st["name"] = (name or "").strip()
    _save_state(st)


# -------- núcleo do scheduler --------

def _eligible(st: State, now: datetime) -> bool:
    if st.get("goal_reached") or st.get("paused"):
        return False

    if not _in_window_local(now):
        return False

    next_due = _coerce_aware(st.get("next_due"))
    if next_due is None or now < next_due:
        return False

    last_bot_ts = _coerce_aware(st.get("last_bot_ts"))
    if last_bot_ts is None:
        return False
    st["last_bot_ts"] = last_bot_ts

    min_gap = int(CFG.get("min_gap_minutes", 0))
    if min_gap > 0:
        gap = now - last_bot_ts
        if gap < timedelta(minutes=min_gap):
            return False

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

        # pega todos ativos (não goal_reached)
        rows = db_query_all(
            """
            SELECT user_id, started_on, last_user_ts, last_bot_ts, next_due,
                   attempts_today, attempts_total, last_attempt_day,
                   days_without_reply, paused, goal_reached, name, docs
              FROM followup_state
             WHERE goal_reached = FALSE
            """
        )

        for row in rows:
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

        for user_id, message, next_due, st in due:
            _deliver_followup(user_id, message, next_due, st)


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
    today = now.date()

    st.setdefault("attempts_today", 0)
    st.setdefault("attempts_total", 0)

    allowed = _allowed_today(st, today)
    if int(st["attempts_today"]) >= allowed:
        return None, None

    script_idx = _script_index(st)
    if script_idx >= len(FOLLOWUP_SCRIPT):
        return None, None

    base_msg = FOLLOWUP_SCRIPT[script_idx]
    message = _compose_followup_message(st, base_msg)

    bands = _bands_for_day(st, today)

    if st["attempts_today"] + 1 < allowed:
        next_due = _pick_future_today(now, bands, st)
    else:
        next_due = _pick_next_day(now, bands, st)

    st["_pending_next_due"] = next_due
    st["_pending_attempts_today"] = int(st["attempts_today"]) + 1
    st["_pending_attempts_total"] = int(st["attempts_total"]) + 1

    return message, next_due


def _deliver_followup(user_id: str, message: str, next_due: datetime, st: State) -> None:
    if _SENDER is None:
        _LOGGER.warning("followup sender not configured; skipping message to %s", user_id)
        return

    try:
        _SENDER(user_id, message)
    except Exception as exc:
        _LOGGER.warning("followup send failed for %s: %s", user_id, exc)
        return

    now = _utcnow()
    today = now.date()

    scheduled_due = _coerce_aware(st.get("_pending_next_due", next_due)) or next_due
    st["attempts_today"] = int(st.get("_pending_attempts_today", st.get("attempts_today", 0)))
    st["attempts_total"] = int(st.get("_pending_attempts_total", st.get("attempts_total", 0)))

    st["last_attempt_day"] = today
    st["next_due"] = scheduled_due
    st["_last_day_check"] = today
    st.setdefault("days_without_reply", 0)
    st["last_bot_ts"] = now

    st.pop("_pending_next_due", None)
    st.pop("_pending_attempts_today", None)
    st.pop("_pending_attempts_total", None)

    _save_state(st)


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

    # se o próximo horário caiu fora da janela, realoca dentro da janela do dia
    next_due = _coerce_aware(st.get("next_due"))
    if next_due is not None and not _in_window_local(next_due):
        local_now = _to_local(now)
        bands = _bands_for_day(st, local_now.date())
        candidate = _pick_future_today(now, bands, st)
        if candidate <= now:
            candidate = _pick_next_day(now, bands, st)
        st["next_due"] = candidate


# -------- helpers de mensagem / state --------

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
