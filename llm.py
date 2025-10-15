from typing import Optional, List, Dict, Tuple, Any
import json, logging
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL
# from playbook import build_snippet, proxima_etapa
import re

_logger = logging.getLogger(__name__)

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

_EMOJI_RE = re.compile(
    r"[\U0001F1E6-\U0001F1FF]"      # flags
    r"|[\U0001F300-\U0001F5FF]"     # symbols & pictographs
    r"|[\U0001F600-\U0001F64F]"     # emoticons
    r"|[\U0001F680-\U0001F6FF]"     # transport & map
    r"|[\U0001F700-\U0001F77F]"     # alchemical
    r"|[\U0001F780-\U0001F7FF]"     # geometric ext
    r"|[\U0001F800-\U0001F8FF]"
    r"|[\U0001F900-\U0001F9FF]"
    r"|[\U0001FA00-\U0001FAFF]"
    r"|[\U00002700-\U000027BF]"     # dingbats
    r"|[\U00002600-\U000026FF]",    # misc symbols
    flags=re.UNICODE
)

def _strip_noise(text: str) -> str:
    if not isinstance(text, str):
        return text
    t = _EMOJI_RE.sub("", text)
    # opcional: encurta respostas antigas muito longas
    return t[:800]

def _clean_history(hist):
    if not hist: return []
    out = []
    for m in hist:
        r = m.get("role")
        c = m.get("content", "")
        if r in ("user", "assistant") and isinstance(c, str):
            out.append({"role": r, "content": _strip_noise(c)})
    return out

Message = Dict[str, str]

def _trim(history: Optional[List[Message]], max_msgs: int = 16) -> List[Message]:
    if not history: return []
    clean = [m for m in history if m.get("role") in ("user","assistant") and isinstance(m.get("content"), str)]
    return clean[-max_msgs:]

def ask_chatgpt(
    pergunta: str,
    ctx: Optional[List[str]],
    history: Optional[List[Message]] = None,
    playbook_snippet: str = "",
    debug: bool = False
) -> str | Tuple[str, Dict[str, Any]]:
    if not _client:
        return ("sem acesso ao modelo externo." if not debug
                else ("sem acesso ao modelo externo.", {"error": "no_client"}))

    sys = (
        "Você é Movelina, atendente virtual (SDR) da Imobiliária Movese."
        "Responda humano. Faça sempre 1 pergunta por vez."
        "Não use emojis, não elogie, não parabenize e não invente assuntos. "
        "se faltar dado no contexto, diga isso em 1 linha e peça para reformular."
        "use somente o contexto confiável recebido; não invente fatos."
        "Sempre termine sua resposta com a pergunta da etapa atual."
        "sempre Separe frases com mais de 4 palavras pulando duas linhas para facilitar a leitura."
        "Nunca antecipe informações de outras etapas."
        "Nunca encerre o assunto e nunca prometa retorno futuro."
        "caso o usuário pergunte sobre o Creci, responda em qualquer etapa"
        "Esse é o nosso Creci:\n\n28339 J - Imobiliária Move.se Gênesis LTDA"
        "Sua única meta é conduzir o lead pelo fluxo de atendimento até a etapa CONTEXTUALIZAÇÃO."
        "Use o histórico apenas para manter coerência."
        "Nunca invente, nunca ofereça ajuda extra e nunca fale sobre equipe, valores ou horários"
    )  # :contentReference[oaicite:0]{index=0}
 



    messages: List[Message] = [{"role":"system","content": sys}]

    # NEW: cartilha da etapa atual (curta)
    if playbook_snippet:
        messages.append({"role":"system","content": playbook_snippet})

    # histórico
    trimmed_hist = _trim(_clean_history(history), max_msgs=10)
    messages += trimmed_hist


    # contexto confiável (FAQ top-k) — depois da cartilha
    ctx_block = None
    if ctx:
        ctx_block = "contexto confiável:\n- " + "\n- ".join(ctx)
        messages.append({"role":"system","content": ctx_block})

    messages.append({"role":"user","content": pergunta})

    trace = {
        "model": OPENAI_MODEL,
        "temperature": 0.5,
        "max_tokens": 600,
        "system_base": sys[:2000],  # evita log gigante
        "playbook_snippet": (playbook_snippet or "")[:4000],
        "history_trimmed": trimmed_hist,
        "ctx_block": (ctx_block or "")[:4000],
        "final_messages": messages,  # TODAS as mensagens que vão para a API
    }

    try:
        r = _client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.5,
            max_tokens=600,
            response_format={"type": "text"},
            messages=messages,
            timeout=90
        )
        answer = (r.choices[0].message.content or "").strip()
        trace["answer"] = answer

        return (answer, trace) if debug else answer

    except Exception as e:
        m = str(e)
        trace["error"] = m
        _logger.warning("[LLM TRACE ERROR] %s", json.dumps(trace, ensure_ascii=False))

        if "insufficient_quota" in m or "429" in m:
            fallback = "no momento estou sem créditos para consultar o modelo; sigo pelo FAQ."
            return (fallback, trace) if debug else fallback
        return (m, trace) if debug else m
    
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

