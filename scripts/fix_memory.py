from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path

try:
    from . import vector_search
except ImportError:
    import vector_search


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_ROOT = BASE_DIR / "data"


def memory_root() -> Path:
    return Path(os.environ.get("FIX_MEMORY_ROOT", DEFAULT_MEMORY_ROOT)).expanduser().resolve()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\u4e00-\u9fff]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:60] or "fix-case"


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def frontmatter_list(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def frontmatter_value(value: str | None) -> str:
    return json.dumps(value or "", ensure_ascii=False)


def ensure_dirs(root: Path) -> None:
    for name in ("fixes", "failed-attempts", "commands"):
        (root / name).mkdir(parents=True, exist_ok=True)


def build_case(args: argparse.Namespace) -> str:
    now = dt.datetime.now().replace(microsecond=0).isoformat()
    tags = parse_tags(args.tags)
    status = args.status
    title = args.title

    return f"""---
title: {frontmatter_value(title)}
project: {frontmatter_value(args.project)}
language: {frontmatter_value(args.language)}
framework: {frontmatter_value(args.framework)}
command: {frontmatter_value(args.command)}
source_tool: {frontmatter_value(args.source_tool)}
created_at: {frontmatter_value(now)}
tags: {frontmatter_list(tags)}
status: {frontmatter_value(status)}
---

# 修复案例：{title}

## 场景

- 项目：{args.project or ''}
- 语言：{args.language or ''}
- 框架：{args.framework or ''}
- 触发命令：{args.command or ''}
- 系统/环境：

## 报错

```txt
{args.error or ''}
```

## 现象

-

## 根因


## 相关文件

-

## 修改方案


## 关键 diff

```diff

```

## 验证方式

```bash

```

结果：

## 复用建议

下次遇到类似问题，优先检查：

1.
2.
3.

## 失败尝试

-

## 敏感信息检查

- 是否包含 token / key / password：需要人工确认
- 是否包含隐私路径或账号信息：需要人工确认
"""


def create_case(args: argparse.Namespace) -> Path:
    root = memory_root()
    ensure_dirs(root)
    bucket = "failed-attempts" if args.status == "failed" else "fixes"
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = root / bucket / f"{timestamp}-{slugify(args.title)}.md"
    path.write_text(build_case(args), encoding="utf-8")
    return path


def new_case(args: argparse.Namespace) -> None:
    path = create_case(args)
    print(path)


def iter_cases(root: Path) -> list[Path]:
    if not root.exists():
        return []
    buckets = [root / "fixes", root / "failed-attempts", root / "commands"]
    files: list[Path] = []
    for bucket in buckets:
        if bucket.exists():
            files.extend(bucket.rglob("*.md"))
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def score_text(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    score = 0
    for term in terms:
        if not term:
            continue
        count = lowered.count(term.lower())
        score += count * max(1, len(term))
    return score


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def snippet(text: str, terms: list[str], width: int = 160) -> str:
    lowered = text.lower()
    index = -1
    for term in terms:
        found = lowered.find(term.lower())
        if found >= 0:
            index = found
            break
    if index < 0:
        return " ".join(text.split())[:width]
    start = max(0, index - width // 3)
    end = min(len(text), start + width)
    return " ".join(text[start:end].split())


def find_keyword_cases(query: str, limit: int = 5, root: Path | None = None) -> list[dict[str, object]]:
    root = root or memory_root()
    terms = [term for term in re.split(r"\s+", query.strip()) if term]
    results = []
    for path in iter_cases(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        score = score_text(path.name + "\n" + text, terms)
        if score:
            results.append((score, path, text))

    results.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "score": score,
            "path": str(path),
            "relative_path": path.relative_to(root).as_posix(),
            "title": first_heading(text, path.stem),
            "snippet": snippet(text, terms),
            "keyword_score": score,
            "mode": "keyword",
        }
        for score, path, text in results[:limit]
    ]


def find_vector_cases(query: str, limit: int = 5, root: Path | None = None) -> list[dict[str, object]]:
    return vector_search.search_vectors(query, limit, root or memory_root())


def find_hybrid_cases(query: str, limit: int = 5, root: Path | None = None) -> list[dict[str, object]]:
    root = root or memory_root()
    keyword = find_keyword_cases(query, max(limit * 4, 20), root)
    vector = find_vector_cases(query, max(limit * 4, 20), root)
    max_keyword = max((float(item.get("keyword_score", 0)) for item in keyword), default=0.0)
    merged: dict[str, dict[str, object]] = {}

    for item in keyword:
        key = str(item["relative_path"])
        keyword_norm = float(item.get("keyword_score", 0)) / max_keyword if max_keyword else 0.0
        merged[key] = {
            **item,
            "keyword_score": item.get("keyword_score", 0),
            "vector_score": 0.0,
            "score": round(keyword_norm * 0.45, 6),
            "mode": "hybrid",
        }

    for item in vector:
        key = str(item["relative_path"])
        existing = merged.get(key, {})
        vector_score = float(item.get("vector_score", item.get("score", 0.0)))
        keyword_score = float(existing.get("keyword_score", 0.0))
        keyword_norm = keyword_score / max_keyword if max_keyword else 0.0
        merged[key] = {
            **item,
            **existing,
            "snippet": existing.get("snippet") or item.get("snippet", ""),
            "keyword_score": keyword_score,
            "vector_score": round(vector_score, 6),
            "score": round(keyword_norm * 0.45 + vector_score * 0.55, 6),
            "mode": "hybrid",
        }

    results = sorted(merged.values(), key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return results[:limit]


def find_cases(query: str, limit: int = 5, root: Path | None = None, mode: str = "hybrid") -> list[dict[str, object]]:
    if mode == "keyword":
        return find_keyword_cases(query, limit, root)
    if mode == "vector":
        return find_vector_cases(query, limit, root)
    if mode == "hybrid":
        return find_hybrid_cases(query, limit, root)
    raise ValueError(f"Unknown search mode: {mode}")


def search_cases(args: argparse.Namespace) -> None:
    results = find_cases(args.query, args.limit, mode=args.mode)
    for result in results:
        print(f"[{result['score']}] {result['relative_path']}")
        print(f"    {result['title']}")
        print(f"    {result['snippet']}")

    if not results:
        print("No matching fix cases found.")


def list_recent(limit: int = 10, root: Path | None = None) -> list[dict[str, str]]:
    root = root or memory_root()
    recent = []
    for path in iter_cases(root)[:limit]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        recent.append(
            {
                "path": str(path),
                "relative_path": path.relative_to(root).as_posix(),
                "title": first_heading(text, path.stem),
            }
        )
    return recent


def recent_cases(args: argparse.Namespace) -> None:
    for item in list_recent(args.limit):
        print(item["relative_path"])
        print(f"    {item['title']}")


def show_case(args: argparse.Namespace) -> None:
    try:
        print(read_case(args.path))
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc


def read_case(case_path: str) -> str:
    root = memory_root()
    requested = Path(case_path)
    candidates = []
    if requested.is_absolute():
        candidates.append(requested)
    else:
        candidates.append(root / requested)
        candidates.extend(iter_cases(root))

    for path in candidates:
        relative = ""
        if path.exists():
            try:
                relative = str(path.relative_to(root)).replace("\\", "/")
            except ValueError:
                relative = ""
        if path.exists() and (path.name == requested.name or path == requested or relative == case_path.replace("\\", "/")):
            return path.read_text(encoding="utf-8", errors="ignore")
    raise FileNotFoundError(f"Case not found: {case_path}")


def rebuild_vector_index(args: argparse.Namespace) -> None:
    root = memory_root()
    index = vector_search.build_index(root)
    print(root / vector_search.INDEX_FILE)
    print(f"documents: {len(index.get('documents', []))}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local fix memory MVP")
    sub = parser.add_subparsers(required=True)

    new_parser = sub.add_parser("new", help="create a fix case markdown file")
    new_parser.add_argument("--title", required=True)
    new_parser.add_argument("--project", default="")
    new_parser.add_argument("--language", default="")
    new_parser.add_argument("--framework", default="")
    new_parser.add_argument("--command", default="")
    new_parser.add_argument("--error", default="")
    new_parser.add_argument("--tags", default="")
    new_parser.add_argument("--source-tool", default="")
    new_parser.add_argument("--status", choices=["fixed", "failed", "partial"], default="fixed")
    new_parser.set_defaults(func=new_case)

    search_parser = sub.add_parser("search", help="search fix cases")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.add_argument("--mode", choices=["hybrid", "keyword", "vector"], default="hybrid")
    search_parser.set_defaults(func=search_cases)

    recent_parser = sub.add_parser("recent", help="list recent cases")
    recent_parser.add_argument("--limit", type=int, default=10)
    recent_parser.set_defaults(func=recent_cases)

    show_parser = sub.add_parser("show", help="show a case by path or filename")
    show_parser.add_argument("path")
    show_parser.set_defaults(func=show_case)

    index_parser = sub.add_parser("rebuild-index", help="rebuild the local vector index")
    index_parser.set_defaults(func=rebuild_vector_index)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
