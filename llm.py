from typing import Optional, List
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def ask_chatgpt(pergunta: str, ctx: Optional[List[str]]) -> str:
    if not _client:
        return "não consegui consultar o modelo externo no momento."
    sys = (
    "você é um atendente de whatsapp. "
    "sempre responda de forma curta e humanizada. "
    "nunca invente além do contexto. "
    "se não houver informação no contexto, peça para a pessoa reformular ou aguarde instruções."
    )
    user = f"pergunta: {pergunta}\n\ncontexto:\n- " + "\n- ".join(ctx) if ctx else pergunta
    r = _client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.2,
        max_tokens=300,
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
        timeout=12
    )
    return r.choices[0].message.content.strip()
