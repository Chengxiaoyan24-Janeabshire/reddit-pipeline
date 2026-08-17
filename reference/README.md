# Reddit References

Reference 保存选定的账号、Subreddit 和受众上下文，它们只能在 Guidance 建立的
边界内使用。它们不定义工作流如何运行，也不能重新定义全局编辑的 pass/fail
策略。

- `accounts/`：R1/R2 人设、话题路由和稳定的声音指纹。
- `slots/`：四个 subreddit overlay、Post Types、原生结构和脱敏截图指针的
  机器 JSON 与生成的 MD 审核页。
- `topic_bank.json`：筛选中使用的共享咨询性话题分类。
- `accounts/RULES.md`、`TOPIC_RULES.md` 和 `slots/RULES.md`：机器 JSON 的
  生成式人工审核视图。

Workflow 和全局编辑规则位于 `guidance/reddit/`。图片和生成的 PDF 位于
`resource/reddit/`。

在编辑工作中，Reference 内容有两个不同优先级：

1. 选定的 `slots/` Subreddit reference 在全局 Guidance 之后应用其 subrule、
   有效的 Post Category/Post Type、原生结构和常见风格；
2. `accounts/` 和 `topic_bank.json` 随后提供受众偏好的角度、topic fit 和
   声音指纹。

受众层不能覆盖 Guidance 或选定的 Subreddit。如果其偏好的 vector-database、
retrieval、memory 或 local-inference 角度不符合两个更高层级和来源事实，
就选择其他角度或拒绝该来源。

JSON 仍然是底层运行时合同。生成的 Markdown 是供人工检查的上层审核层。
通过 AI 更新 JSON，然后运行 `python3 scripts/render_rule_docs.py`；不要手工
维护两个层。
