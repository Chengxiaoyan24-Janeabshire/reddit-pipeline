# Editorial Guidance

这些机器可读文件定义每个账号和 Subreddit 槽位的第一个、也是最高的编辑
指令层级。

- `editorial_policy.json`：disclosure、匿名、第一人称表达、language Buffer、
  标题、品牌、链接、开头、结尾和安全策略。
- `content_length_rules.json`：短、标准、长和带代码长帖的层级。
- `RULES.md`：两个 JSON 文件的生成式人工审核视图。

AI 和运行时校验读取 JSON，人工检查 `RULES.md`。通过 AI 修改 JSON，然后运行
`python3 scripts/render_rule_docs.py`；不要独立编辑生成的审核视图。

通过这层 Guidance 后，选定的 Subreddit reference 才应用其 subrule、有效的
Post Category/Post Type、原生结构和风格。账号和受众 reference 是第三层，
只能塑造仍合规的剩余选择。
