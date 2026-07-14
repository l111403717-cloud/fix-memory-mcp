# Fix Memory MCP

[中文](README.zh-CN.md) | [English](README.md)

> 不要为同一个报错重复排查两次。

Fix Memory MCP 是一个本地优先的开发者长期记忆库。它把经过筛选的报错、修复经验、环境配置和工作流保存为本地 Markdown 文件，供 Codex、Claude Code 或其他 MCP 客户端在需要时检索。

它不是记录完整聊天记录的通用记忆工具，而是面向排错和复用的“Agent 错题本”。

```text
出现错误
  -> 检索历史案例
  -> 复用适用的修复思路
  -> 修复并验证
  -> 写入有长期价值的结论
```

## 特性

- 本地 Markdown 存储，内容可读、可编辑、可用 Git 管理。
- 关键词检索与本地 TF-IDF 向量检索融合，不依赖云端 Embedding API。
- stdio MCP 服务，可供 Codex、Claude Code 等客户端按需启动。
- 检索闸门：首次读仓库、普通代码阅读和无明确错误的部署检查不会自动检索。
- 工作记忆与检索缓存，减少同一任务中的重复搜索。
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
    .runtime/           # 检索缓存和任务状态，默认不上传
  scripts/
    fix_memory.py       # CLI
    fix_memory_mcp.py   # stdio MCP 服务
    mcp_healthcheck.py  # MCP 启动健康检查
    mcp_smoke.py        # MCP 冒烟测试
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

## MCP 工具

服务入口：

```powershell
D:\python312\python.exe scripts\fix_memory_mcp.py
```

MCP 提供以下工具：

- `save_fix_case`：经评估、去重和敏感信息检查后保存修复案例。
- `search_fixes` / `search_fixes_vector`：检索修复案例。
- `search_memory`：检索环境、偏好、项目决策等长期记忆。
- `should_search_memory` / `smart_search_memory`：检索闸门和带缓存的智能检索。
- `task_state`：记录当前任务状态，不写入长期记忆。
- `assess_memory` / `save_memory`：评估并保存普通长期记忆。
- `get_fix_case`、`list_recent_fixes`、`rebuild_vector_index`。

`save_fix_case` 建议传入 `verified: true`，只在修复已验证后把案例提升为活跃记忆。

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
| 重复出现至少两次 | `active` |
| 环境、偏好、项目决策、面试薄弱点 | 通常为 `active` |
| 30 天未再次出现的候选 | `archived` |

相同项目和相同作用域内的相似记录会合并，`occurrence_count` 增加；不同项目不会被错误合并。

默认检索只返回 `active`。`candidate` 需要显式传 `include_candidates` 或 `--include-candidates`，`archived` 不参与检索。

不要写入完整聊天、完整终端日志、源码转储、API Key、Token、Cookie、密码、私有账号信息或私密文件内容。敏感内容会被拒绝写入。

## RAG 说明

项目实现的是本地轻量 RAG：

1. 从 `data/**/*.md` 中检索历史案例。
2. 关键词得分与 TF-IDF 余弦相似度融合排序。
3. MCP 把相关案例返回给 Codex 或其他 Agent。
4. 调用 MCP 的 Agent 根据检索结果完成分析、修复和回答。

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
