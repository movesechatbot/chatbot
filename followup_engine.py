import psycopg2.extras
from db import db_get_conn

ELIGIBLE_USERS_SQL = """
SELECT *
FROM followup_state
WHERE
  goal_reached = FALSE
  AND attempts_total < 12
  AND (
    paused = FALSE
    OR (
      paused = TRUE
      AND last_bot_ts IS NOT NULL
      AND (
        last_user_ts IS NULL
        OR last_user_ts < last_bot_ts
      )
      AND NOW() >= last_bot_ts + INTERVAL '15 minutes'
    )
  )
  AND (
    next_due IS NULL
    OR next_due <= NOW()
  )
FOR UPDATE SKIP LOCKED
"""

def get_eligible_users_locked():
    conn = db_get_conn()
    conn.autocommit = False

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(ELIGIBLE_USERS_SQL)
    users = cur.fetchall()

    return conn, users
