"""Embedding generation for catalog items with fallbacks."""
from __future__ import annotations

import logging

import numpy as np

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_service = None


class EmbeddingService:
    def __init__(self):
        self.model = None
        self.backend = "hashing"
        self.dim = getattr(settings, "EMBEDDING_DIM", 384)
        self.model_name = getattr(settings, "EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        self._try_load()

    def _try_load(self):
        try:
            from fastembed import TextEmbedding

            model_name = getattr(settings, "EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
            self.model = TextEmbedding(model_name=model_name)
            try:
                test = list(self.model.embed(["test"]))[0]
                self.dim = len(test)
            except Exception:
                self.dim = getattr(settings, "EMBEDDING_DIM", 384)
            self.backend = "fastembed"
            self.model_name = model_name
            logger.info(f"Loaded embedding model {model_name} dim={self.dim} (fastembed)")
            return
        except Exception as e:
            logger.warning(f"fastembed unavailable ({e}), trying sentence-transformers")
        try:
            from sentence_transformers import SentenceTransformer

            model_name = getattr(settings, "EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            self.model = SentenceTransformer(model_name)
            self.dim = self.model.get_sentence_embedding_dimension()
            self.backend = "sentence-transformers"
            self.model_name = model_name
            logger.info(f"Loaded embedding model {model_name} dim={self.dim}")
        except Exception as e2:
            logger.warning(f"sentence-transformers unavailable ({e2}), using hashing embeddings")
            self.backend = "hashing"

    def embed_text(self, text: str) -> np.ndarray:
        if not text:
            text = ""
        if self.backend == "fastembed" and self.model is not None:
            try:
                embeddings = list(self.model.embed([text]))
                vec = embeddings[0]
                return np.asarray(vec, dtype=np.float32)
            except Exception as e:
                logger.warning(f"fastembed embed failed: {e}, falling back")
        if self.backend == "sentence-transformers" and self.model is not None:
            try:
                vec = self.model.encode(text or "", normalize_embeddings=True)
                return np.asarray(vec, dtype=np.float32)
            except Exception as e:
                logger.warning(f"sentence-transformers embed failed: {e}, falling back")
        return self._hash_embed(text)

    def _hash_embed(self, text: str):
        import hashlib
        import re

        _TOKEN_RE = re.compile(r"[a-z0-9]+")
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = _TOKEN_RE.findall(text.lower())
        for tok in tokens:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec


def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service


def build_title_text(title) -> str:
    """Build text for embedding from title metadata."""
    parts = []
    name = getattr(title, "title", None) or getattr(title, "name", "")
    if name:
        parts.append(name)
    if getattr(title, "original_title", None) and title.original_title != name:
        parts.append(title.original_title)
    if getattr(title, "tagline", None):
        parts.append(title.tagline)
    if getattr(title, "overview", None):
        overview = title.overview
        if len(overview) > 200:
            overview = overview[:200]
        parts.append(overview)
    if getattr(title, "director", None):
        parts.append(f"director {title.director}")
    if getattr(title, "created_by", None):
        parts.append(f"created by {title.created_by}")
    try:
        genres = [g.name for g in title.genres.all()]
        if genres:
            parts.append(" ".join(genres))
    except Exception:
        pass
    return " ".join(parts)


def embed_title(title, save: bool = True):
    svc = get_embedding_service()
    text = build_title_text(title)
    vec = svc.embed_text(text)
    if save:
        title.embedding = vec.tolist() if hasattr(vec, "tolist") else list(vec)
        title.embedding_model = svc.model_name
        title.embedding_updated_at = timezone.now()
        title.save(update_fields=["embedding", "embedding_model", "embedding_updated_at"])
    return vec
