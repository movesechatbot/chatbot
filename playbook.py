# carrega playbook.json e gera “cartilha” curta por etapa p/ injetar como system no GPT

from __future__ import annotations
import json, pathlib
import unicodedata
import re

PB_PATH = pathlib.Path("playbook.json")

# etapas principais
BOAS = "BOAS_VINDAS"
FILTRAR = "FILTRAR_CLIENTE"
NIVEL = "NIVEL_DE_CONSCIENCIA"
CONTEXT = "CONTEXTUALIZACAO"

# subetapas do FILTRAR
FILTRAR_CIDADE = "FILTRAR_CIDADE"
FILTRAR_PRIMEIRO = "FILTRAR_PRIMEIRO_IMOVEL"
FILTRAR_ESCRITURA = "FILTRAR_ESCRITURA"
FILTRAR_RENDA = "FILTRAR_RENDA"
FILTRAR_ENTRADA = "FILTRAR_ENTRADA"

ETAPAS = (
    BOAS,
    FILTRAR_CIDADE,
    FILTRAR_PRIMEIRO,
    FILTRAR_ESCRITURA,
    FILTRAR_RENDA,
    FILTRAR_ENTRADA,
    NIVEL,
    CONTEXT
)


ETAPAS = (BOAS, FILTRAR, NIVEL, CONTEXT)

# -------- carregamento básico --------
def _load() -> list:
    with PB_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

PLAYBOOK = _load()

# helpers pra achar blocos do json original (sem mudar teu formato)
def _find(etapa_nome_pt: str) -> dict | None:
    for item in PLAYBOOK:
        if item.get("etapa", "").strip().upper().replace(" ", "_") == etapa_nome_pt:
            return item
    return None

def _safe(s: str | None) -> str:
    return (s or "").strip()

# cidades (usadas em FILTRAR_CLIENTE)
def lista_cidades() -> list[str]:
    filtrar = _find(FILTRAR)
    if not filtrar:
        return []
    blocos = filtrar.get("blocos", [])
    for b in blocos:
        if "cidades" in b:
            return b.get("cidades", [])
    return []

CIDADES = set(lista_cidades())

# -------- geração de snippet curto por etapa --------
# máx ~1200 chars pra economizar token
MAX_SNIPPET = 1200

def build_snippet(etapa: str) -> str:  
    etapa = (etapa or BOAS).upper()
    if etapa not in ETAPAS:
        etapa = BOAS

    if etapa == BOAS:
        node = _find(BOAS)
        instr = _safe(node.get("instrução"))
        fala = _safe(node.get("fala"))
        txt = (
            "cartilha (boas-vindas):\n"
            "- objetivo: abordar lead, dizer quem somos e por que o contato.\n"
            f"- regra: {_truncate(instr)}\n"
            "- tom: curto, humano, direto; avance a conversa após cumprimentos.\n"
            f"- exemplo:\n{fala}"
        )
        return _truncate(txt, MAX_SNIPPET)

    if etapa == FILTRAR:
        node = _find(FILTRAR) or {}
        blocos = node.get("blocos", [])
        fala_cidade = next((b.get("fala") for b in blocos if _safe(b.get("fala","")).lower().startswith("hoje tu procura")), "")
        fala_fora = next((b.get("fala") for b in blocos if "infelizmente" in _safe(b.get("fala","")).lower()), "")
        fala_primeiro = next((b.get("fala") for b in blocos if "primeiro imóvel" in _safe(b.get("fala","")).lower()), "")
        fala_escritura = next((b.get("fala") for b in blocos if "escritura" in _safe(b.get("fala","")).lower()), "")
        fala_renda = next((b.get("fala") for b in blocos if _safe(b.get("fala","")).lower().startswith("qual a sua renda")), "")
        fala_entrada = next((b.get("fala") for b in blocos if "entrada acima de 10 mil" in _safe(b.get("fala","")).lower()), "")

        txt = (
            "cartilha (filtro inicial):\n"
            "- objetivo: qualificar rápido; atuar só RM de Porto Alegre.\n"
            f"- cidades válidas: {', '.join(sorted(CIDADES))}\n"
            "- fluxo:\n"
            "  1) perguntar a cidade antes de tudo; 2) encerre se a cidade não estiver na lista; 3) caso o lead responda uma cidade da lista, pergunte se é o 1º(primeiro) imóvel;\n"
            "  4) se não for 1º(primeiro), checar se ele possui escritura; 5) se possuir a escritura, aí você pergunta a renda dele;\n"
            "  6) se renda <= 6500, perguntar se tem entrada > 10 mil.\n"
            "- exemplos:\n"
            f"  • {fala_cidade}\n"
            f"  • {fala_fora}\n"
            f"  • {fala_primeiro}\n"
            f"  • {fala_escritura}\n"
            f"  • {fala_renda}\n"
            f"  • {fala_entrada}"
        )
        return _truncate(txt, MAX_SNIPPET)

    if etapa == NIVEL:
        node = _find("NÍVEL_DE_CONSCIÊNCIA") or _find(NIVEL) or {}
        instr = ""
        fala_base = ""
        fala_reprov = ""
        fala_aprov = ""
        for b in node.get("blocos", []):
            t = _safe(b.get("instrução"))
            if "nível de consciência" in t.lower():
                instr = t
            f = _safe(b.get("fala"))
            if f and not fala_base:
                fala_base = f
            if "reprovação" in f.lower():
                fala_reprov = f
            if "não seguir com a compra" in f.lower():
                fala_aprov = f

        txt = (
            "cartilha (nível de consciência):\n"
            "- objetivo: entender maturidade do cliente (já falou com corretor? análise feita? reprovado? por quê?).\n"
            f"- regra: {_truncate(instr)}\n"
            "- exemplos:\n"
            f"  • {fala_base}\n"
            f"  • {fala_reprov}\n"
            f"  • {fala_aprov}"
        )
        return _truncate(txt, MAX_SNIPPET)

    # CONTEXTUALIZACAO
    node = _find(CONTEXT) or {}
    instr = _safe(node.get("instrução"))
    fala = _safe(node.get("fala"))
    txt = (
        "cartilha (contextualização + coleta de docs):\n"
        "- objetivo: explicar Minha Casa Minha Vida (até ~80% financiamento; resto = entrada, geralmente parcelável) e coletar documentos.\n"
        f"- regra: {_truncate(instr)}\n"
        "- documentos: contracheque do último mês; RG/CPF ou CNH; comprovante de residência; e-mail.\n"
        f"- exemplo:\n{fala}"
    )
    return _truncate(txt, MAX_SNIPPET)

# -------- heurística simples de avanço de etapa --------
def normalize(text):
    text = text.lower()
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    text = re.sub(r'[^a-z\s]', '', text)  # remove pontuação/números
    return text.strip()

def cidade_valida(user_msg: str) -> bool:
    m = normalize(user_msg)
    tokens = m.split()

    for c in CIDADES:
        norm_c = normalize(c)
        c_tokens = norm_c.split()

        # cidade de 1 palavra → checa se está nos tokens
        if len(c_tokens) == 1:
            if c_tokens[0] in tokens:
                return True

        # cidade de 2+ palavras → checa sequência exata nos tokens
        else:
            for i in range(len(tokens) - len(c_tokens) + 1):
                if tokens[i:i+len(c_tokens)] == c_tokens:
                    return True

    return False



def proxima_etapa(user_msg: str, etapa_atual: str) -> str:
    """
    heurística barata. segura e previsível.
    - boas-vindas -> filtrar
    - filtrar -> nivel quando detectar cidade válida OU já discutiu 1º imóvel/escritura/renda
    - nivel -> contextualização
    - contextualização -> permanece (última etapa)
    """
    m = normalize(user_msg or "")
    if etapa_atual == BOAS:
        return FILTRAR
    if etapa_atual == FILTRAR:
        if cidade_valida(user_msg) or "primeiro imovel" in m or "renda" in m or "escritura" in m:
            return NIVEL
        return FILTRAR
    if etapa_atual == NIVEL:
        return CONTEXT
    return CONTEXT  # mantém


# -------- util --------
def _truncate(s: str, n: int = 300) -> str:
    s = _safe(s)
    return (s if len(s) <= n else (s[: max(0, n - 1)] + "…"))
