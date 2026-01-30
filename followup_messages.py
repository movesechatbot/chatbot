# followup_messages.py
from typing import Optional

SCRIPT = [
    "Vi que você ainda não conseguiu me responder. Fica tranquilo(a), estou por aqui para te ajudar e entendo que o dia a dia é corrido. Qual melhor horário para conversarmos aqui?",
    "Olá!, só reforçando: meu objetivo é facilitar ao máximo para você. Se puder me informar a cidade onde mora e onde trabalha, já consigo saber se tenho opções para você",
    "Você já tem imóvel em vista ou está começando a olhar agora?",
    "Tudo bem!?, estou encerrando meu dia por aqui, mas deixei teu nome no topo da minha agenda pra te responder assim que você me der um retorno. Te desejo uma ótima noite e sigo à disposição pra te ajudar",
    "Bom dia !, estou começando meu expediente, vi que você não me respondeu ainda.. Assim que puder me dar um sinal, já seguimos com os próximos passos",
    "Você procura imóvel para morar ou para investir?",
    "Passando aqui rapidinho pra dizer que sigo à disposição! Mesmo que o teu momento ainda não seja de compra posso te ajudar a entender as possibilidades do mercado e te ajudar a planejar os próximos passos.",
    "Você já chegou a conversar com o banco sobre financiamento ou prefere que eu te ajude a entender essa parte?",
    "Vou aproveitar pra te mandar meu Instagram 👉 [link perfil]. Vale a pena seguir.",
    "Oi!, que tal reservar só 5 minutinhos hoje para falarmos?",
    "{{name}} ???",
    "{{name}}, eu errei em alguma coisa contigo?"
]


def render_message(
    attempt_index: int,
    name: Optional[str] = None
) -> str:
    """
    Retorna a mensagem correta baseada no índice de tentativa.
    Nunca quebra.
    """

    if attempt_index < 0:
        attempt_index = 0

    if attempt_index >= len(SCRIPT):
        msg = SCRIPT[-1]
    else:
        msg = SCRIPT[attempt_index]

    safe_name = (name or "").strip() or "tudo bem"
    return msg.replace("{{name}}", safe_name)
