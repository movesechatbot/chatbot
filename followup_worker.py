# followup_worker.py
import logging
from followup_engine import get_eligible_users_locked
from followup_executor import execute_followup_for_user
from db import db_put_conn

logger = logging.getLogger(__name__)

def run_followup_cycle():
    conn, users = get_eligible_users_locked()

    if not users:
        conn.commit()
        db_put_conn(conn)
        logger.info("[FOLLOWUP] nenhum usuário elegível")
        return

    logger.info("[FOLLOWUP] %d usuários elegíveis", len(users))

    try:
        for user in users:
            sent = execute_followup_for_user(user, conn)
            logger.info(
                "[FOLLOWUP] user=%s sent=%s",
                user["user_id"],
                sent
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        db_put_conn(conn)
