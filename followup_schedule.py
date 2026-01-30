# followup_schedule.py
from datetime import datetime, timedelta
import random

BRAZIL_OFFSET = -3

SLOTS_BRAZIL = [
    (8, 0),
    (13, 0),
    (20, 0),
]

def to_brazil(dt_utc: datetime) -> datetime:
    return dt_utc + timedelta(hours=BRAZIL_OFFSET)

def to_utc(dt_br: datetime) -> datetime:
    return dt_br - timedelta(hours=BRAZIL_OFFSET)

def pick_next_due(
    now_utc: datetime,
) -> datetime:
    """
    Primeiro repique do ciclo → imediato
    Demais → slot humano (08 / 13 / 20)
    """

    now_br = to_brazil(now_utc)

    slots = SLOTS_BRAZIL[:]
    random.shuffle(slots)

    for h, m in slots:
        candidate_br = now_br.replace(
            hour=h,
            minute=m,
            second=0,
            microsecond=0
        )
        if candidate_br > now_br:
            return to_utc(candidate_br)

    # fallback: amanhã, slot aleatório
    tomorrow_br = now_br + timedelta(days=1)
    h, m = random.choice(SLOTS_BRAZIL)

    tomorrow_br = tomorrow_br.replace(
        hour=h,
        minute=m,
        second=0,
        microsecond=0
    )

    return to_utc(tomorrow_br)
