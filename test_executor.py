from followup_engine import get_eligible_users
from followup_executor import execute_followup_for_user

users = get_eligible_users()

for u in users:
    sent = execute_followup_for_user(u)
    print({
    "user_id": u["user_id"],
    "sent": sent,
    "attempts_today": u["attempts_today"],
    "attempts_total": u["attempts_total"],
})

