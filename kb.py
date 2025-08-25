import json, torch
from sentence_transformers import SentenceTransformer, util
from typing import List, Tuple
from config import MODEL_NAME, FAQ_PATH, TOPK

# singletons
_model = SentenceTransformer(MODEL_NAME)

_perguntas: list[str] = []
_respostas: list[str] = []
_embeddings: torch.Tensor | None = None  # [N, d] normalizado

def _normalize(t: torch.Tensor) -> torch.Tensor:
    return torch.nn.functional.normalize(t, p=2, dim=1)

def load_kb() -> None:
    global _perguntas, _respostas, _embeddings
    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        base = json.load(f)
    _perguntas = [item.get("pergunta","") for item in base]
    _respostas = [item.get("resposta","") for item in base]
    embs = torch.tensor([item["embedding"] for item in base], dtype=torch.float32)
    _embeddings = _normalize(embs)

def encode_query(q: str) -> torch.Tensor:
    v = _model.encode(q, convert_to_tensor=True, normalize_embeddings=True)  # [d]
    if _embeddings is not None and v.dtype != _embeddings.dtype:
        v = v.to(dtype=_embeddings.dtype)
    return v

def top_match(q_emb: torch.Tensor) -> Tuple[int, float]:
    scores = util.cos_sim(q_emb, _embeddings)[0]
    best_idx = int(torch.argmax(scores).item())
    best_score = float(scores[best_idx].item())
    return best_idx, best_score

def topk(q_emb: torch.Tensor, k: int = TOPK) -> tuple[list[int], list[float]]:
    scores = util.cos_sim(q_emb, _embeddings)[0]
    k = min(k, scores.numel())
    vals, idxs = torch.topk(scores, k=k)
    return idxs.tolist(), [float(v.item()) for v in vals]

def get_answer(i: int) -> str:
    return _respostas[i]

def get_ctx(indices: List[int]) -> list[str]:
    ctx = []
    for i in indices:
        q = _perguntas[i]
        r = _respostas[i]
        ctx.append(f"Q: {q}\nA: {r}" if q else r)
    return ctx

def size() -> int:
    return len(_respostas)

# carga inicial
load_kb()
