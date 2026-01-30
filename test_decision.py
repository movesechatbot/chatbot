from followup_engine import get_eligible_users
from followup_decision import should_send

users = get_eligible_users()

for u in users:
    decision = should_send(u)
    print(u[0], decision)


# from followup_engine import get_eligible_users

# users = get_eligible_users()
# assert users == [] or len(users) == 0

# print("OK: nenhum usuário elegível")
