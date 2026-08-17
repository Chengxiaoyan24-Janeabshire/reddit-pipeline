# Reddit Guidance

Guidance 定义 Reddit pipeline 如何运行，以及每个周槽位和账号继承的全局规则。
这些值可能变化，而不需要重写稳定的 Agent 阶段调用逻辑。

- `workflow/`：周数量、活跃账号、槽位分配、来源时效和同步合同。
- `editorial/`：全局编辑、安全和内容长度合同。
- `Reddit 运营要求.md`：人工可读的运营与安全边界。
- `Reddit 内容问答.md`：面向用户的 FAQ。
- `Reddit 内容建议及范例.md`：起草指导和范例。
- `Milvus blog for repurpose.md`：经过脱敏的改写范例。

图片和生成的 PDF 放在 `resource/reddit/`。

日常运行时，AI 和脚本读取 JSON。人工检查时读取 `workflow/RULES.md` 或
`editorial/RULES.md`。不要独立编辑生成的审核页；修改 JSON 后运行
`python3 scripts/render_rule_docs.py`。

## 编辑优先级

Guidance 是第一层，也是最高编辑层级。先解决 Disclosure，再满足要求的第一人称
`I` 和合乎语法的 language Buffer，然后应用其余全局匿名、品牌、链接、标题、
开头和安全合同。

只有在 Guidance 满足之后，选定的 Subreddit 才能定义其有效的
Post Category/Post Type、原生结构和常见写作风格。受众偏好、技术角度、
topic fit 和账号指纹是第三层，只能在前两层仍允许的选项内塑造内容。

机器可读的顺序是 `editorial/editorial_policy.json` 中的
`guidance > subreddit > audience_angle`。上层始终优先；无法解决的冲突就是
拒绝。来源事实约束所有三层，不能为了迎合偏好角度而编造。
