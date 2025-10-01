# carrega playbook.json e gera “cartilha” curta por etapa p/ injetar como system no GPT

from __future__ import annotations
import json, pathlib
import unicodedata
import re

PB_PATH = pathlib.Path("playbook.json")

# etapas principais
BOAS = "BOAS_VINDAS"
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

# -------- carregamento básico --------
def _load() -> list:
    with PB_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

PLAYBOOK = _load()

# helpers pra achar blocos do json
def _find(etapa_nome_pt: str) -> dict | None:
    return PLAYBOOK.get(etapa_nome_pt)


def _safe(s: str | None) -> str:
    return (s or "").strip()

# cidades (usadas em FILTRAR_CIDADE)
def _find_filtrar_cidade_node() -> dict | None:
    return _find(FILTRAR_CIDADE)

def lista_cidades() -> list[str]:
    """
    Retorna a lista CANÔNICA de cidades do playbook.json (campo 'lista_cidades').
    """
    node = _find_filtrar_cidade_node()
    if not node:
        return []
    return node.get("lista_cidades", [])  # <- antes estava 'cidades'



CIDADES = set(lista_cidades())

# -------- geração de snippet curto por etapa --------
MAX_SNIPPET = 1200

def build_snippet(etapa: str) -> str:
    etapa = (etapa or BOAS).upper()
    if etapa not in ETAPAS:
        etapa = BOAS

    node = _find(etapa)
    if not node:
        return ""

    # devolve o bloco completo em JSON (sem estilo)
    return json.dumps(node, ensure_ascii=False, indent=2)

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

        if len(c_tokens) == 1:
            if c_tokens[0] in tokens:
                return True
        else:
            for i in range(len(tokens) - len(c_tokens) + 1):
                if tokens[i:i+len(c_tokens)] == c_tokens:
                    return True
    return False

def respondeu_primeiro_imovel(msg: str) -> bool:
    m = normalize(msg)
    return any(p in m for p in ["sim", "primeiro", "não", "nao", "nao é", "não é"])

def respondeu_escritura(msg: str) -> bool:
    m = normalize(msg)
    return any(p in m for p in ["sim", "não", "nao", "escriturado", "sem escritura"])

def respondeu_renda(msg: str) -> bool:
    nums = [int(n) for n in re.findall(r"\d+", normalize(msg))]
    return bool(nums)

def extrair_renda(m: str) -> int:
    # normaliza
    m = m.replace(".", "").replace(",", "")
    nums = re.findall(r"\d+", m)
    if not nums:
        return 0
    valor = max(int(n) for n in nums)

    if "mil" in m and valor < 100:  # "7 mil" vira 7000
        valor *= 1000
    if "k" in m:
        valor *= 1000
    return valor


def respondeu_entrada(msg: str) -> bool:
    m = normalize(msg)
    return any(p in m for p in ["sim", "nao", "não", "entrada", "consigo", "tenho"])


def proxima_etapa(user_msg: str, etapa_atual: str) -> str:
    m = normalize(user_msg or "")
    renda = extrair_renda(m)



    if etapa_atual == BOAS:
        return FILTRAR_CIDADE

    if etapa_atual == FILTRAR_CIDADE:
        return FILTRAR_PRIMEIRO if cidade_valida(user_msg) else FILTRAR_CIDADE

    if etapa_atual == FILTRAR_PRIMEIRO:
        if respondeu_primeiro_imovel(user_msg):
            if "sim" in m:
                return NIVEL  # primeiro imóvel → vai direto pro nível de consciência
            return FILTRAR_ESCRITURA
        return FILTRAR_PRIMEIRO

    if etapa_atual == FILTRAR_ESCRITURA:
        if respondeu_escritura(user_msg):
            if "nao" in m or "não" in m:
                return NIVEL
            return FILTRAR_RENDA
        return FILTRAR_ESCRITURA

    if etapa_atual == FILTRAR_RENDA:
        if respondeu_renda(user_msg):
            renda = extrair_renda(user_msg.lower())
            return NIVEL if renda > 6500 else FILTRAR_ENTRADA
        return FILTRAR_RENDA


    if etapa_atual == FILTRAR_ENTRADA:
        if respondeu_entrada(user_msg):
            return NIVEL
        return FILTRAR_ENTRADA

    # NIVEL — agora mantém até classificar a resposta
    if etapa_atual == NIVEL:
        if any(p in m for p in ["primeira", "nunca", "não", "nao"]):
            return CONTEXT
        if any(p in m for p in ["reprovei", "reprovado", "negado"]):
            return CONTEXT
        if any(p in m for p in ["aprovado", "aprovou", "sim", "ok"]):
            return CONTEXT
        return NIVEL  # fica pedindo até entender

    return CONTEXT


# -------- util --------
def _truncate(s: str, n: int = 300) -> str:
    s = _safe(s)
    return (s if len(s) <= n else (s[: max(0, n - 1)] + "…"))
