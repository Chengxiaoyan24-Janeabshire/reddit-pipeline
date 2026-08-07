# Reddit 内容问答

## 这套流程会自动发 Reddit 吗？

不会。它只生成草稿并写入飞书审核区。登录、发布、评论、回复、点赞和投票
全部由人工完成。

## 一周生成多少内容？

固定四个技术主帖槽位：R1 两条、R2 两条。没有额外账号、warm-up 或无关内容。

## R1 和 R2 可以公开身份吗？

不可以。两个账号都必须保持匿名，Disclosure 为空。可以写 `I built`，但不能
写雇主、真实身份、贡献者/维护者角色、affiliation、客户身份或组织代表关系。

## 正文可以写产品名吗？

标题不能出现 Milvus。每篇正文必须恰好出现一次 Milvus，而且必须确实用于说明
来源支持的开发背景或数据。提及必须是自然的同类举例或并列，例如
`vector databases like Milvus`、`data infrastructures such as Milvus` 或
`Milvus and other databases`；不能把它直接写成推荐、主语或产品植入。任何位置
都不能出现 Zilliz。

## 标题应该怎么写？

标题必须使用第一人称单数视角，例如 `I think`、`Now I believe` 或
`What I learned`，或者写成以 `?` 结尾的明确疑问句。完全第三人称的陈述标题
不能通过验证。

## 可以带链接吗？

R1 和 R2 都不带链接。标题、正文和任何链接字段都不能出现 URL。

## 第一句和 language buffer 是硬性要求吗？

是。正文第一句必须建立有来源支持的第一人称视角，而且全文至少包含一个自然、
合乎语法的 language buffer，用来修饰判断、建议或不确定性。缺少任一项都会
阻断验证。不得用 buffer 模糊来源已经支持的事实、benchmark 设置或测量数据。

## 什么样的帖子更合适？

优先选择有技术细节的内容，例如：

- retrieval、chunking、reranking 和 evaluation 的具体方法；
- agent 工具调用、memory、可靠性和失败处理；
- vector database 的迁移、索引、成本、过滤和 benchmark 方法；
- data pipeline 的 CDC、增量同步、可观测性和生产维护。

## 什么内容不能写？

- 预设某个方案必然是赢家的结论；
- 无来源的 benchmark、客户故事、数字或第一人称经历；
- 暴露账号身份、雇主或项目关系的内容；
- 从截图复制用户名、原文、链接、Disclosure 或个人主张；
- 操纵投票、组织评论或引导协同行动的内容。

## 每条正文应该怎样收尾？

Tutorial 必须用结论、验证步骤或下一步收尾，不能追加问题。Discussion 的互动
邀请可有可无；需要邀请时使用 `Would love to hear your thoughts.` 一类柔和表达，
不以生硬问句结尾。`Question | Help` 可以保留清晰、具体的问题。

## 短帖子可以保留吗？

可以。真实的短 Discussion 或 Resource Request 使用 `short_post`，不需要为了
达到 `standard_post` 的长度而填充，但仍要给出足够背景。开放问题可有可无。
