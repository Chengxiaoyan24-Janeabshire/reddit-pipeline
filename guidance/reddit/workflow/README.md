# Workflow Guidance

这些是当前关于工作流如何运行的机器可读规则。

- `weekly.json`：活跃账号、每周 pack 数量、来源时效行为、账号/Subreddit
  分配、Post Types 和槽位资源指针。
- `source_sync.json`：来源 Base/table/view、资格字段、最小日期、官方域名、
  URL 前缀和排除来源。
- `RULES.md`：两个 workflow JSON 文件的生成式人工审核视图。

除非阶段、命令、输出或写入门禁本身也变化，否则修改这些文件不应要求修改
Skill。运行时加载器和测试直接消费这些文件。当周形状变化导致签入示例过期时，
更新样例。AI 和脚本读取 JSON；人工审核 `RULES.md`。每次规则变化后运行
`python3 scripts/render_rule_docs.py` 重新生成。
