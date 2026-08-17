# Slot References

只读取所选周槽位的目录。AI 和运行时使用 JSON 文件；匹配的 Markdown 文件是其
生成式人工审核视图：

| Slot | Account | Machine rule | Human review |
|---|---|---|---|
| `r/Rag` | R1 | `rag/rag.json` | `rag/rag.md` |
| `r/AI_Agents` | R1 | `ai_agents/ai_agents.json` | `ai_agents/ai_agents.md` |
| `r/AIMemory` | R2 | `ai_memory/ai_memory.json` | `ai_memory/ai_memory.md` |
| `r/LocalLLaMA` | R2 | `local_llama/local_llama.json` | `local_llama/local_llama.md` |

每个槽位 JSON 包含社区范围、Post Type guidance、原生结构、继承合同、截图边界
和规避列表。配对的 Markdown 由 `python3 scripts/render_rule_docs.py` 生成；不要
独立编辑。`resource/reddit/slots/` 下的截图仅作为 Post Type 和结构的视觉证据；
绝不能复制身份、链接、主张、指标或措辞。

`subreddits.json` 是机器注册表。`RULES.md` 是其生成式人工审核视图。

所有槽位 JSON 都继承 `guidance/reddit/editorial/editorial_policy.json`、来自
`guidance/reddit/workflow/weekly.json` 的当前映射，以及来自 `reference/accounts/`
的选定账号指纹。

编辑上，槽位是第二层：Guidance 已经强制，随后槽位强制社区 subrule 和有效的
Post Category/Post Type，再应用原生结构和风格。只有这些决策完成后，账号/
受众角度和指纹才能塑造剩余选择。截图是证据，不是第四规则层。
