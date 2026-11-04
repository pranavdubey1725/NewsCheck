from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"

_model: TextEmbedding | None = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(MODEL_NAME)
    return _model


def embed_passages(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _get_model().passage_embed(texts)]


def embed_query(text: str) -> list[float]:
    return next(iter(_get_model().query_embed(text))).tolist()