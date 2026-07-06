from __future__ import annotations

import datetime as dt
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


INDEX_FILE = ".fix_memory_vectors.json"
TOKEN_RE = re.compile(r"[a-zA-Z0-9_./\\:-]+|[\u4e00-\u9fff]+")
CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+")


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in TOKEN_RE.findall(text):
        lowered = raw.lower()
        if len(lowered) >= 2:
            tokens.append(lowered)
        if re.search(r"[\u4e00-\u9fff]", raw):
            chars = [char for char in raw if "\u4e00" <= char <= "\u9fff"]
            tokens.extend("".join(chars[i : i + 2]) for i in range(max(0, len(chars) - 1)))
            tokens.extend("".join(chars[i : i + 3]) for i in range(max(0, len(chars) - 2)))
        else:
            parts = [part.lower() for part in CAMEL_RE.findall(raw) if len(part) >= 2]
            tokens.extend(parts)
    return tokens


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def snippet(text: str, query_tokens: list[str], width: int = 180) -> str:
    lowered = text.lower()
    index = -1
    for token in sorted(query_tokens, key=len, reverse=True):
        found = lowered.find(token.lower())
        if found >= 0:
            index = found
            break
    if index < 0:
        return " ".join(text.split())[:width]
    start = max(0, index - width // 3)
    end = min(len(text), start + width)
    return " ".join(text[start:end].split())


def iter_markdown(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files = [
        path
        for path in root.rglob("*.md")
        if not any(part.startswith(".") for part in path.relative_to(root).parts)
    ]
    return sorted(files, key=lambda path: str(path.relative_to(root)).lower())


def file_meta(path: Path, root: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
    }


def normalise(vector: dict[str, float]) -> dict[str, float]:
    length = math.sqrt(sum(weight * weight for weight in vector.values()))
    if not length:
        return {}
    return {term: weight / length for term, weight in vector.items()}


def build_index(root: Path, write: bool = True) -> dict[str, Any]:
    files = iter_markdown(root)
    documents = []
    doc_tokens: list[Counter[str]] = []
    document_frequency: Counter[str] = Counter()

    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        tokens = Counter(tokenize(path.name + "\n" + text))
        if not tokens:
            continue
        doc_tokens.append(tokens)
        document_frequency.update(tokens.keys())
        documents.append(
            {
                **file_meta(path, root),
                "title": first_heading(text, path.stem),
                "text": text,
            }
        )

    total_docs = max(1, len(documents))
    idf = {
        term: math.log((1 + total_docs) / (1 + count)) + 1
        for term, count in document_frequency.items()
    }

    indexed_docs = []
    for document, tokens in zip(documents, doc_tokens):
        weighted = {
            term: (1 + math.log(count)) * idf[term]
            for term, count in tokens.items()
            if count > 0
        }
        indexed_docs.append(
            {
                "relative_path": document["relative_path"],
                "mtime_ns": document["mtime_ns"],
                "size": document["size"],
                "title": document["title"],
                "snippet_source": document["text"][:4000],
                "vector": normalise(weighted),
            }
        )

    index = {
        "version": 1,
        "kind": "tfidf-cosine",
        "built_at": dt.datetime.now().replace(microsecond=0).isoformat(),
        "documents_meta": [file_meta(path, root) for path in files],
        "idf": idf,
        "documents": indexed_docs,
    }

    if write:
        (root / INDEX_FILE).write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return index


def load_index(root: Path) -> dict[str, Any] | None:
    path = root / INDEX_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def index_is_fresh(index: dict[str, Any], root: Path) -> bool:
    current = [file_meta(path, root) for path in iter_markdown(root)]
    return index.get("version") == 1 and index.get("documents_meta") == current


def load_or_build_index(root: Path) -> dict[str, Any]:
    index = load_index(root)
    if index and index_is_fresh(index, root):
        return index
    return build_index(root)


def vectorise_query(query: str, idf: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    tokens = tokenize(query)
    counts = Counter(tokens)
    if not counts:
        return {}, tokens
    default_idf = math.log(2) + 1
    weighted = {
        term: (1 + math.log(count)) * float(idf.get(term, default_idf))
        for term, count in counts.items()
    }
    return normalise(weighted), tokens


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(term, 0.0) for term, weight in left.items())


def search_vectors(query: str, limit: int = 5, root: Path | None = None) -> list[dict[str, Any]]:
    root = root or Path.cwd()
    index = load_or_build_index(root)
    query_vector, query_tokens = vectorise_query(query, index.get("idf", {}))
    if not query_vector:
        return []

    results = []
    for document in index.get("documents", []):
        score = cosine(query_vector, document.get("vector", {}))
        if score <= 0:
            continue
        path = root / document["relative_path"]
        results.append(
            {
                "score": round(score, 6),
                "vector_score": round(score, 6),
                "path": str(path),
                "relative_path": document["relative_path"],
                "title": document["title"],
                "snippet": snippet(document.get("snippet_source", ""), query_tokens),
                "mode": "vector",
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:limit]
