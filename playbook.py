# carrega playbook.json e gera “cartilha” curta por etapa p/ injetar como system no GPT

from __future__ import annotations
import json, pathlib

PB_PATH = pathlib.Path("playbook.json")

# etapas suportadas (use estas strings no estado da sessão)
BOAS = "BOAS_VINDAS"
FILTRAR = "FILTRAR_CLIENTE"
NIVEL = "NIVEL_DE_CONSCIENCIA"
CONTEXT = "CONTEXTUALIZACAO"

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
            "- objetivo: abordar lead de tráfego pago, dizer quem somos e por que o contato.\n"
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
            "  1) perguntar cidade; 2) se fora, encerrar; 3) se dentro, perguntar se é 1º imóvel;\n"
            "  4) se não for 1º, checar escritura; 5) se escriturado, perguntar renda;\n"
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
def proxima_etapa(user_msg: str, etapa_atual: str) -> str:
    """
    heurística barata. segura e previsível.
    - boas-vindas -> filtrar
    - filtrar -> nivel quando detectar cidade válida OU já discutiu 1º imóvel/escritura/renda
    - nivel -> contextualização
    - contextualização -> permanece (última etapa)
    """
    m = (user_msg or "").lower()
    if etapa_atual == BOAS:
        return FILTRAR
    if etapa_atual == FILTRAR:
        if any(c.lower() in m for c in CIDADES) or "primeiro imóvel" in m or "renda" in m or "escritura" in m:
            return NIVEL
        return FILTRAR
    if etapa_atual == NIVEL:
        return CONTEXT
    return CONTEXT  # mantém

# -------- util --------
def _truncate(s: str, n: int = 300) -> str:
    s = _safe(s)
    return (s if len(s) <= n else (s[: max(0, n - 1)] + "…"))
