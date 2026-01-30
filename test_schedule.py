from datetime import datetime, timezone
from followup_schedule import pick_next_due

now = datetime.now(timezone.utc)

print("Agora UTC:", now)
print("Primeiro repique:", pick_next_due(now, True))
print("Repique seguinte:", pick_next_due(now, False))
