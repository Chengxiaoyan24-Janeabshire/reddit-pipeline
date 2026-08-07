# Reddit 运营要求

## 工作范围

当前流程只生成供人工审核的 Reddit 内容，不执行任何 Reddit 账号操作。

- 不自动登录、发帖、评论、回复、点赞、投票或切换账号。
- 不生成 warm-up、无关水帖或协同互动。
- 飞书仅作为内容审核与人工发布状态记录系统。

## 账号与周槽位

只使用 R1 和 R2，每周固定四个技术主帖：

| 账号 | 固定 Subreddit |
|---|---|
| R1 | r/Rag、r/AI_Agents |
| R2 | r/vectordatabase、r/LocalLLaMA |

每个槽位必须使用对应社区允许的 Post Type。r/vectordatabase 写入
`No fixed post type`，表示规则已检查但社区没有固定类型。

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
- 不得编造第一人称经历、客户故事、benchmark 或结果。

## 链接要求

- R1 和 R2 全部为 `no_link`。
- 标题、正文和任何链接字段都不得包含 URL。

## 数据同步

`Reddit Blog Pool` 的来源固定为 Zilliz Content All in One：

- Table：`All content`（`tblsyUaNiyPnhrFI`）
- View：`all content`（`vewx5CDVdU`）
- 条件：`Category = Blog Post`、`Status = Published`、官方 Blog URL 非空
- 日期下限：`2026-01-01`

飞书真实标签为 `Blog Post`；用户口述的 “Post Blog” 对应此选项。不得从
`Medium sync`、`Medium Daily` 或 EN Content 同步。

## 输出要求

输出只能包含最终草稿和结构化审核字段，不得包含推理过程、账号隐私、
登录信息或内部草稿备注。所有 Reddit 发布和互动必须由人工完成。

第一句必须建立有来源支持的第一人称视角；每篇正文至少使用一个自然、合乎语法的
language buffer 表达判断或不确定性。缺少任一项都会阻断验证。Buffer 不得用来
模糊来源支持的事实、benchmark 设置或测量数据。Tutorial 用结论、验证步骤或下一步收尾，不追加问题；
Discussion 的互动邀请可选，使用柔和表达而不是生硬问句。原生短讨论或
Resource Request 使用 `short_post`；普通技术讨论继续使用 `standard_post`。
