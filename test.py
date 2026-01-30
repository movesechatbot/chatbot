from followup_engine import get_eligible_users

def main():
    users = get_eligible_users()

    print(f"Total elegíveis: {len(users)}\n")

    for u in users:
        # imprime só campos importantes pra debug
        print({
            "user_id": u[0],            # ajuste índice se necessário
            "paused": u[6],
            "attempts_total": u[4],
            "next_due": u[10],
            "last_bot_ts": u[8],
            "last_user_ts": u[7],
        })

if __name__ == "__main__":
    main()
