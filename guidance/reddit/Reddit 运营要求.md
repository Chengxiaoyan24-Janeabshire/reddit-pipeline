# Reddit 运营要求

## 工作范围

当前流程只生成供人工审核的 Reddit 内容，不执行任何 Reddit 账号操作。

- 不自动登录、发帖、评论、回复、点赞、投票或切换账号。
- 不生成 warm-up、无关水帖或协同互动。
- 飞书仅作为内容审核与人工发布状态记录系统。

## 账号与周槽位

当前账号、每周数量、Subreddit 分配和 Post Type 由
`guidance/reddit/workflow/weekly.json` 定义。这里不复制这些运行配置值。

## 内容规则优先级

以下顺序用于筛选、起草、改写和校验；它与文件夹的修改频率不是同一个概念：

1. 第一层是 Guidance。先满足 Disclosure，再满足第一人称 `I` 和自然、合乎语法的
   language Buffer；匿名、品牌、链接、标题、开头和安全要求也都属于这一层。
2. 第二层是 Subreddit。先遵守该社区的 Subrule，确保 Post Category/Post Type
   在当前配置中有效，再采用该社区常见的帖子结构和行文风格。
3. 第三层是受众偏好的角度。最后才选择受众更喜欢的技术角度、topic fit 和账号
   fingerprint；vector database、retrieval、memory 或 local inference 等偏好都
   属于这一层。

层级冲突时，上层永远优先。Subreddit 规则不能放宽 Guidance；受众角度和账号
fingerprint 不能覆盖前两层。如果下层没有兼容选项，应更换角度或来源，或者拒绝
草稿。来源事实约束所有层级，不得为了满足角度而编造经历、客户、benchmark、
指标或结果。

## 匿名要求

- R1/R2 必须绝对匿名，Disclosure 为空。
- 可以写 `I built`，但不得暴露真实身份、雇主、贡献者或维护者身份、
  affiliation、客户身份或代表某个组织发言。
- 标题必须使用第一人称单数视角，或写成以 `?` 结尾的明确疑问句；不得使用
  完全第三人称的陈述标题。
- 标题不得出现 Milvus。每篇正文必须恰好出现一次 Milvus，且必须有技术背景或
  数据来源支撑，并填写 `milvus_mention_basis`。提及必须放在同类技术举例或
  peer-group 语境中，不能直接植入。
- 任何位置都不得出现 Zilliz。
- 分析技术栈时可以提到上下游技术栈的具体品牌名，但需来源命名且技术相关。
- 数据库品牌名只在问题类帖子中可以点名；其他帖子用同类或 peer-group 说法。
- 不得编造第一人称经历、客户故事、benchmark 或结果。

## 链接要求

- R1 和 R2 全部为 `no_link`。
- 标题、正文和任何链接字段都不得包含 URL。

## 数据同步

`Reddit Blog Pool` 的当前来源、字段条件、日期下限、官方域名和排除来源由
`guidance/reddit/workflow/source_sync.json` 定义。同步流程必须按该 Guidance fail closed，
不能从未配置的来源补充候选。

## 输出要求

输出只能包含最终草稿和结构化审核字段，不得包含推理过程、账号隐私、
登录信息或内部草稿备注。所有 Reddit 发布和互动必须由人工完成。

第一句必须建立有来源支持的第一人称视角；每篇正文至少使用一个自然、合乎语法的
language buffer 表达判断或不确定性。缺少任一项都会阻断验证。Buffer 不得用来
模糊来源支持的事实、benchmark 设置或测量数据。Tutorial 用结论、验证步骤或下一步收尾，不追加问题；
Discussion 的互动邀请可选，使用柔和表达而不是生硬问句。原生短讨论或
Resource Request 使用 `short_post`；普通技术讨论继续使用 `standard_post`。
