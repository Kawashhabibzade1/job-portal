IVF_QUERY_TERMS = [
    "ivf",
    "biotechnologie",
    "labor",
    "biologielaborant",
    "molekularbiologie",
    "medizinisches labor",
]

IVF_RELEVANCE_TERMS = [
    "analytik",
    "androlog",
    "biolog",
    "biomed",
    "biotech",
    "bta",
    "charite",
    "chemie",
    "diagnost",
    "embryo",
    "fertil",
    "humangenetik",
    "ivf",
    "labor",
    "lab",
    "molekular",
    "mtl",
    "mtla",
    "pharma",
    "reproduktion",
    "serologie",
    "synlab",
    "zell",
]


def expanded_job_queries(query: str) -> list[str]:
    normalized = " ".join(query.lower().replace("-", " ").split())
    compact = normalized.replace(" ", "")

    if (
        normalized in {"ivf", "ifv"}
        or "ivf lab" in normalized
        or "ifv lab" in normalized
        or compact.startswith("ivflab")
        or compact.startswith("ifvlab")
    ):
        return IVF_QUERY_TERMS

    return [query]


def expanded_relevance_terms(query: str) -> list[str]:
    return IVF_RELEVANCE_TERMS if len(expanded_job_queries(query)) > 1 else []
