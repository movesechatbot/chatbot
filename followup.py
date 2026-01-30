# followup_state.py (somente estado; n8n cuida do tempo e do envio)
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, Optional
from db import db_query_one, db_execute

DOC_KEYS = ("rg_cnh", "residencia", "renda", "email")

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _ensure_row(user_id: str) -> None:
    row = db_query_one(
        "SELECT user_id FROM followup_state WHERE user_id = %s",
        (user_id,),
    )
    if row:
        return

    today = _utcnow().date()
    db_execute(
        """
        INSERT INTO followup_state (
            user_id,
            started_on,
            attempts_today,
            attempts_total,
            days_without_reply,
            paused,
            goal_reached,
            next_due
        )
        VALUES (%s, %s, 0, 0, 0, TRUE, FALSE, NULL)
        """,
        (user_id, today),
    )

def mark_user_reply(user_id: str) -> None:
    """
    Usuário respondeu:
    - zera ciclo
    - pausa follow-up
    """
    if not user_id:
        return

    _ensure_row(user_id)
    now = _utcnow()

    db_execute(
        """
        UPDATE followup_state
           SET last_user_ts = %s,
               started_on = %s,
               paused = TRUE,
               next_due = NULL,
               attempts_today = 0,
               attempts_total = 0,
               last_attempt_day = %s,
               days_without_reply = 0
         WHERE user_id = %s
        """,
        (now, now.date(), now.date(), user_id),
    )

def track_bot_reply(user_id: str) -> None:
    """
    Bot respondeu:
    - atualiza last_bot_ts
    - pausa follow-up
    - NÃO reseta attempts_today
    """
    if not user_id:
        return

    _ensure_row(user_id)
    now = _utcnow()

    db_execute(
        """
        UPDATE followup_state
           SET last_bot_ts = %s,
               paused = TRUE,
               next_due = NULL
         WHERE user_id = %s
        """,
        (now, user_id),
    )

def update_profile(user_id: str, name: Optional[str] = None) -> None:
    if not user_id or not name:
        return

    _ensure_row(user_id)
    db_execute(
        "UPDATE followup_state SET name = %s WHERE user_id = %s",
        ((name or "").strip(), user_id),
    )

def update_docs_status(user_id: str, info: Dict[str, object]) -> None:
    if not user_id:
        return

    _ensure_row(user_id)
    normalized = {k: bool(info.get(k)) for k in DOC_KEYS}
    docs_json = json.dumps(normalized, ensure_ascii=False)

    all_done = all(normalized.get(k) for k in DOC_KEYS)

    if all_done:
        db_execute(
            """
            UPDATE followup_state
               SET docs = %s,
                   goal_reached = TRUE,
                   paused = TRUE,
                   next_due = NULL
             WHERE user_id = %s
            """,
            (docs_json, user_id),
        )
    else:
        db_execute(
            "UPDATE followup_state SET docs = %s WHERE user_id = %s",
            (docs_json, user_id),
        )

def mark_goal(user_id: str, reached: bool = True) -> None:
    if not user_id:
        return

    _ensure_row(user_id)

    if reached:
        db_execute(
            """
            UPDATE followup_state
               SET goal_reached = TRUE,
                   paused = TRUE,
                   next_due = NULL
             WHERE user_id = %s
            """,
            (user_id,),
        )
    else:
        db_execute(
            """
            UPDATE followup_state
               SET goal_reached = FALSE
             WHERE user_id = %s
             """,
            (user_id,),
        )
