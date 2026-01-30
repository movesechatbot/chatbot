from datetime import datetime, timezone
from followup_decision import should_send
from followup_messages import render_message
from followup_schedule import pick_next_due
from whatsapp import _send_text

def execute_followup_for_user(user: dict, conn) -> bool:
    decision = should_send(user)
    if not decision["send"]:
        return False

    now_utc = datetime.now(timezone.utc)

    message = render_message(
        decision["attempt_index"],
        user.get("name")
    )

    _send_text(user["user_id"], message)

    next_due = pick_next_due(now_utc)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE followup_state SET
              attempts_total = attempts_total + 1,
              attempts_today = CASE
                WHEN CURRENT_DATE = last_attempt_day
                THEN attempts_today + 1
                ELSE 1
              END,
              last_attempt_day = CURRENT_DATE,
              last_bot_ts = NOW(),
              next_due = %s
            WHERE user_id = %s
            """,
            (next_due, user["user_id"])
        )

    return True
