from __future__ import annotations

import argparse
import datetime as dt
import hashlib
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
    "user": "users",
    "decision": "decisions",
    "task": "tasks",
    "constraint": "constraints",
}

STRONG_MEMORY_TYPES = {
    "preference",
    "environment",
    "interview",
    "project",
    "user",
    "decision",
    "constraint",
}
V2_MEMORY_CATEGORIES = {"user", "project", "decision", "task", "constraint"}
VALID_SCOPES = ("current", "task", "project", "workspace", "global")
VALID_EXECUTION_LEVELS = ("hard", "guarded", "soft")
VALID_CONTEXT_SECTIONS = ("profile", "current_focus", "active_projects", "long_term_goals", "preferences", "")
AGENT_WRITABLE_SOURCES = ("observed", "inferred", "imported")
ENVIRONMENT_HINT_RE = re.compile(
    r"(?:\b(?:api|proxy|ccswitch|port|path|python|node|npm|pnpm|uv|venv|mcp|token|key|cookie|password|account)\b|账号|路径|端口|中转|环境|模型|代理|密钥)",
    re.IGNORECASE,
)
ERROR_HINT_RE = re.compile(
    r"(?:\b(?:error|exception|traceback|failed|failure|cannot|can't|module not found|not found|timeout|refused|denied|permission|syntaxerror|typeerror|moduleerror|importerror|modulenotfounderror)\b|报错|错误|失败|不行|崩|连不上|拒绝|超时|权限)",
    re.IGNORECASE,
)
TECH_CONTEXT_RE = re.compile(
    r"(?:\b(?:build|test|deploy|nginx|docker|mcp|api|server|config|github|repo|repository)\b|构建|测试|部署|服务器|配置|仓库|项目)",
    re.IGNORECASE,
)
REPEAT_HINT_RE = re.compile(r"(?:\bagain\b|\bstill\b|\brepeated\b|又|还是|重复|之前|上次|老问题)", re.IGNORECASE)
EXPLICIT_MEMORY_RE = re.compile(
    r"(?:fix-memory|错题库|报错库|历史记忆|先查|查一下记忆|search memory|remember this)",
    re.IGNORECASE,
)
CONFIG_PATH_RE = re.compile(
    r"(?:package\.json|pyproject\.toml|requirements\.txt|tsconfig|vite\.config|next\.config|docker-compose|Dockerfile|nginx|\.env|mcp|settings|config)",
    re.IGNORECASE,
)
RUNTIME_DIR = ".runtime"
TASK_STATE_FILE = "task_state.json"
RETRIEVAL_CACHE_FILE = "retrieval_cache.json"
ERROR_OBSERVATIONS_FILE = "error_observations.json"
CACHE_SIMILARITY_THRESHOLD = 0.72
CACHE_MAX_AGE_HOURS = 12
CANDIDATE_MAX_AGE_DAYS = 30
OBSERVATION_CANDIDATE_THRESHOLD = 2
OBSERVATION_ACTIVE_THRESHOLD = 3
ACTIVE_MEMORY_STATUS = "active"
CANDIDATE_MEMORY_STATUS = "candidate"
ARCHIVED_MEMORY_STATUS = "archived"
SENSITIVE_CONTENT_RE = re.compile(
    r"(?:\b(?:api[_-]?key|access[_-]?token|token|password|authorization|cookie)\s*[:=]\s*\S+|"
    r"\b(?:sk[-_]|ghp_|github_pat_)[A-Za-z0-9_-]{12,}|\bBearer\s+[A-Za-z0-9._-]{12,})",
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


def parse_csv(raw: str | None) -> list[str]:
    return parse_tags(raw)


def confidence_score(value: object) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    return {"high": 0.9, "medium": 0.65, "low": 0.35}.get(str(value).lower(), 0.5)


def validate_agent_writable_source(source: str) -> str:
    if source not in AGENT_WRITABLE_SOURCES:
        allowed = ", ".join(AGENT_WRITABLE_SOURCES)
        raise ValueError(
            f"Agent-writable interfaces reject authoritative source '{source}'. "
            f"Allowed sources: {allowed}"
        )
    return source


def default_priority(memory_type: str) -> int:
    return {
        "constraint": 9,
        "decision": 8,
        "task": 8,
        "user": 7,
        "project": 7,
        "preference": 6,
        "environment": 6,
        "bug": 6,
        "fix": 6,
    }.get(memory_type, 5)


def stable_memory_id(*, title: str, memory_type: str, project: str, scope: str) -> str:
    source = json.dumps(
        {
            "title": slugify(title),
            "memory_type": memory_type,
            "project": project.strip().lower(),
            "scope": scope,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{memory_type}-{hashlib.sha256(source.encode('utf-8')).hexdigest()[:16]}"


def frontmatter_value(value: object) -> str:
    return json.dumps(value if value is not None else "", ensure_ascii=False)


def frontmatter_list(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def ensure_dirs(root: Path) -> None:
    for bucket in sorted(set(MEMORY_BUCKETS.values())):
        (root / bucket).mkdir(parents=True, exist_ok=True)
    (root / RUNTIME_DIR).mkdir(parents=True, exist_ok=True)


def runtime_path(name: str, root: Path | None = None) -> Path:
    root = root or memory_root()
    return root / RUNTIME_DIR / name


def load_json_file(path: Path, default: dict[str, object]) -> dict[str, object]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)
    return data if isinstance(data, dict) else dict(default)


def write_json_file(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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


def parse_iso(value: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def task_state_default() -> dict[str, object]:
    return {
        "version": 1,
        "current_task": None,
    }


def load_task_state(root: Path | None = None) -> dict[str, object]:
    root = root or memory_root()
    ensure_dirs(root)
    return load_json_file(runtime_path(TASK_STATE_FILE, root), task_state_default())


def save_task_state(data: dict[str, object], root: Path | None = None) -> dict[str, object]:
    root = root or memory_root()
    ensure_dirs(root)
    data["version"] = 1
    write_json_file(runtime_path(TASK_STATE_FILE, root), data)
    return data


def start_task_state(goal: str, project: str = "", task_id: str = "", root: Path | None = None) -> dict[str, object]:
    timestamp = now_iso()
    task = {
        "task_id": task_id or slugify(f"{project}-{goal}")[:80],
        "project": project,
        "goal": goal,
        "started_at": timestamp,
        "last_updated": timestamp,
        "memory_searched": False,
        "searches": [],
        "matched_memory": [],
        "verified": [],
        "notes": [],
    }
    return save_task_state({"version": 1, "current_task": task}, root)


def current_task(data: dict[str, object]) -> dict[str, object] | None:
    task = data.get("current_task")
    return task if isinstance(task, dict) else None


def append_task_event(
    *,
    event_type: str,
    value: object,
    root: Path | None = None,
    project: str = "",
    goal: str = "",
) -> dict[str, object]:
    data = load_task_state(root)
    task = current_task(data)
    if task is None:
        task = current_task(start_task_state(goal or "ad-hoc task", project, root=root)) or {}
        data = {"version": 1, "current_task": task}

    timestamp = now_iso()
    task["last_updated"] = timestamp
    if event_type == "search":
        task["memory_searched"] = True
        searches = task.setdefault("searches", [])
        if isinstance(searches, list):
            searches.append(value)
    elif event_type == "match":
        matched = task.setdefault("matched_memory", [])
        if isinstance(matched, list):
            for item in value if isinstance(value, list) else [value]:
                if item and item not in matched:
                    matched.append(item)
    elif event_type == "verified":
        verified = task.setdefault("verified", [])
        if isinstance(verified, list):
            verified.append({"at": timestamp, "item": value})
    elif event_type == "note":
        notes = task.setdefault("notes", [])
        if isinstance(notes, list):
            notes.append({"at": timestamp, "note": value})
    else:
        notes = task.setdefault("notes", [])
        if isinstance(notes, list):
            notes.append({"at": timestamp, "note": f"{event_type}: {value}"})
    data["current_task"] = task
    return save_task_state(data, root)


def clear_task_state(root: Path | None = None) -> dict[str, object]:
    return save_task_state(task_state_default(), root)


def should_search_memory(
    query: str,
    *,
    context: str = "",
    project: str = "",
    command: str = "",
    file_path: str = "",
    memory_type: str = "",
    force: bool = False,
) -> dict[str, object]:
    text = "\n".join(part for part in [query, context, project, command, file_path, memory_type] if part)
    reasons: list[str] = []
    has_error = bool(ERROR_HINT_RE.search(text))
    has_environment_hint = bool(ENVIRONMENT_HINT_RE.search(text))
    has_repeat = bool(REPEAT_HINT_RE.search(text))
    has_explicit_memory_request = bool(EXPLICIT_MEMORY_RE.search(text))
    has_tech_context = bool(TECH_CONTEXT_RE.search(text))
    touches_config = bool(CONFIG_PATH_RE.search(file_path) or CONFIG_PATH_RE.search(command))

    if force:
        reasons.append("forced by caller")
    if has_explicit_memory_request:
        reasons.append("caller explicitly asked to use memory")
    if has_error:
        reasons.append("query/context contains a hard error or failure signal")
    if has_repeat and (has_environment_hint or has_tech_context):
        reasons.append("query/context suggests a repeated environment/tooling issue")
    if touches_config and (has_error or has_repeat or has_explicit_memory_request):
        reasons.append("configuration/tooling file is involved in an error or repeated issue")
    if memory_type in STRONG_MEMORY_TYPES and (has_error or has_repeat or has_explicit_memory_request):
        reasons.append(f"{memory_type} memory can affect this error/repeated task")

    if reasons:
        return {
            "decision": "search",
            "confidence": "high" if len(reasons) >= 2 else "medium",
            "reasons": reasons,
        }

    return {
        "decision": "skip",
        "confidence": "medium",
        "reasons": [
            "no hard error, repeated-issue signal, or explicit memory request found; first-time repo/deploy checks should inspect the project directly"
        ],
    }


def cache_default() -> dict[str, object]:
    return {"version": 1, "entries": []}


def load_retrieval_cache(root: Path | None = None) -> dict[str, object]:
    root = root or memory_root()
    ensure_dirs(root)
    return load_json_file(runtime_path(RETRIEVAL_CACHE_FILE, root), cache_default())


def save_retrieval_cache(data: dict[str, object], root: Path | None = None) -> dict[str, object]:
    root = root or memory_root()
    ensure_dirs(root)
    data["version"] = 1
    write_json_file(runtime_path(RETRIEVAL_CACHE_FILE, root), data)
    return data


def invalidate_retrieval_cache(root: Path | None = None) -> None:
    """Discard cached retrievals after a memory write changes search results."""
    root = root or memory_root()
    cache_path = runtime_path(RETRIEVAL_CACHE_FILE, root)
    if cache_path.exists():
        cache_path.unlink()


def query_tokens(query: str) -> set[str]:
    return set(vector_search.tokenize(query))


def token_similarity(left: str, right: str) -> float:
    left_tokens = query_tokens(left)
    right_tokens = query_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    return overlap / ((len(left_tokens) * len(right_tokens)) ** 0.5)


def cache_entry_is_fresh(entry: dict[str, object], max_age_hours: int = CACHE_MAX_AGE_HOURS) -> bool:
    created = parse_iso(str(entry.get("created_at", "")))
    if not created:
        return False
    return dt.datetime.now() - created <= dt.timedelta(hours=max_age_hours)


def find_cached_retrieval(
    query: str,
    *,
    search_scope: str,
    memory_type: str = "",
    mode: str = "hybrid",
    project: str = "",
    threshold: float = CACHE_SIMILARITY_THRESHOLD,
    max_age_hours: int = CACHE_MAX_AGE_HOURS,
    root: Path | None = None,
) -> dict[str, object] | None:
    cache = load_retrieval_cache(root)
    entries = cache.get("entries", [])
    if not isinstance(entries, list):
        return None

    best: tuple[float, dict[str, object]] | None = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("search_scope") != search_scope or entry.get("mode") != mode:
            continue
        if memory_type and entry.get("memory_type") != memory_type:
            continue
        if project and entry.get("project") and entry.get("project") != project:
            continue
        if not cache_entry_is_fresh(entry, max_age_hours):
            continue
        similarity = token_similarity(query, str(entry.get("query", "")))
        if similarity >= threshold and (best is None or similarity > best[0]):
            best = (similarity, entry)

    if best is None:
        return None

    similarity, entry = best
    entry["last_used"] = now_iso()
    entry["hit_count"] = int(entry.get("hit_count", 0)) + 1
    save_retrieval_cache(cache, root)
    return {**entry, "similarity": round(similarity, 6)}


def store_retrieval_cache(
    query: str,
    results: list[dict[str, object]],
    *,
    search_scope: str,
    memory_type: str = "",
    mode: str = "hybrid",
    project: str = "",
    root: Path | None = None,
) -> dict[str, object]:
    cache = load_retrieval_cache(root)
    entries = cache.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    timestamp = now_iso()
    summary_results = [
        {
            "score": item.get("score"),
            "relative_path": item.get("relative_path"),
            "title": item.get("title"),
            "memory_type": item.get("memory_type", item.get("meta_memory_type", "")),
            "memory_status": item.get("memory_status", item.get("meta_memory_status", "")),
            "snippet": item.get("snippet", ""),
        }
        for item in results
    ]
    entry = {
        "query": query,
        "search_scope": search_scope,
        "memory_type": memory_type,
        "mode": mode,
        "project": project,
        "created_at": timestamp,
        "last_used": timestamp,
        "hit_count": 0,
        "results": summary_results,
    }
    entries.insert(0, entry)
    cache["entries"] = entries[:100]
    save_retrieval_cache(cache, root)
    return entry


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
    priority: int | None = None,
    source: str = "observed",
    evidence_refs: list[str] | None = None,
    reason: str = "",
    workspace: str = "",
    task_id: str = "",
    context_section: str = "",
    execution_level: str = "soft",
    policy_key: str = "",
    expires_at: str = "",
    superseded_by: str = "",
) -> dict[str, object]:
    timestamp = now_iso()
    resolved_priority = default_priority(memory_type) if priority is None else max(0, min(10, priority))
    resolved_scope = scope if scope in VALID_SCOPES else "global"
    resolved_execution_level = (
        execution_level if execution_level in VALID_EXECUTION_LEVELS else "soft"
    )
    return {
        "memory_id": stable_memory_id(
            title=title,
            memory_type=memory_type,
            project=project,
            scope=resolved_scope,
        ),
        "title": title,
        "memory_type": memory_type,
        "memory_category": memory_type if memory_type in V2_MEMORY_CATEGORIES else memory_type,
        "memory_status": memory_status,
        "occurrence_count": 1,
        "first_seen": timestamp,
        "last_seen": timestamp,
        "confidence": confidence,
        "confidence_score": confidence_score(confidence),
        "evidence_score": 1.0 if source == "user_explicit" else (0.2 if source == "inferred" else 0.35),
        "priority": resolved_priority,
        "scope": resolved_scope,
        "workspace": workspace,
        "task_id": task_id,
        "sensitivity": sensitivity,
        "project": project,
        "language": language,
        "framework": framework,
        "command": command,
        "source_tool": source_tool,
        "source": source,
        "evidence_refs": evidence_refs or [],
        "reason": reason,
        "created_at": timestamp,
        "updated_at": timestamp,
        "last_verified_at": timestamp if source == "user_explicit" else "",
        "last_used_at": "",
        "used_count": 0,
        "expires_at": expires_at,
        "superseded_by": superseded_by,
        "context_section": context_section,
        "execution_level": resolved_execution_level,
        "policy_key": policy_key,
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
        priority=getattr(args, "priority", None),
        source=getattr(args, "source", "observed"),
        evidence_refs=parse_csv(getattr(args, "evidence_refs", "")),
        reason=getattr(args, "reason", ""),
        workspace=getattr(args, "workspace", ""),
        task_id=getattr(args, "task_id", ""),
        context_section=getattr(args, "context_section", ""),
        execution_level=getattr(args, "execution_level", "soft"),
        policy_key=getattr(args, "policy_key", ""),
        expires_at=getattr(args, "expires_at", ""),
        superseded_by=getattr(args, "superseded_by", ""),
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


def write_case_file(args: argparse.Namespace, root: Path | None = None) -> Path:
    root = root or memory_root()
    ensure_dirs(root)
    bucket = bucket_for_memory(getattr(args, "memory_type", "bug"), getattr(args, "status", "fixed"))
    path = root / bucket / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(args.title)}.md"
    path.write_text(build_case(args), encoding="utf-8")
    vector_search.build_index(root)
    return path


def fix_case_content(args: argparse.Namespace) -> str:
    return "\n".join(
        str(value)
        for value in (
            getattr(args, "title", ""),
            getattr(args, "project", ""),
            getattr(args, "language", ""),
            getattr(args, "framework", ""),
            getattr(args, "command", ""),
            getattr(args, "error", ""),
            getattr(args, "tags", ""),
        )
        if value
    )


def contains_sensitive_material(*values: object) -> bool:
    return any(SENSITIVE_CONTENT_RE.search(str(value)) for value in values if value)


def secret_skip_assessment() -> dict[str, object]:
    return {
        "decision": "skip",
        "memory_status": ARCHIVED_MEMORY_STATUS,
        "confidence": "high",
        "reasons": ["secret-looking material must not be stored"],
    }


def save_fix_case_entry(args: argparse.Namespace) -> dict[str, object]:
    root = memory_root()
    ensure_dirs(root)
    status = getattr(args, "status", "fixed")
    memory_type = "failed_attempt" if status == "failed" else getattr(args, "memory_type", "bug")
    content = fix_case_content(args)
    assessment = assess_memory_value(
        memory_type,
        args.title,
        content,
        verified=bool(getattr(args, "verified", False)),
        repeat_observed=bool(getattr(args, "repeat_observed", False)),
        duration_minutes=int(getattr(args, "duration_minutes", 0)),
        user_requested=bool(getattr(args, "user_requested", False)),
    )
    if getattr(args, "sensitivity", "private") == "secret" or contains_sensitive_material(
        args.title, content
    ):
        assessment = secret_skip_assessment()

    if assessment["decision"] == "skip":
        return {"action": "skipped", "assessment": assessment}

    args.memory_type = memory_type
    args.memory_status = assessment["memory_status"]
    args.confidence = assessment["confidence"]
    duplicate = find_duplicate_memory(root, args)
    if duplicate:
        path = Path(str(duplicate["path"]))
        update_existing_memory(path, args, assessment)
        invalidate_retrieval_cache(root)
        return {"action": "updated", "path": str(path), "assessment": assessment}

    path = write_case_file(args, root)
    invalidate_retrieval_cache(root)
    return {"action": "created", "path": str(path), "assessment": assessment}


def create_case(args: argparse.Namespace) -> Path:
    """Backward-compatible case creator that now always uses the write gate."""
    result = save_fix_case_entry(args)
    if result["action"] == "skipped":
        reasons = ", ".join(str(reason) for reason in result["assessment"]["reasons"])
        raise ValueError(f"Fix case was not saved: {reasons}")
    return Path(str(result["path"]))


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
    source: str = "",
) -> dict[str, object]:
    text = f"{title}\n{content}"
    reasons: list[str] = []

    if user_requested or source == "user_explicit":
        reasons.append("user explicitly asked to remember it")
    if repeat_observed or occurrence_count >= 2:
        reasons.append("it has repeated at least twice")
    if duration_minutes >= 10:
        reasons.append("it cost at least 10 minutes")
    if verified and memory_type in {"bug", "fix", "failed_attempt"}:
        reasons.append("the fix was verified")
    if source == "inferred" and not user_requested:
        return {
            "decision": "candidate",
            "memory_status": "candidate",
            "confidence": "low",
            "reasons": ["AI inference requires more evidence or user confirmation"],
        }
    if memory_type in STRONG_MEMORY_TYPES:
        reasons.append(f"{memory_type} memory is durable by default")
    if memory_type == "workflow" and (repeat_observed or occurrence_count >= 2):
        reasons.append("workflow repeated enough to become reusable")
    if ENVIRONMENT_HINT_RE.search(text) and memory_type in {"environment", "preference"}:
        reasons.append("it involves environment/API/path/account/tool configuration")

    if reasons:
        return {
            "decision": "save",
            "memory_status": "active",
            "confidence": "high" if len(reasons) >= 2 else "medium",
            "reasons": reasons,
        }

    if memory_type in {"episode", "workflow", "prompt", "bug", "fix", "failed_attempt"}:
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
    validate_agent_writable_source(getattr(args, "source", "observed"))
    result = assess_memory_value(
        args.memory_type,
        args.title,
        args.content,
        verified=args.verified,
        repeat_observed=args.repeat_observed,
        duration_minutes=args.duration_minutes,
        user_requested=args.user_requested,
        source=getattr(args, "source", ""),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_memory_body(args: argparse.Namespace, assessment: dict[str, object]) -> str:
    timestamp = now_iso()
    evidence = getattr(args, "evidence", "") or getattr(args, "content", "") or fix_case_content(args)
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
        priority=getattr(args, "priority", None),
        source=getattr(args, "source", "observed"),
        evidence_refs=parse_csv(getattr(args, "evidence_refs", "")),
        reason=getattr(args, "reason", "") or "; ".join(
            str(item) for item in assessment.get("reasons", [])
        ),
        workspace=getattr(args, "workspace", ""),
        task_id=getattr(args, "task_id", ""),
        context_section=getattr(args, "context_section", ""),
        execution_level=getattr(args, "execution_level", "soft"),
        policy_key=getattr(args, "policy_key", ""),
        expires_at=getattr(args, "expires_at", ""),
        superseded_by=getattr(args, "superseded_by", ""),
    )


def iter_cases(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files = [
        path
        for path in root.rglob("*.md")
        if path.is_file()
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
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


def archive_stale_candidates(root: Path | None = None, max_age_days: int = CANDIDATE_MAX_AGE_DAYS) -> int:
    """Archive unpromoted candidate memories that have not recurred recently."""
    root = root or memory_root()
    cutoff = dt.datetime.now() - dt.timedelta(days=max_age_days)
    archived = 0
    for path in iter_cases(root):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8", errors="ignore"))
        if meta.get("memory_status") != CANDIDATE_MEMORY_STATUS:
            continue
        deferred_until = parse_iso(str(meta.get("review_deferred_until", "")))
        if deferred_until:
            current = dt.datetime.now(deferred_until.tzinfo) if deferred_until.tzinfo else dt.datetime.now()
            if deferred_until > current:
                continue
        last_seen = parse_iso(str(meta.get("last_seen", "")))
        if last_seen is None or last_seen > cutoff:
            continue
        meta["memory_status"] = ARCHIVED_MEMORY_STATUS
        meta["status"] = ARCHIVED_MEMORY_STATUS
        meta["last_seen"] = now_iso()
        write_memory_file(path, meta, body)
        archived += 1
    return archived


def filter_retrievable_results(
    results: list[dict[str, object]], *, include_candidates: bool = False
) -> list[dict[str, object]]:
    allowed_statuses = {ACTIVE_MEMORY_STATUS}
    if include_candidates:
        allowed_statuses.add(CANDIDATE_MEMORY_STATUS)
    return [
        item
        for item in results
        if str(item.get("memory_status", item.get("meta_memory_status", ACTIVE_MEMORY_STATUS)))
        in allowed_statuses
    ]


def find_duplicate_memory(root: Path, args: argparse.Namespace, threshold: float = 0.62) -> dict[str, object] | None:
    content = getattr(args, "content", "") or fix_case_content(args)
    query = f"{args.title}\n{content}\n{getattr(args, 'tags', '')}"
    candidates = [enrich_result(root, item) for item in find_cases(query, limit=8, root=root, mode="hybrid")]
    for item in candidates:
        if item.get("memory_type") != args.memory_type:
            continue
        if str(item.get("meta_project", "")) != str(getattr(args, "project", "")):
            continue
        if str(item.get("meta_scope", "global")) != str(getattr(args, "scope", "global")):
            continue
        candidate_title = str(item.get("meta_title", item.get("title", "")))
        if slugify(candidate_title) == slugify(args.title):
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
    source = getattr(args, "source", str(meta.get("source", "observed")))
    evidence_score = float(meta.get("evidence_score", 0.0))
    if source == "user_explicit" or getattr(args, "user_requested", False):
        evidence_score = 1.0
    else:
        evidence_score += 0.35 if getattr(args, "verified", False) else 0.2
        if getattr(args, "repeat_observed", False):
            evidence_score += 0.25
    evidence_score = min(1.0, evidence_score)
    new_status = current_status
    if assessment["memory_status"] == "active" or evidence_score >= 0.75:
        new_status = "active"
    evidence = getattr(args, "evidence", "") or getattr(args, "content", "") or fix_case_content(args)

    meta.update(
        {
            "memory_type": args.memory_type,
            "memory_status": new_status,
            "occurrence_count": occurrence_count,
            "last_seen": timestamp,
            "confidence": "high" if new_status == "active" else assessment["confidence"],
            "confidence_score": 0.9 if new_status == "active" else confidence_score(
                assessment["confidence"]
            ),
            "evidence_score": round(evidence_score, 3),
            "scope": meta.get("scope") or getattr(args, "scope", "global"),
            "sensitivity": meta.get("sensitivity") or getattr(args, "sensitivity", "private"),
            "updated_at": timestamp,
            "last_verified_at": timestamp
            if getattr(args, "verified", False) or source == "user_explicit"
            else meta.get("last_verified_at", ""),
            "source": source,
            "reason": getattr(args, "reason", "") or meta.get("reason", ""),
            "priority": max(
                int(meta.get("priority", default_priority(args.memory_type))),
                int(getattr(args, "priority", default_priority(args.memory_type)) or 0),
            ),
        }
    )
    refs = meta.get("evidence_refs", [])
    if not isinstance(refs, list):
        refs = []
    for ref in parse_csv(getattr(args, "evidence_refs", "")):
        if ref not in refs:
            refs.append(ref)
    meta["evidence_refs"] = refs

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


def error_observations_default() -> dict[str, object]:
    return {"version": 1, "entries": []}


def normalise_observation_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[a-z]:\\[^\s'\"]+|/[^\s'\"]+", "<path>", value)
    value = re.sub(r"\b(?:at\s+)?line\s+\d+\b", "", value)
    value = re.sub(r"\bline\s*=\s*\d+\b", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" :,-")


def error_type_from_text(error: str) -> str:
    match = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))\b", error)
    return match.group(1) if match else "error"


def error_observation_signature(
    *, project: str, error: str, command: str, file_path: str
) -> tuple[str, dict[str, str]]:
    error_type = error_type_from_text(error)
    normalized = {
        "project": normalise_observation_text(project),
        "error_type": error_type,
        "error": normalise_observation_text(error),
        "command": normalise_observation_text(command),
        "file_path": Path(file_path).name.lower(),
    }
    source = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:24], normalized


def observation_case_title(entry: dict[str, object]) -> str:
    project = str(entry.get("project", "")) or "local task"
    error_type = str(entry.get("error_type", "error"))
    return f"Repeated {error_type} in {project}"


def write_observation_case(root: Path, entry: dict[str, object]) -> Path:
    args = argparse.Namespace(
        title=observation_case_title(entry),
        project=str(entry.get("project", "")),
        language="",
        framework="",
        command=str(entry.get("command", "")),
        error=str(entry.get("normalized_error", "")),
        tags=f"observed,error,{str(entry.get('error_type', 'error')).lower()}",
        source_tool="error-observation",
        status="partial",
        memory_type="bug",
        memory_status=CANDIDATE_MEMORY_STATUS,
        confidence="medium",
        scope="project" if entry.get("project") else "global",
        sensitivity="private",
    )
    return write_case_file(args, root)


def activate_observation_case(root: Path, entry: dict[str, object]) -> Path | None:
    relative_path = str(entry.get("case_path", ""))
    path = root / relative_path
    if not relative_path or not path.exists():
        return None
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8", errors="ignore"))
    occurrence_count = int(entry["occurrence_count"])
    meta.update(
        {
            "memory_type": "bug",
            "memory_status": ACTIVE_MEMORY_STATUS,
            "occurrence_count": occurrence_count,
            "last_seen": now_iso(),
            "confidence": "high",
            "status": "active",
        }
    )
    body = body.rstrip() + f"""

## 观察升级

- 自动观察到相同错误第 {occurrence_count} 次出现，已升级为 active。
"""
    write_memory_file(path, meta, body)
    vector_search.build_index(root)
    return path


def record_error_observation(
    *,
    error: str,
    project: str = "",
    command: str = "",
    file_path: str = "",
    root: Path | None = None,
) -> dict[str, object]:
    """Count recurring errors without exposing first occurrences to default RAG."""
    root = root or memory_root()
    ensure_dirs(root)
    if contains_sensitive_material(error, project, command, file_path):
        return {"action": "skipped", "reason": "secret-looking material must not be observed"}

    fingerprint, normalized = error_observation_signature(
        project=project, error=error, command=command, file_path=file_path
    )
    data = load_json_file(runtime_path(ERROR_OBSERVATIONS_FILE, root), error_observations_default())
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        entries = []

    entry = next(
        (item for item in entries if isinstance(item, dict) and item.get("fingerprint") == fingerprint),
        None,
    )
    timestamp = now_iso()
    if entry is None:
        entry = {
            "fingerprint": fingerprint,
            "project": project,
            "error_type": normalized["error_type"],
            "normalized_error": normalized["error"],
            "command": command,
            "file_path": normalized["file_path"],
            "first_seen": timestamp,
            "last_seen": timestamp,
            "occurrence_count": 1,
            "case_path": "",
        }
        entries.append(entry)
    else:
        entry["last_seen"] = timestamp
        entry["occurrence_count"] = int(entry.get("occurrence_count", 1)) + 1

    occurrence_count = int(entry["occurrence_count"])
    action = "observed"
    case_path = ""
    if occurrence_count == OBSERVATION_CANDIDATE_THRESHOLD:
        case = write_observation_case(root, entry)
        entry["case_path"] = case.relative_to(root).as_posix()
        case_path = str(case)
        action = "candidate_created"
        invalidate_retrieval_cache(root)
    elif occurrence_count >= OBSERVATION_ACTIVE_THRESHOLD:
        case = activate_observation_case(root, entry)
        if case is not None:
            case_path = str(case)
            action = "activated" if occurrence_count == OBSERVATION_ACTIVE_THRESHOLD else "active_updated"
            invalidate_retrieval_cache(root)

    data["version"] = 1
    data["entries"] = entries
    write_json_file(runtime_path(ERROR_OBSERVATIONS_FILE, root), data)
    return {
        "action": action,
        "fingerprint": fingerprint,
        "occurrence_count": occurrence_count,
        "path": case_path or str(entry.get("case_path", "")),
    }


def save_memory_entry(args: argparse.Namespace) -> dict[str, object]:
    root = memory_root()
    ensure_dirs(root)
    if not getattr(args, "scope", ""):
        args.scope = "project" if getattr(args, "project", "") else "global"
    assessment = assess_memory_value(
        args.memory_type,
        args.title,
        args.content,
        verified=args.verified,
        repeat_observed=args.repeat_observed,
        duration_minutes=args.duration_minutes,
        user_requested=args.user_requested,
        source=getattr(args, "source", ""),
    )

    if args.sensitivity == "secret" or contains_sensitive_material(args.title, args.content, args.evidence):
        assessment = secret_skip_assessment()

    if assessment["decision"] == "skip":
        return {"action": "skipped", "assessment": assessment}

    duplicate = find_duplicate_memory(root, args)
    if duplicate:
        path = Path(str(duplicate["path"]))
        update_existing_memory(path, args, assessment)
        invalidate_retrieval_cache(root)
        return {"action": "updated", "path": str(path), "assessment": assessment}

    bucket = bucket_for_memory(args.memory_type)
    path = root / bucket / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(args.title)}.md"
    write_memory_file(path, memory_meta(args, assessment), build_memory_body(args, assessment))
    vector_search.build_index(root)
    invalidate_retrieval_cache(root)
    return {"action": "created", "path": str(path), "assessment": assessment}


def save_memory(args: argparse.Namespace) -> None:
    validate_agent_writable_source(getattr(args, "source", "observed"))
    print(json.dumps(save_memory_entry(args), ensure_ascii=False, indent=2))


def search_cases(args: argparse.Namespace) -> None:
    results = search_fix_items(
        args.query,
        args.limit,
        mode=args.mode,
        include_candidates=getattr(args, "include_candidates", False),
    )
    for result in results:
        print(f"[{result['score']}] {result['relative_path']}")
        print(f"    {result['title']}")
        print(f"    {result['snippet']}")
    if not results:
        print("No matching fix cases found.")


def search_fix_items(
    query: str,
    limit: int = 5,
    mode: str = "hybrid",
    include_candidates: bool = False,
) -> list[dict[str, object]]:
    root = memory_root()
    archive_stale_candidates(root)
    results = [enrich_result(root, item) for item in find_cases(query, max(limit * 8, 40), root=root, mode=mode)]
    return filter_retrievable_results(results, include_candidates=include_candidates)[:limit]


def search_memory_items(
    query: str,
    limit: int = 5,
    memory_type: str = "",
    mode: str = "hybrid",
    include_candidates: bool = False,
) -> list[dict[str, object]]:
    root = memory_root()
    archive_stale_candidates(root)
    results = [enrich_result(root, item) for item in find_cases(query, max(limit * 8, 40), root=root, mode=mode)]
    if memory_type:
        results = [
            item
            for item in results
            if item.get("memory_type") == memory_type or item.get("meta_memory_type") == memory_type
        ]
    return filter_retrievable_results(results, include_candidates=include_candidates)[:limit]


def smart_search(
    query: str,
    *,
    search_scope: str = "memory",
    limit: int = 5,
    memory_type: str = "",
    mode: str = "hybrid",
    context: str = "",
    project: str = "",
    command: str = "",
    file_path: str = "",
    force: bool = False,
    include_candidates: bool = False,
) -> dict[str, object]:
    if archive_stale_candidates(memory_root()):
        invalidate_retrieval_cache()
    gate = should_search_memory(
        query,
        context=context,
        project=project,
        command=command,
        file_path=file_path,
        memory_type=memory_type,
        force=force,
    )
    if gate["decision"] == "skip" and not force:
        append_task_event(
            event_type="note",
            value=f"retrieval skipped for query: {query}",
            project=project,
            goal=context or query,
        )
        return {
            "action": "skipped",
            "from_cache": False,
            "gate": gate,
            "results": [],
        }

    cached = find_cached_retrieval(
        query,
        search_scope=search_scope,
        memory_type=memory_type,
        mode=mode,
        project=project,
    )
    if cached:
        results = cached.get("results", [])
        append_task_event(
            event_type="search",
            value={
                "at": now_iso(),
                "query": query,
                "search_scope": search_scope,
                "memory_type": memory_type,
                "mode": mode,
                "from_cache": True,
                "cache_similarity": cached.get("similarity"),
                "result_count": len(results) if isinstance(results, list) else 0,
            },
            project=project,
            goal=context or query,
        )
        if isinstance(results, list):
            append_task_event(
                event_type="match",
                value=[item.get("relative_path") for item in results if isinstance(item, dict)],
                project=project,
                goal=context or query,
            )
        return {
            "action": "cache_hit",
            "from_cache": True,
            "gate": gate,
            "cache": {
                "query": cached.get("query"),
                "similarity": cached.get("similarity"),
                "hit_count": cached.get("hit_count"),
                "created_at": cached.get("created_at"),
            },
            "results": results,
        }

    if search_scope == "fixes":
        results = search_fix_items(
            query, limit=limit, mode=mode, include_candidates=include_candidates
        )
    elif search_scope == "memory":
        results = search_memory_items(
            query,
            limit=limit,
            memory_type=memory_type,
            mode=mode,
            include_candidates=include_candidates,
        )
    else:
        raise ValueError(f"Unknown smart search scope: {search_scope}")

    store_retrieval_cache(
        query,
        results,
        search_scope=search_scope,
        memory_type=memory_type,
        mode=mode,
        project=project,
    )
    append_task_event(
        event_type="search",
        value={
            "at": now_iso(),
            "query": query,
            "search_scope": search_scope,
            "memory_type": memory_type,
            "mode": mode,
            "from_cache": False,
            "result_count": len(results),
        },
        project=project,
        goal=context or query,
    )
    append_task_event(
        event_type="match",
        value=[item.get("relative_path") for item in results],
        project=project,
        goal=context or query,
    )
    return {
        "action": "searched",
        "from_cache": False,
        "gate": gate,
        "results": results,
    }


def search_memory(args: argparse.Namespace) -> None:
    results = search_memory_items(
        args.query,
        args.limit,
        args.memory_type,
        args.mode,
        getattr(args, "include_candidates", False),
    )
    for result in results:
        memory_type = result.get("memory_type", result.get("meta_memory_type", "unknown"))
        memory_status = result.get("memory_status", result.get("meta_memory_status", "unknown"))
        occurrence_count = result.get("occurrence_count", result.get("meta_occurrence_count", "?"))
        print(f"[{result['score']}] {result['relative_path']} ({memory_type}/{memory_status}/count={occurrence_count})")
        print(f"    {result['title']}")
        print(f"    {result['snippet']}")
    if not results:
        print("No matching memory found.")


def gate_search(args: argparse.Namespace) -> None:
    result = should_search_memory(
        args.query,
        context=args.context,
        project=args.project,
        command=args.command,
        file_path=args.file_path,
        memory_type=args.memory_type,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def smart_search_cli(args: argparse.Namespace) -> None:
    result = smart_search(
        args.query,
        search_scope=args.scope,
        limit=args.limit,
        memory_type=args.memory_type,
        mode=args.mode,
        context=args.context,
        project=args.project,
        command=args.command,
        file_path=args.file_path,
        force=args.force,
        include_candidates=getattr(args, "include_candidates", False),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def task_state_cli(args: argparse.Namespace) -> None:
    if args.task_action == "start":
        result = start_task_state(args.goal, args.project, args.task_id)
    elif args.task_action == "show":
        result = load_task_state()
    elif args.task_action == "note":
        result = append_task_event(event_type="note", value=args.note, project=args.project, goal=args.goal)
    elif args.task_action == "verify":
        result = append_task_event(event_type="verified", value=args.item, project=args.project, goal=args.goal)
    elif args.task_action == "clear":
        result = clear_task_state()
    else:
        raise SystemExit(f"Unknown task-state action: {args.task_action}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def observe_error_cli(args: argparse.Namespace) -> None:
    result = record_error_observation(
        error=args.error,
        project=args.project,
        command=args.command,
        file_path=args.file_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def load_context_engine():
    try:
        from . import context_engine
    except ImportError:
        import context_engine
    return context_engine


def assemble_context_cli(args: argparse.Namespace) -> None:
    engine = load_context_engine()
    result = engine.assemble_context(
        args.query,
        context=args.context,
        project=args.project,
        workspace=args.workspace,
        task_id=args.task_id,
        current_instruction=args.current_instruction,
        core_token_budget=args.core_token_budget,
        retrieval_token_budget=args.retrieval_token_budget,
        policy_token_budget=args.policy_token_budget,
        context_token_budget=args.context_token_budget,
        max_items=args.max_items,
        override_policy_keys=args.override_policy_key,
        approve_guarded_override=args.approve_guarded_override,
        track_usage=not args.no_track_usage,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def manage_memory_cli(args: argparse.Namespace) -> None:
    engine = load_context_engine()
    if args.memory_action == "review":
        approve = parse_csv(args.approve)
        defer = parse_csv(args.defer)
        archive = parse_csv(args.archive)
        if approve or defer or archive:
            result = engine.apply_candidate_review(
                approve=approve,
                defer=defer,
                archive=archive,
                defer_days=args.defer_days,
            )
        else:
            result = engine.write_candidate_review(project=args.project, limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    result = engine.manage_memory(
        args.memory_action,
        args.identifier,
        content=getattr(args, "content", ""),
        reason=getattr(args, "reason", ""),
        superseded_by=getattr(args, "superseded_by", ""),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def lifecycle_cli(args: argparse.Namespace) -> None:
    result = load_context_engine().maintain_lifecycle()
    print(json.dumps(result, ensure_ascii=False, indent=2))


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
    parser.add_argument("--scope", choices=VALID_SCOPES, default="")
    parser.add_argument("--sensitivity", choices=["public", "private", "secret"], default="private")
    parser.add_argument("--duration-minutes", type=int, default=0)
    parser.add_argument("--verified", action="store_true")
    parser.add_argument("--repeat-observed", action="store_true")
    parser.add_argument("--user-requested", action="store_true")
    parser.add_argument("--priority", type=int, choices=range(0, 11), default=None)
    parser.add_argument(
        "--source",
        choices=AGENT_WRITABLE_SOURCES,
        default="observed",
    )
    parser.add_argument("--evidence-refs", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--context-section", choices=VALID_CONTEXT_SECTIONS, default="")
    parser.add_argument("--execution-level", choices=VALID_EXECUTION_LEVELS, default="soft")
    parser.add_argument("--policy-key", default="")
    parser.add_argument("--expires-at", default="")
    parser.add_argument("--superseded-by", default="")


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
    new_parser.add_argument("--verified", action="store_true")
    new_parser.add_argument("--repeat-observed", action="store_true")
    new_parser.add_argument("--duration-minutes", type=int, default=0)
    new_parser.add_argument("--user-requested", action="store_true")
    new_parser.add_argument("--sensitivity", choices=["public", "private", "secret"], default="private")
    new_parser.set_defaults(func=new_case)

    search_parser = sub.add_parser("search", help="search fix cases")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.add_argument("--mode", choices=["hybrid", "keyword", "vector"], default="hybrid")
    search_parser.add_argument("--include-candidates", action="store_true")
    search_parser.set_defaults(func=search_cases)

    search_memory_parser = sub.add_parser("search-memory", help="search long-term memory with optional memory type filter")
    search_memory_parser.add_argument("query")
    search_memory_parser.add_argument("--memory-type", choices=sorted(MEMORY_BUCKETS.keys()), default="")
    search_memory_parser.add_argument("--limit", type=int, default=5)
    search_memory_parser.add_argument("--mode", choices=["hybrid", "keyword", "vector"], default="hybrid")
    search_memory_parser.add_argument("--include-candidates", action="store_true")
    search_memory_parser.set_defaults(func=search_memory)

    gate_parser = sub.add_parser("gate", help="decide whether a task should search long-term memory")
    gate_parser.add_argument("query")
    gate_parser.add_argument("--context", default="")
    gate_parser.add_argument("--project", default="")
    gate_parser.add_argument("--command", default="")
    gate_parser.add_argument("--file-path", default="")
    gate_parser.add_argument("--memory-type", choices=sorted(MEMORY_BUCKETS.keys()), default="")
    gate_parser.add_argument("--force", action="store_true")
    gate_parser.set_defaults(func=gate_search)

    smart_parser = sub.add_parser("smart-search", help="use retrieval gate and semantic cache before searching")
    smart_parser.add_argument("query")
    smart_parser.add_argument("--scope", choices=["memory", "fixes"], default="memory")
    smart_parser.add_argument("--memory-type", choices=sorted(MEMORY_BUCKETS.keys()), default="")
    smart_parser.add_argument("--limit", type=int, default=5)
    smart_parser.add_argument("--mode", choices=["hybrid", "keyword", "vector"], default="hybrid")
    smart_parser.add_argument("--context", default="")
    smart_parser.add_argument("--project", default="")
    smart_parser.add_argument("--command", default="")
    smart_parser.add_argument("--file-path", default="")
    smart_parser.add_argument("--force", action="store_true")
    smart_parser.add_argument("--include-candidates", action="store_true")
    smart_parser.set_defaults(func=smart_search_cli)

    task_parser = sub.add_parser("task-state", help="manage current task working memory")
    task_sub = task_parser.add_subparsers(dest="task_action", required=True)
    task_start = task_sub.add_parser("start", help="start a working-memory task")
    task_start.add_argument("--goal", required=True)
    task_start.add_argument("--project", default="")
    task_start.add_argument("--task-id", default="")
    task_start.set_defaults(func=task_state_cli)
    task_show = task_sub.add_parser("show", help="show current working-memory task")
    task_show.set_defaults(func=task_state_cli)
    task_note = task_sub.add_parser("note", help="append a task note")
    task_note.add_argument("--note", required=True)
    task_note.add_argument("--project", default="")
    task_note.add_argument("--goal", default="")
    task_note.set_defaults(func=task_state_cli)
    task_verify = task_sub.add_parser("verify", help="append a verification item")
    task_verify.add_argument("--item", required=True)
    task_verify.add_argument("--project", default="")
    task_verify.add_argument("--goal", default="")
    task_verify.set_defaults(func=task_state_cli)
    task_clear = task_sub.add_parser("clear", help="clear current working-memory task")
    task_clear.set_defaults(func=task_state_cli)

    observe_parser = sub.add_parser(
        "observe-error", help="count a recurring error without immediately adding it to RAG"
    )
    observe_parser.add_argument("--error", required=True)
    observe_parser.add_argument("--project", default="")
    observe_parser.add_argument("--command", default="")
    observe_parser.add_argument("--file-path", default="")
    observe_parser.set_defaults(func=observe_error_cli)

    context_parser = sub.add_parser(
        "context", help="assemble budgeted Core Context, policy, and relevant memory"
    )
    context_parser.add_argument("query")
    context_parser.add_argument("--context", default="")
    context_parser.add_argument("--project", default="")
    context_parser.add_argument("--workspace", default="")
    context_parser.add_argument("--task-id", default="")
    context_parser.add_argument("--current-instruction", default="")
    context_parser.add_argument("--core-token-budget", type=int, default=600)
    context_parser.add_argument("--retrieval-token-budget", type=int, default=800)
    context_parser.add_argument("--policy-token-budget", type=int, default=400)
    context_parser.add_argument("--context-token-budget", type=int, default=None)
    context_parser.add_argument("--max-items", type=int, default=12)
    context_parser.add_argument("--override-policy-key", action="append", default=[])
    context_parser.add_argument("--approve-guarded-override", action="store_true")
    context_parser.add_argument("--no-track-usage", action="store_true")
    context_parser.set_defaults(func=assemble_context_cli)

    memory_parser = sub.add_parser("memory", help="inspect or update a V2 memory lifecycle")
    memory_sub = memory_parser.add_subparsers(dest="memory_action", required=True)
    for action in ("show", "archive", "expire", "promote", "delete"):
        action_parser = memory_sub.add_parser(action)
        action_parser.add_argument("identifier")
        action_parser.add_argument("--reason", default="")
        action_parser.set_defaults(func=manage_memory_cli)
    correct_parser = memory_sub.add_parser("correct")
    correct_parser.add_argument("identifier")
    correct_parser.add_argument("--content", required=True)
    correct_parser.add_argument("--reason", default="")
    correct_parser.set_defaults(func=manage_memory_cli)
    supersede_parser = memory_sub.add_parser("supersede")
    supersede_parser.add_argument("identifier")
    supersede_parser.add_argument("--superseded-by", required=True)
    supersede_parser.add_argument("--reason", default="")
    supersede_parser.set_defaults(func=manage_memory_cli)
    review_parser = memory_sub.add_parser(
        "review", help="generate or apply a batch review for candidate memories"
    )
    review_parser.add_argument("--project", default="")
    review_parser.add_argument("--limit", type=int, default=25)
    review_parser.add_argument("--approve", default="", help="comma-separated candidate ids")
    review_parser.add_argument("--defer", default="", help="comma-separated candidate ids")
    review_parser.add_argument("--archive", default="", help="comma-separated candidate ids")
    review_parser.add_argument("--defer-days", type=int, default=14)
    review_parser.set_defaults(func=manage_memory_cli)

    lifecycle_parser = sub.add_parser(
        "lifecycle", help="archive stale candidates and expire dated memories"
    )
    lifecycle_parser.set_defaults(func=lifecycle_cli)

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
