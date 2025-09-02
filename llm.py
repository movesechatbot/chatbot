from typing import Optional, List, Dict
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
Message = Dict[str, str]

def _trim(history: Optional[List[Message]], max_msgs: int = 16) -> List[Message]:
    if not history: return []
    clean = [m for m in history if m.get("role") in ("user","assistant") and isinstance(m.get("content"), str)]
    return clean[-max_msgs:]

def ask_chatgpt(pergunta: str, ctx: Optional[List[str]], history: Optional[List[Message]] = None) -> str:
    if not _client:
        return "sem acesso ao modelo externo."

    sys = (
      "você é um atendente de whatsapp. "
      "responda curto e humanizado, siga o histórico da conversa. "
      "sua principal tarefa é conduzir o cliente a enviar documentos para análise de crédito."
      "os documentos para análise de crédito são: RG ou CNH,comprovante de residência e comprovante de renda. "
      "EXCEÇÃO: para saudações ou pequenas cortesias (ex: 'oi', 'boa tarde'), responda educadamente e avance a conversa."
      "se faltar dado factual no contexto, peça para reformular. "
    )

    messages: List[Message] = [{"role":"system","content": sys}]
    messages += _trim(history, max_msgs=16)

    if ctx:
        messages.append({"role":"system","content": "contexto confiável:\n- " + "\n- ".join(ctx)})

    messages.append({"role":"user","content": pergunta})

    try:
        r = _client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=1,
            max_completion_tokens=300,
            messages=messages,
            timeout=12
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        m = str(e)
        if "insufficient_quota" in m or "429" in m:
            return "no momento estou sem créditos para consultar o modelo; sigo pelo FAQ."
        return m



# from typing import Optional, List, Dict, Literal
# from openai import OpenAI
# from config import OPENAI_API_KEY, OPENAI_MODEL

# Role = Literal["system","user","assistant"]
# Message = Dict[str, str]

# _client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# def _trim_history(history: Optional[List[Message]], max_turns: int = 8) -> List[Message]:
#     """
#     Mantém só os últimos 'max_turns' turnos (user+assistant = 2 msgs).
#     Aceita lista de dicts: [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}...]
#     """
#     if not history:
#         return []
#     # remove sistemas antigos e garante apenas roles válidos
#     clean = [m for m in history if m.get("role") in ("user","assistant") and isinstance(m.get("content"), str)]
#     # cada turno ~2 msgs → 2*max_turns
#     return clean[-(2*max_turns):]

# def ask_chatgpt(pergunta: str, ctx: Optional[List[str]], history: Optional[List[Message]] = None) -> str:
#     """
#     - pergunta: última entrada do usuário
#     - ctx: lista de strings com top-k (sempre enviado, nunca 'open')
#     - history: histórico da conversa (user/assistant). ex:
#         [{"role":"user","content":"oi"},
#          {"role":"assistant","content":"olá!"},
#          {"role":"user","content":"quais cidades?"}]
#     """
#     if not _client:
#         return "no momento não consigo acessar o modelo externo."

#     sys = (
#         "você é um atendente de whatsapp, breve e humano. "
#         "use SOMENTE o contexto confiável fornecido. "
#         "se algo não estiver no contexto, peça reformulação curta. "
#         "não invente fatos."
#     )

#     messages: List[Message] = [{"role":"system","content": sys}]

#     # histórico janelado (mantém coerência de conversa)
#     messages += _trim_history(history, max_turns=8)

#     # contexto sempre presente (mesmo com score baixo)
#     if ctx:
#         ctx_block = "contexto confiável:\n- " + "\n- ".join(ctx)
#         messages.append({"role":"system","content": ctx_block})

#     # última pergunta do usuário
#     messages.append({"role":"user","content": pergunta})

#     try:
#         r = _client.chat.completions.create(
#             model=OPENAI_MODEL,
#             # o4-mini aceita apenas temperature padrão=1; deixe 1
#             temperature=1,
#             max_completion_tokens=300,
#             messages=messages,
#             timeout=12,
#         )
#         return r.choices[0].message.content.strip()

#     except Exception as e:
#         m = str(e)
#         if "insufficient_quota" in m or "429" in m:
#             return "no momento estou sem créditos para consultar o modelo; sigo pelo FAQ."
#         return m

