# carrega playbook.json e gera “cartilha” curta por etapa p/ injetar como system no GPT

from __future__ import annotations
import json, pathlib
import unicodedata
import re
from difflib import SequenceMatcher

PB_PATH = pathlib.Path("playbook.json")
FUZZY_THRESHOLD = 0.75
# etapas principais
BOAS = "BOAS_VINDAS"
CONTEXT = "CONTEXTUALIZACAO"
INDICA = "INDICACAO"
SUGES = "SUGESTAO"

# subetapas do FILTRAR
FILTRAR_CIDADE = "FILTRAR_CIDADE"
FILTRAR_PRIMEIRO = "FILTRAR_PRIMEIRO_IMOVEL"
FILTRAR_ESCRITURA = "FILTRAR_ESCRITURA"
FILTRAR_RENDA = "FILTRAR_RENDA"
FILTRAR_ENTRADA = "FILTRAR_ENTRADA"

ETAPAS = (
    BOAS,
    FILTRAR_CIDADE,
    SUGES,
    FILTRAR_PRIMEIRO,
    FILTRAR_ESCRITURA,
    FILTRAR_RENDA,
    FILTRAR_ENTRADA,
    INDICA,
    CONTEXT
)

# -------- carregamento básico --------
def _load() -> list:
    with PB_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

PLAYBOOK = _load()

# helpers pra achar blocos do json
def palavras_positivas() -> list[str]:
    return PLAYBOOK.get("palavras_chave", {}).get("positivo", [])

def palavras_negativas() -> list[str]:
    return PLAYBOOK.get("palavras_chave", {}).get("negativo", [])

def _gatilho_creci_node() -> dict:
    return PLAYBOOK.get("gatilhos_globais", {}).get("creci", {})  # seguro se não existir

def creci_padroes() -> list[str]:
    return _gatilho_creci_node().get("padroes", [])

def creci_resposta() -> str:
    return _gatilho_creci_node().get("resposta", "").strip()

def is_creci_question(msg: str) -> bool:
    """
    Detecta perguntas sobre CRECI de forma robusta, sem acento/caixa.
    """
    m = normalize(msg or "")
    # heurística simples: presença explícita de 'creci'
    if "creci" in m:
        return True
    # padrões adicionais vindos do playbook.json
    for p in creci_padroes():
        if normalize(p) in m:
            return True
    return False


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

def gerar_lista_cidades_texto() -> str:
    """
    Lê automaticamente a lista de cidades do playbook.json e devolve texto formatado com quebras de linha.
    """
    cidades = lista_cidades()
    if not cidades:
        return "(nenhuma cidade cadastrada no playbook.json)"
    corpo = "\n".join(cidades)
    return f"{corpo}."

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
    text = re.sub(r'[^a-z0-9\s]', '', text)  # mantém letras e números
    return text.strip()

def resposta_positiva(msg: str) -> bool:
    m = normalize(msg)
    return any(p in m for p in palavras_positivas())

def resposta_negativa(msg: str) -> bool:
    m = normalize(msg)
    return any(p in m for p in palavras_negativas())


def cidade_valida(user_msg: str) -> bool:
    m = normalize(user_msg)
    tokens = m.split()

    for c in CIDADES:
        norm_c = normalize(c)
        c_tokens = norm_c.split()

        if len(c_tokens) == 1:
            target = c_tokens[0]
            for tok in tokens:
                if tok == target or SequenceMatcher(None, tok, target).ratio() >= FUZZY_THRESHOLD:
                    return True
        else:
            target = norm_c
            for i in range(len(tokens) - len(c_tokens) + 1):
                window_tokens = tokens[i:i+len(c_tokens)]
                if window_tokens == c_tokens:
                    return True
                window = " ".join(window_tokens)
                if SequenceMatcher(None, window, target).ratio() >= FUZZY_THRESHOLD:
                    return True
    return False

def respondeu_primeiro_imovel(msg: str) -> bool:
    """
    Considera que o lead respondeu à pergunta 'é o primeiro imóvel?'
    se a mensagem contiver qualquer sinal de resposta positiva ou negativa.
    """
    return resposta_positiva(msg) or resposta_negativa(msg)

def respondeu_escritura(msg: str) -> bool:
    """
    Considera que o lead respondeu à pergunta sobre escritura
    se a mensagem contiver sinais de sim/não ou menções diretas à escritura.
    """
    m = normalize(msg)
    return (
        resposta_positiva(msg)
        or resposta_negativa(msg)
        or any(p in m for p in ["escriturado", "sem escritura"])
    )

def respondeu_renda(msg: str) -> bool:
    nums = [int(n) for n in re.findall(r"\d+", normalize(msg))]
    return bool(nums)

def extrair_renda(m: str) -> int:
    """
    Extrai a renda informada no texto, considerando formatos brasileiros:
    - "R$ 12.000,00" → 12000
    - "7 mil" → 7000
    - "12k" ou "12 K" → 12000
    - "750,00" → 750
    """
    m = m.lower().strip()

    # 1) Detecta formato com vírgula decimal (brasileiro: 12.000,00)
    match = re.search(r'(\d{1,3}(\.\d{3})+,\d{2})', m)
    if match:
        num = match.group(1)
        num = num.replace(".", "").replace(",", ".")  # vira "12000.00"
        return int(float(num))

    # 2) Detecta número com vírgula como decimal simples (ex: 750,00)
    match = re.search(r'(\d+,\d{2})', m)
    if match:
        num = match.group(1).replace(",", ".")
        return int(float(num))

    # 3) Detecta número com milhar em ponto (ex: "12.000")
    match = re.search(r'(\d{1,3}(\.\d{3})+)', m)
    if match:
        num = match.group(1).replace(".", "")
        return int(num)

    # 4) Detecta número simples (ex: "12000")
    match = re.search(r'(\d+)', m)
    if match:
        valor = int(match.group(1))
        # ajuste para "mil" ou "k"
        if "mil" in m and valor < 100:
            valor *= 1000
        if "k" in m:
            valor *= 1000
        return valor

    return 0

def respondeu_entrada(msg: str) -> bool:
    m = normalize(msg)
    return any(p in m for p in ["sim", "nao", "não", "entrada", "consigo", "tenho"])


def proxima_etapa(user_msg: str, etapa_atual: str) -> str:
    m = normalize(user_msg or "")
    renda = extrair_renda(m)
    lista_cidades_texto = gerar_lista_cidades_texto()


    if etapa_atual == BOAS:
        return FILTRAR_CIDADE

    # Se o lead disser uma cidade
    if etapa_atual == FILTRAR_CIDADE:
        if cidade_valida(user_msg):
            return FILTRAR_PRIMEIRO

        # cidade inválida → envia lista e muda pra SUGESTAO
        if re.search(r"\b(cidade|porto|novo|são|paulo|leopoldo|hamburgo|canoas|viamão|alvorada|gravataí|esteio|sapucaia|guaíba|nova)\b", m):
            print("[DEBUG] Cidade inválida detectada, enviando lista de cidades.")
            return SUGES + "|lista_cidades:" + lista_cidades_texto

        # se não mencionou cidade → permanece na etapa
        return FILTRAR_CIDADE
    
    # sugestões
    if etapa_atual == SUGES:

        if resposta_positiva(user_msg):
            return FILTRAR_CIDADE

        if cidade_valida(user_msg):
            return FILTRAR_PRIMEIRO

        if re.search(r"\b(cidade|porto|novo|são|paulo|leopoldo|hamburgo|canoas|viamão|alvorada|gravataí|esteio|sapucaia|guaíba|nova)\b", m):
            return SUGES + "|lista_cidades:" + lista_cidades_texto

        return INDICA

    if etapa_atual == FILTRAR_PRIMEIRO:
        if respondeu_primeiro_imovel(user_msg):
            if resposta_positiva(user_msg):
                return CONTEXT  # primeiro imóvel → vai direto pro nível de consciência
            return FILTRAR_ESCRITURA
        return FILTRAR_PRIMEIRO

    if etapa_atual == FILTRAR_ESCRITURA:
        if respondeu_escritura(user_msg):
            if resposta_negativa(user_msg):
                return CONTEXT
            return FILTRAR_RENDA
        return FILTRAR_ESCRITURA

    if etapa_atual == FILTRAR_RENDA:
        renda = extrair_renda(user_msg.lower())
        if renda > 0:
            print(f"[DEBUG] Renda detectada: {renda}")
            return CONTEXT if renda > 6500 else FILTRAR_ENTRADA
        return FILTRAR_RENDA

    if etapa_atual == FILTRAR_ENTRADA:
        if respondeu_entrada(user_msg):
            return CONTEXT
        return FILTRAR_ENTRADA

    return CONTEXT




# # -------- util --------
# def _truncate(s: str, n: int = 300) -> str:
#     s = _safe(s)
#     return (s if len(s) <= n else (s[: max(0, n - 1)] + "…"))
