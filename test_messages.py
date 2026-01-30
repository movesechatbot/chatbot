from followup_messages import render_message

for i in range(0, 15):
    print(i, "→", render_message(i, name="Carlos"))
