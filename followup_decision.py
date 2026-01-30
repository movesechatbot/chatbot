# followup_decision.py
from datetime import datetime, timezone, timedelta
from typing import Dict

# =========================
# CONFIG
# =========================
START_HOUR = 6
END_HOUR = 24
BRAZIL_OFFSET = -3
MAX_TOTAL_ATTEMPTS = 12


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_brazil(dt_utc: datetime) -> datetime:
    return dt_utc + timedelta(hours=BRAZIL_OFFSET)


def inside_brazil_window(now_utc: datetime) -> bool:
    local = to_brazil(now_utc)
    h = local.hour
    return START_HOUR <= h < END_HOUR


def diff_days_brazil(from_date, to_utc: datetime) -> int:
    """
    from_date: date (started_on)
    to_utc: datetime utc
    """
    local_to = to_brazil(to_utc).date()
    return (local_to - from_date).days


def should_send(user) -> Dict:
    """
    Decide se pode enviar mensagem agora.
    user: row do followup_state (tupla)
    """

    # ⚠️ Ajuste os índices se a ordem da tabela mudar
    started_on = user["started_on"]
    attempts_today = user["attempts_today"] or 0
    attempts_total = user["attempts_total"] or 0


    now = _utcnow()

    # =========================
    # JANELA DE HORÁRIO
    # =========================
    if not inside_brazil_window(now):
        return {
            "send": False,
            "reason": "fora_da_janela",
            "attempt_index": None,
            "max_today": 0,
        }

    # =========================
    # LIMITE GLOBAL
    # =========================
    if attempts_total >= MAX_TOTAL_ATTEMPTS:
        return {
            "send": False,
            "reason": "limite_total",
            "attempt_index": None,
            "max_today": 0,
        }

    # =========================
    # DIA DO CICLO
    # =========================
    days_inactive = diff_days_brazil(started_on, now) + 1

    if days_inactive <= 2:
        max_today = 3
    else:
        max_today = 1

    if attempts_today >= max_today:
        return {
            "send": False,
            "reason": "limite_diario",
            "attempt_index": None,
            "max_today": max_today,
        }

    # =========================
    # OK PARA ENVIAR
    # =========================
    return {
        "send": True,
        "reason": "ok",
        "attempt_index": attempts_total,
        "max_today": max_today,
    }
