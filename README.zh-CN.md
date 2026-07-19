# Fix Memory MCP

[中文](README.zh-CN.md) | [English](README.md)

> Fix Memory 的目标不是“记住一切”，而是在正确的时间想起正确的信息，并持续影响 Agent 的行为。

Fix Memory MCP 是一个本地优先的 Agent Operating Context。它把用户、项目、决策、任务、约束和修复经验保存为可读的 Markdown，并为 Codex、Claude Code 或其他 MCP 客户端动态组装最小上下文。

它不保存完整聊天，也不会把整个记忆库塞进提示词。每个新任务只加载精简 Core Context 和当前意图相关的少量记忆；真实报错仍走独立的检索闸门和修复案例流程。

```text
新任务
  -> Intent Analyzer
  -> Scope / Policy Resolver
  -> Core Context + 相关记忆（预算限制）
  -> Agent 执行
  -> 候选 / 晋升 / 归档 / 替代
```

## 特性

- 本地 Markdown 存储，内容可读、可编辑、可用 Git 管理。
- 关键词检索与本地 TF-IDF 向量检索融合，不依赖云端 Embedding API。
- stdio MCP 服务，可供 Codex、Claude Code 等客户端按需启动。
- Core Context：跨窗口加载 Profile、Current Focus、Active Projects、Long-term Goals 和 Preferences。
- Context Assembly：按意图、作用域、优先级、置信度和新鲜度组装最小上下文。
- Policy：项目决策和 `hard` / `guarded` / `soft` 约束会影响 Agent 后续行为。
- Memory Budget：同时限制召回条数和估算 Token，不读取完整记忆库。
- 用户控制：支持查看、纠正、晋升、归档、过期、替代和显式删除。
- 检索闸门：首次读仓库、普通代码阅读和无明确错误的部署检查不会自动检索。
- 工作记忆与检索缓存，减少同一任务中的重复搜索。
- 错误观察账本：简单错误先只计数，第二次才生成候选，第三次才进入默认 RAG。
- 记忆生命周期：首次未验证案例是 `candidate`，已验证或重复案例是 `active`，30 天未复发的候选会归档。
- 默认 RAG 只返回 `active` 记忆；需要排查近期未确认问题时才显式包含候选。
- API Key、Token、密码、Cookie 和 Authorization 内容会在写入前被拒绝。
- `data/` 下的真实记忆默认被 Git 忽略，不会上传到仓库。

## 适用场景

- Python、Node、Windows 路径、虚拟环境、依赖问题。
- 构建、测试、部署、MCP 启动和服务连接故障。
- 本机端口、代理、模型路由、Python/Node 配置等环境事实。
- 已验证的项目决策、重复工作流、面试薄弱点。

## 目录结构

```text
fix-memory-mcp/
  data/
    fixes/              # 已修复案例，默认不上传
    failed-attempts/    # 失败尝试，默认不上传
    environments/       # 本机环境记忆，默认不上传
    preferences/        # 使用偏好，默认不上传
    projects/           # 项目决策，默认不上传
    users/              # 用户事实、能力、目标
    decisions/          # 带来源和理由的正式决策
    tasks/              # 需要跨窗口保留的任务状态
    constraints/        # 非可信的作用域化行为约束参考
    .runtime/           # 检索缓存和任务状态，默认不上传
  scripts/
    fix_memory.py       # CLI
    context_engine.py   # Core Context、Scope、Policy、预算和生命周期
    fix_memory_mcp.py   # stdio MCP 服务
    mcp_healthcheck.py  # MCP 启动健康检查
    mcp_smoke.py        # MCP 冒烟测试
    v2_check.py         # V2 端到端检查
  skills/
    fix-memory-workflow/
      SKILL.md          # Agent 工作流说明
```

## 安装与自检

```bash
git clone https://github.com/l111403717-cloud/fix-memory-mcp.git
cd fix-memory-mcp
python -m pip install mcp
python scripts/self_check.py
python scripts/v2_check.py
python scripts/mcp_smoke.py
```

Windows 上可使用固定解释器：

```powershell
D:\python312\python.exe scripts\self_check.py
D:\python312\python.exe scripts\mcp_healthcheck.py --python D:\python312\python.exe
```

`mcp_healthcheck.py` 会真实启动 MCP，完成 `initialize` 和 `tools/list` 握手，然后自动退出。它通过后，才表示客户端可以正常启动服务。

## CLI 使用

创建一个已验证的修复案例：

```powershell
D:\python312\python.exe scripts\fix_memory.py new `
  --title "Python 从错误工作目录启动导致 ModuleNotFoundError" `
  --project "demo-api" `
  --language "Python" `
  --framework "FastAPI" `
  --command "python app/main.py" `
  --error "ModuleNotFoundError: No module named app" `
  --tags "python,path,fastapi,windows" `
  --verified
```

未带 `--verified` 的首次案例会保存为 `candidate`，默认检索不会返回它。

检索修复案例：

```powershell
D:\python312\python.exe scripts\fix_memory.py search "ModuleNotFoundError FastAPI 工作目录"
D:\python312\python.exe scripts\fix_memory.py search "MCP stdio failed" --mode hybrid
D:\python312\python.exe scripts\fix_memory.py search "MCP stdio failed" --mode keyword
D:\python312\python.exe scripts\fix_memory.py search "MCP stdio failed" --mode vector
```

检索长期记忆：

```powershell
D:\python312\python.exe scripts\fix_memory.py search-memory "CCSwitch API relay" --memory-type environment
```

只有需要排查近期未确认记录时才包含候选：

```powershell
D:\python312\python.exe scripts\fix_memory.py search "TypeError helper" --include-candidates
```

先判断当前任务是否值得检索：

```powershell
D:\python312\python.exe scripts\fix_memory.py gate "rename a local variable"
D:\python312\python.exe scripts\fix_memory.py gate "ModuleNotFoundError python main.py"
```

`gate` 对无明确错误的首次任务会返回 `skip`；对真实报错、重复问题或明确要求查询记忆的任务会返回 `search`。

为新窗口组装 Core Context 和相关记忆：

```powershell
D:\python312\python.exe scripts\fix_memory.py context "继续实现 Fix Memory V2" `
  --project "fix-memory-mvp" `
  --workspace "个人项目" `
  --context-token-budget 1800 `
  --current-instruction "保持旧 Markdown 兼容"
```

`context_token_budget` 是 Context Assembly 的总上限。Core Context 先使用自己的保护上限，剩余容量会动态提供给相关 Retrieved Memory；没有可信 Policy 输入时，Policy 预留也会回流。超大单条记忆不会再按字符截断，而会在预算诊断中注明省略原因。

保存带 V2 元数据的普通决策记录：

```powershell
D:\python312\python.exe scripts\fix_memory.py remember `
  --memory-type decision `
  --title "Markdown 继续作为事实源" `
  --content "保留旧 Markdown 兼容，不做一次性重写。" `
  --project "fix-memory-mvp" `
  --source observed `
  --reason "Agent 记录的 V2 兼容决定" `
  --priority 9 `
  --user-requested
```

普通 MCP/CLI 写入只接受 `observed`、`inferred`、`imported`。Markdown 中的
`user_explicit`、`system`、`execution_level` 或 `policy_key` 都不能授予 Policy 权限；普通
constraint 只作为带 `untrusted memory` 标记的参考记忆召回。

使用 `memory show/correct/promote/archive/expire/supersede/delete` 管理单条记忆，使用 `lifecycle` 执行候选归档和到期处理。

低打扰地批量复核 Candidate：

```powershell
# 生成当天候选复核文件，位于 data/.runtime/reviews/
D:\python312\python.exe scripts\fix_memory.py memory review --project "fix-memory-mvp"

# 对候选 id 批量批准、延期或归档
D:\python312\python.exe scripts\fix_memory.py memory review `
  --approve "memory-id-a,memory-id-b" `
  --defer "memory-id-c" `
  --archive "memory-id-d" `
  --defer-days 14
```

批量批准只会将 Candidate 变为普通可召回 memory，保留原始来源和置信度，不会创建 `user_explicit`、`system` 或 Policy 权限。

对于暂时不值得写成完整错题的简单错误，先记录观察：

```powershell
D:\python312\python.exe scripts\fix_memory.py observe-error `
  --error "ModuleNotFoundError: No module named worker_app" `
  --project "worker-service" `
  --command "python worker_app/main.py" `
  --file-path "worker_app/main.py"
```

第一次只写入本地运行账本，不参与 RAG；同一错误指纹第二次出现时自动创建 `candidate`，第三次自动升级为 `active`。指纹由项目、异常类型、规范化错误文本、命令和文件名组成。

## MCP 工具

服务入口：

```powershell
D:\python312\python.exe scripts\fix_memory_mcp.py
```

MCP 仅向 Codex 等客户端公开三个高层工具：

- `assemble_context`：为当前任务组装 Core Context、有效约束、相关记忆和 Resolution Trace。
- `manage_memory`：保存、查看、纠正和管理单条记忆的生命周期。
- `maintain_memory_lifecycle`：归档过期候选并处理到期记忆。

检索、评估、写入、任务状态和向量索引等底层能力仍保留给 CLI 与内部流程，但不再
出现在 Codex 的 MCP 工具列表中，避免工具选择负担和 Agent 直接调用低层写入接口。

## Codex 配置

Codex 使用 stdio MCP，在它启动并需要工具时自动拉起服务；不需要让 Python 在电脑开机后常驻运行。

在 `%USERPROFILE%\.codex\config.toml` 中添加：

```toml
[mcp_servers.fix-memory]
command = 'D:\python312\python.exe'
args = ['C:\Users\<你的用户名>\Documents\资料库\fix-memory-mcp\scripts\fix_memory_mcp.py']
startup_timeout_sec = 10

[mcp_servers.fix-memory.env]
FIX_MEMORY_ROOT = 'C:\Users\<你的用户名>\Documents\资料库\fix-memory-mcp\data'
```

修改后重启 Codex。使用你自己机器上的实际路径替换示例路径。

也可以运行一键配置脚本：

```powershell
.\scripts\install_codex_mcp.ps1 -PythonPath D:\python312\python.exe
```

Claude Code 可使用：

```powershell
.\scripts\install_claude_mcp.ps1 -PythonPath D:\python312\python.exe
```

## MCP 无法启动时怎么办

记忆库不能成为排错的前置依赖。MCP 启动、调用或检索失败时：

1. 继续直接读取项目、复现和排查错误。
2. 需要时运行健康检查确认问题：

```powershell
D:\python312\python.exe scripts\mcp_healthcheck.py --python D:\python312\python.exe
```

3. 在 MCP 恢复前使用 CLI 兜底：

```powershell
D:\python312\python.exe scripts\fix_memory.py smart-search "<原始错误> <框架> <命令> <文件路径>" --scope fixes --mode hybrid
```

4. 修复完成后，再保存有长期价值的结论。

## 写入与保留规则

每次写入会先经过评估：

| 情况 | 状态 |
| --- | --- |
| 首次、未验证的普通错误 | `candidate` |
| 已验证的修复 | `active` |
| 用户明确说“记住”或明确确认的事实/决策 | `active` |
| AI 对偏好、性格或能力的推断 | `candidate`，等待证据或确认 |
| 多次独立证据达到晋升阈值 | `active` |
| 30 天未再次出现的候选 | `archived` |
| 达到 `expires_at` | `expired` |

相同项目和相同作用域内的相似记录会合并，`occurrence_count` 增加；不同项目不会被错误合并。

默认检索只返回 `active`。`candidate` 需要显式传 `include_candidates` 或 `--include-candidates`，`archived` 不参与检索。

不要写入完整聊天、完整终端日志、源码转储、API Key、Token、Cookie、密码、私有账号信息或私密文件内容。敏感内容会被拒绝写入。

## RAG 说明

项目实现的是本地轻量 RAG：

1. Intent Analyzer 判断当前任务需要哪些记忆类型。
2. Scope Resolver 只保留当前 task/project/workspace/global 可见记录。
3. 关键词、TF-IDF、priority、confidence 和 freshness 综合排序。
4. Policy Resolver 计算有效约束并生成 Resolution Trace。
5. Memory Budget 截断并组装 Core Context，再交给 Agent。

Fix Memory 负责 RAG 的检索部分，不在内部调用大模型生成答案。

## 隐私与 Git

`.gitignore` 默认忽略：

- `data/fixes/*`
- `data/failed-attempts/*`
- 所有其他真实记忆目录
- `data/.runtime/`
- `data/.fix_memory_vectors.json`

因此正常提交和推送时不会包含你的个人错题库。提交前仍可使用以下命令复核：

```powershell
git status --short
git ls-files data
```

## 验证命令

```powershell
D:\python312\python.exe scripts\self_check.py
D:\python312\python.exe scripts\v2_check.py
D:\python312\python.exe scripts\mcp_smoke.py
D:\python312\python.exe scripts\mcp_healthcheck.py --python D:\python312\python.exe
```

## 路线图

- 大规模记忆库的 SQLite + FTS5 索引。
- 可选 Embedding 后端。
- 更严格的敏感信息脱敏。
- 验证后的 Git diff 捕获。
- 面向更多 MCP 客户端的一键安装。
- 浏览和管理案例的 Web UI。

## 许可证

MIT
