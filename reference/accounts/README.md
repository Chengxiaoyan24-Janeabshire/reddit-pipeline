# Account References

只读取所选账号代码对应的一行：

- `accounts.json`：简短人设和分配的指纹 ID；
- `account_topic_rules.json`：角度、关键词、话题和 Subreddit 路由；
- `user_fingerprints.json`：稳定的标题、开头、buffer、格式和技术上下文
  实现。
- `RULES.md`：三个账号 JSON 文件的生成式人工审核视图。

这些文件决定 R1 或 R2 如何包装被允许的来源事实。它们不能覆盖
`guidance/reddit/editorial/editorial_policy.json`，也不能创建
`guidance/reddit/workflow/weekly.json` 中不存在的 lane。

账号和受众 reference 是第三编辑层级。只有在全局 Guidance 和选定 Subreddit 的
subrule、Category/Post Type、结构和风格都满足之后，才能应用其偏好的技术
角度、topic fit 和声音指纹。如果受众偏好与前两个层级冲突，应选择另一个合规
角度，而不是削弱上层规则。

AI 和运行时校验读取 JSON 文件。人工审核使用 `RULES.md`；它由
`python3 scripts/render_rule_docs.py` 生成，不能作为独立规则源编辑。
