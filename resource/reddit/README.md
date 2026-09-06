# Reddit Resources

Resource 是非权威的视觉或生成文件。它们支持起草和审核，但绝不定义策略。

- `slots/`：仅用于 Post Type 和原生结构 overlay 的脱敏 Subreddit 截图。
- `routes/`：James 与 anonymous 两条路线的非权威 Resource manifest；两条路线可按
  manifest 复用同一组 Subreddit 截图，但不得从截图推导身份、披露或品牌规则。
- `pdfs/`：用于分发的 Markdown guidance 生成副本。

可编辑规则位于 `guidance/reddit/`。动态的周、同步、账号、话题和槽位选择位于
`reference/`。

编辑 `guidance/reddit/` 下对应的 Markdown 后，运行
`python3 scripts/rebuild_reddit_resources.py` 重建 PDF。
