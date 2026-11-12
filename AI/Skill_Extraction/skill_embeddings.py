
"""Generate semantic embeddings for normalized Road2Hire skills."""

from functools import lru_cache
import os
from typing import Any
import warnings

# Suppress progress bars and third-party notices by default unless verbose is explicitly enabled
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

warnings.filterwarnings(
    "ignore",
    message=r".*unauthenticated requests to the HF Hub.*",
)
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module=r"huggingface_hub.*",
)

try:
    import huggingface_hub.utils.logging as hf_logging
    if os.environ.get("ROAD2HIRE_VERBOSE") != "1":
        hf_logging.set_verbosity_error()
except ImportError:
    pass

try:
    import transformers.utils.logging as t_logging
    if os.environ.get("ROAD2HIRE_VERBOSE") != "1":
        t_logging.set_verbosity_error()
except ImportError:
    pass


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=2)
def _load_model(model_name: str = DEFAULT_MODEL_NAME) -> Any:
    """Load and cache the pretrained sentence embedding model."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError("Sentence Transformers is required for non-empty skill embeddings. Install it using: python -m pip install -r Backend/Requirements-ai-test.txt") from exc

    return SentenceTransformer(model_name)


def generate_skill_embeddings(
    skills: list[str],
    model_name: str = DEFAULT_MODEL_NAME,
) -> dict[str, Any]:
    """
    Generate semantic embeddings for a list of skill names.

    Returns each skill with its vector and the model used.
    Duplicate skill names are embedded only once per call.
    """
    if not isinstance(skills, list):
        raise TypeError("skills must be a list of strings.")

    cleaned_skills = []

    for skill in skills:
        if not isinstance(skill, str):
            raise TypeError("Every skill must be a string.")
        if skill.strip():
            cleaned_skills.append(skill.strip())

    unique_skills = list(dict.fromkeys(cleaned_skills))

    if not unique_skills:
        return {
            "model_name": model_name,
            "embedding_dimension": 384,
            "skills": [],
        }

    model = _load_model(model_name)
    vectors = model.encode(
        unique_skills,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    embedded_skills = [
        {
            "skill": skill,
            "embedding": vector.tolist(),
        }
        for skill, vector in zip(unique_skills, vectors)
    ]

    return {
        "model_name": model_name,
        "embedding_dimension": int(vectors.shape[1]),
        "skills": embedded_skills,
    }


def cosine_similarity(
    first_embedding: list[float],
    second_embedding: list[float],
) -> float:
    """Calculate cosine similarity between two embedding vectors."""
    if not first_embedding or not second_embedding:
        raise ValueError("Embedding vectors must not be empty.")

    if len(first_embedding) != len(second_embedding):
        raise ValueError("Embedding vectors must have equal dimensions.")

    dot_product = sum(a * b for a, b in zip(first_embedding, second_embedding))
    first_norm = sum(value * value for value in first_embedding) ** 0.5
    second_norm = sum(value * value for value in second_embedding) ** 0.5

    if first_norm == 0 or second_norm == 0:
        raise ValueError("Embedding vectors must not be zero vectors.")

    return dot_product / (first_norm * second_norm)
