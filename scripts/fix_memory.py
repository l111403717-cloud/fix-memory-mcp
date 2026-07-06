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

MEMORY_BUCKETS = {
    "bug": "fixes",
    "fix": "fixes",
    "failed_attempt": "failed-attempts",
    "command": "commands",
    "preference": "preferences",
    "environment": "environments",
    "workflow": "workflows",
    "interview": "interviews",
    "project": "projects",
    "prompt": "prompts",
    "episode": "episodes",
}

STRONG_MEMORY_TYPES = {"preference", "environment", "interview", "project"}
ENVIRONMENT_HINT_RE = re.compile(
    r"(?:\b(?:api|proxy|ccswitch|port|path|python|node|npm|pnpm|uv|venv|mcp|token|key|cookie|password|account)\b|账号|路径|端口|中转|环境|模型|代理|密钥)",
    re.IGNORECASE,
)


def memory_root() -> Path:
    return Path(os.environ.get("FIX_MEMORY_ROOT", DEFAULT_MEMORY_ROOT)).expanduser().resolve()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\u4e00-\u9fff]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:60] or "memory"


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def frontmatter_value(value: object) -> str:
    return json.dumps(value if value is not None else "", ensure_ascii=False)


def frontmatter_list(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def ensure_dirs(root: Path) -> None:
    for bucket in sorted(set(MEMORY_BUCKETS.values())):
        (root / bucket).mkdir(parents=True, exist_ok=True)


def bucket_for_memory(memory_type: str, status: str = "") -> str:
    if status == "failed":
        return "failed-attempts"
    return MEMORY_BUCKETS.get(memory_type, "episodes")


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    marker = "\n---"
    end = text.find(marker, 4)
    if end < 0:
        return {}, text

    raw = text[4:end].strip().splitlines()
    body_start = end + len(marker)
    if body_start < len(text) and text[body_start : body_start + 1] == "\n":
        body_start += 1
    body = text[body_start:]

    meta: dict[str, object] = {}
    for line in raw:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        try:
            meta[key.strip()] = json.loads(value)
        except json.JSONDecodeError:
            meta[key.strip()] = value.strip('"')
    return meta, body


def dump_frontmatter(meta: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {frontmatter_value(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def write_memory_file(path: Path, meta: dict[str, object], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_frontmatter(meta) + body.lstrip(), encoding="utf-8")


def now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def base_meta(
    *,
    title: str,
    memory_type: str,
    memory_status: str,
    confidence: str,
    project: str = "",
    language: str = "",
    framework: str = "",
    command: str = "",
    source_tool: str = "",
    scope: str = "global",
    sensitivity: str = "private",
    tags: list[str] | None = None,
    status: str = "active",
) -> dict[str, object]:
    timestamp = now_iso()
    return {
        "title": title,
        "memory_type": memory_type,
        "memory_status": memory_status,
        "occurrence_count": 1,
        "first_seen": timestamp,
        "last_seen": timestamp,
        "confidence": confidence,
        "scope": scope,
        "sensitivity": sensitivity,
        "project": project,
        "language": language,
        "framework": framework,
        "command": command,
        "source_tool": source_tool,
        "created_at": timestamp,
        "tags": tags or [],
        "status": status,
    }


def build_case(args: argparse.Namespace) -> str:
    meta = base_meta(
        title=args.title,
        memory_type=getattr(args, "memory_type", "bug"),
        memory_status=getattr(args, "memory_status", "active"),
        confidence=getattr(args, "confidence", "medium"),
        project=getattr(args, "project", ""),
        language=getattr(args, "language", ""),
        framework=getattr(args, "framework", ""),
        command=getattr(args, "command", ""),
        source_tool=getattr(args, "source_tool", ""),
        scope=getattr(args, "scope", "global"),
        sensitivity=getattr(args, "sensitivity", "private"),
        tags=parse_tags(getattr(args, "tags", "")),
        status=getattr(args, "status", "fixed"),
    )
    meta["first_seen"] = getattr(args, "first_seen", meta["first_seen"])
    meta["last_seen"] = getattr(args, "last_seen", meta["last_seen"])
    meta["occurrence_count"] = int(getattr(args, "occurrence_count", 1))

    body = f"""# 修复案例：{args.title}

## 场景

- 项目：{getattr(args, "project", "") or ""}
- 语言：{getattr(args, "language", "") or ""}
- 框架：{getattr(args, "framework", "") or ""}
- 触发命令：{getattr(args, "command", "") or ""}
- 系统/环境：

## 报错

```txt
{getattr(args, "error", "") or ""}
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
    return dump_frontmatter(meta) + body


def create_case(args: argparse.Namespace) -> Path:
    root = memory_root()
    ensure_dirs(root)
    bucket = bucket_for_memory(getattr(args, "memory_type", "bug"), getattr(args, "status", "fixed"))
    path = root / bucket / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(args.title)}.md"
    path.write_text(build_case(args), encoding="utf-8")
    vector_search.build_index(root)
    return path


def new_case(args: argparse.Namespace) -> None:
    print(create_case(args))


def assess_memory_value(
    memory_type: str,
    title: str,
    content: str,
    *,
    verified: bool = False,
    repeat_observed: bool = False,
    duration_minutes: int = 0,
    user_requested: bool = False,
    occurrence_count: int = 1,
) -> dict[str, object]:
    text = f"{title}\n{content}"
    reasons: list[str] = []

    if user_requested:
        reasons.append("user explicitly asked to remember it")
    if repeat_observed or occurrence_count >= 2:
        reasons.append("it has repeated at least twice")
    if duration_minutes >= 10:
        reasons.append("it cost at least 10 minutes")
    if verified and memory_type in {"bug", "fix", "failed_attempt"}:
        reasons.append("the fix was verified")
    if memory_type in STRONG_MEMORY_TYPES:
        reasons.append(f"{memory_type} memory is durable by default")
    if memory_type == "workflow" and (repeat_observed or occurrence_count >= 2):
        reasons.append("workflow repeated enough to become reusable")
    if ENVIRONMENT_HINT_RE.search(text):
        reasons.append("it involves environment/API/path/account/tool configuration")

    if reasons:
        return {
            "decision": "save",
            "memory_status": "active",
            "confidence": "high" if len(reasons) >= 2 else "medium",
            "reasons": reasons,
        }

    if memory_type in {"episode", "workflow", "prompt", "bug", "fix"}:
        return {
            "decision": "candidate",
            "memory_status": "candidate",
            "confidence": "low",
            "reasons": ["possibly useful later, but not yet proven durable"],
        }

    return {
        "decision": "skip",
        "memory_status": "archived",
        "confidence": "low",
        "reasons": ["no strong long-term value signal"],
    }


def assess_memory(args: argparse.Namespace) -> None:
    result = assess_memory_value(
        args.memory_type,
        args.title,
        args.content,
        verified=args.verified,
        repeat_observed=args.repeat_observed,
        duration_minutes=args.duration_minutes,
        user_requested=args.user_requested,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_memory_body(args: argparse.Namespace, assessment: dict[str, object]) -> str:
    timestamp = now_iso()
    evidence = args.evidence or args.content
    return f"""# 记忆：{args.title}

## 类型

{args.memory_type}

## 内容

{args.content}

## 证据

- {evidence}

## 写入闸门判断

- decision: {assessment["decision"]}
- memory_status: {assessment["memory_status"]}
- confidence: {assessment["confidence"]}
- reasons: {", ".join(str(reason) for reason in assessment["reasons"])}

## 复用建议

以后遇到类似问题，先搜索这条 memory，再决定是否继续调试、询问用户或更新记录。

## 发生记录

- {timestamp}: {evidence}

## 敏感信息检查

- 是否包含 token / key / password：需要人工确认
- 是否包含隐私路径或账号信息：需要人工确认
"""


def memory_meta(args: argparse.Namespace, assessment: dict[str, object]) -> dict[str, object]:
    status = "active" if assessment["memory_status"] == "active" else "candidate"
    return base_meta(
        title=args.title,
        memory_type=args.memory_type,
        memory_status=str(assessment["memory_status"]),
        confidence=str(assessment["confidence"]),
        project=args.project,
        source_tool=args.source_tool,
        scope=args.scope,
        sensitivity=args.sensitivity,
        tags=parse_tags(args.tags),
        status=status,
    )


def iter_cases(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files = [
        path
        for path in root.rglob("*.md")
        if not any(part.startswith(".") for part in path.relative_to(root).parts)
    ]
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def score_text(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    score = 0
    for term in terms:
        count = lowered.count(term.lower())
        score += count * max(1, len(term))
    return score


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
    results: list[tuple[int, Path, str]] = []
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


def enrich_result(root: Path, result: dict[str, object]) -> dict[str, object]:
    path = Path(str(result["path"]))
    if not path.is_absolute():
        path = root / str(result["relative_path"])
    if path.exists():
        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8", errors="ignore"))
        enriched = {**result, **{f"meta_{key}": value for key, value in meta.items()}}
        for key in ("memory_type", "memory_status", "occurrence_count"):
            if key in meta:
                enriched[key] = meta[key]
        return enriched
    return result


def find_duplicate_memory(root: Path, args: argparse.Namespace, threshold: float = 0.62) -> dict[str, object] | None:
    query = f"{args.title}\n{args.content}\n{args.tags}"
    candidates = [enrich_result(root, item) for item in find_cases(query, limit=8, root=root, mode="hybrid")]
    for item in candidates:
        if item.get("memory_type") != args.memory_type:
            continue
        if slugify(str(item.get("title", ""))) == slugify(args.title):
            return item
        if float(item.get("score", 0.0)) >= threshold:
            return item
    return None


def update_existing_memory(path: Path, args: argparse.Namespace, assessment: dict[str, object]) -> Path:
    text = path.read_text(encoding="utf-8", errors="ignore")
    meta, body = parse_frontmatter(text)
    timestamp = now_iso()
    occurrence_count = int(meta.get("occurrence_count", 1)) + 1
    current_status = str(meta.get("memory_status", "candidate"))
    new_status = "active" if occurrence_count >= 2 or assessment["memory_status"] == "active" else current_status
    evidence = args.evidence or args.content

    meta.update(
        {
            "memory_type": args.memory_type,
            "memory_status": new_status,
            "occurrence_count": occurrence_count,
            "last_seen": timestamp,
            "confidence": "high" if new_status == "active" else assessment["confidence"],
            "scope": meta.get("scope") or args.scope,
            "sensitivity": meta.get("sensitivity") or args.sensitivity,
        }
    )

    body = body.rstrip() + f"""

## 发生记录

- {timestamp}: {evidence}

## 更新记录

- occurrence_count -> {occurrence_count}
- memory_status -> {new_status}
"""
    write_memory_file(path, meta, body)
    vector_search.build_index(memory_root())
    return path


def save_memory_entry(args: argparse.Namespace) -> dict[str, object]:
    root = memory_root()
    ensure_dirs(root)
    assessment = assess_memory_value(
        args.memory_type,
        args.title,
        args.content,
        verified=args.verified,
        repeat_observed=args.repeat_observed,
        duration_minutes=args.duration_minutes,
        user_requested=args.user_requested,
    )

    if args.sensitivity == "secret" and not args.force:
        assessment = {
            "decision": "skip",
            "memory_status": "archived",
            "confidence": "high",
            "reasons": ["secret material must not be saved without force"],
        }

    if assessment["decision"] == "skip" and not args.force:
        return {"action": "skipped", "assessment": assessment}

    duplicate = find_duplicate_memory(root, args)
    if duplicate:
        path = Path(str(duplicate["path"]))
        update_existing_memory(path, args, assessment)
        return {"action": "updated", "path": str(path), "assessment": assessment}

    bucket = bucket_for_memory(args.memory_type)
    path = root / bucket / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(args.title)}.md"
    write_memory_file(path, memory_meta(args, assessment), build_memory_body(args, assessment))
    vector_search.build_index(root)
    return {"action": "created", "path": str(path), "assessment": assessment}


def save_memory(args: argparse.Namespace) -> None:
    print(json.dumps(save_memory_entry(args), ensure_ascii=False, indent=2))


def search_cases(args: argparse.Namespace) -> None:
    results = find_cases(args.query, args.limit, mode=args.mode)
    for result in results:
        print(f"[{result['score']}] {result['relative_path']}")
        print(f"    {result['title']}")
        print(f"    {result['snippet']}")
    if not results:
        print("No matching fix cases found.")


def search_memory_items(query: str, limit: int = 5, memory_type: str = "", mode: str = "hybrid") -> list[dict[str, object]]:
    root = memory_root()
    results = [enrich_result(root, item) for item in find_cases(query, max(limit * 4, 20), root=root, mode=mode)]
    if memory_type:
        results = [
            item
            for item in results
            if item.get("memory_type") == memory_type or item.get("meta_memory_type") == memory_type
        ]
    return results[:limit]


def search_memory(args: argparse.Namespace) -> None:
    results = search_memory_items(args.query, args.limit, args.memory_type, args.mode)
    for result in results:
        memory_type = result.get("memory_type", result.get("meta_memory_type", "unknown"))
        memory_status = result.get("memory_status", result.get("meta_memory_status", "unknown"))
        occurrence_count = result.get("occurrence_count", result.get("meta_occurrence_count", "?"))
        print(f"[{result['score']}] {result['relative_path']} ({memory_type}/{memory_status}/count={occurrence_count})")
        print(f"    {result['title']}")
        print(f"    {result['snippet']}")
    if not results:
        print("No matching memory found.")


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


def read_case(case_path: str) -> str:
    root = memory_root()
    requested = Path(case_path)
    candidates: list[Path] = []
    if requested.is_absolute():
        candidates.append(requested)
    else:
        candidates.append(root / requested)
        candidates.extend(iter_cases(root))

    normalized = case_path.replace("\\", "/")
    for path in candidates:
        relative = ""
        if path.exists():
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                relative = ""
        if path.exists() and (path.name == requested.name or path == requested or relative == normalized):
            return path.read_text(encoding="utf-8", errors="ignore")
    raise FileNotFoundError(f"Case not found: {case_path}")


def show_case(args: argparse.Namespace) -> None:
    try:
        print(read_case(args.path))
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc


def rebuild_vector_index(args: argparse.Namespace) -> None:
    root = memory_root()
    index = vector_search.build_index(root)
    print(root / vector_search.INDEX_FILE)
    print(f"documents: {len(index.get('documents', []))}")


def add_memory_gate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--memory-type", choices=sorted(MEMORY_BUCKETS.keys()), default="episode")
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--project", default="")
    parser.add_argument("--tags", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--source-tool", default="")
    parser.add_argument("--scope", default="global")
    parser.add_argument("--sensitivity", choices=["public", "private", "secret"], default="private")
    parser.add_argument("--duration-minutes", type=int, default=0)
    parser.add_argument("--verified", action="store_true")
    parser.add_argument("--repeat-observed", action="store_true")
    parser.add_argument("--user-requested", action="store_true")


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
    new_parser.add_argument("--memory-type", choices=sorted(MEMORY_BUCKETS.keys()), default="bug")
    new_parser.set_defaults(func=new_case)

    search_parser = sub.add_parser("search", help="search fix cases")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.add_argument("--mode", choices=["hybrid", "keyword", "vector"], default="hybrid")
    search_parser.set_defaults(func=search_cases)

    search_memory_parser = sub.add_parser("search-memory", help="search long-term memory with optional memory type filter")
    search_memory_parser.add_argument("query")
    search_memory_parser.add_argument("--memory-type", choices=sorted(MEMORY_BUCKETS.keys()), default="")
    search_memory_parser.add_argument("--limit", type=int, default=5)
    search_memory_parser.add_argument("--mode", choices=["hybrid", "keyword", "vector"], default="hybrid")
    search_memory_parser.set_defaults(func=search_memory)

    recent_parser = sub.add_parser("recent", help="list recent cases")
    recent_parser.add_argument("--limit", type=int, default=10)
    recent_parser.set_defaults(func=recent_cases)

    show_parser = sub.add_parser("show", help="show a case by path or filename")
    show_parser.add_argument("path")
    show_parser.set_defaults(func=show_case)

    index_parser = sub.add_parser("rebuild-index", help="rebuild the local vector index")
    index_parser.set_defaults(func=rebuild_vector_index)

    assess_parser = sub.add_parser("assess", help="assess whether a memory should be saved")
    add_memory_gate_args(assess_parser)
    assess_parser.set_defaults(func=assess_memory)

    remember_parser = sub.add_parser("remember", help="save or update long-term memory through the write gate")
    add_memory_gate_args(remember_parser)
    remember_parser.add_argument("--force", action="store_true")
    remember_parser.set_defaults(func=save_memory)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
