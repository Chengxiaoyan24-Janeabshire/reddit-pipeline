# Reddit Weekly Pipeline

本项目生成符合策略要求的 Reddit 草稿，供人工审核和手动发布；随后通过可见的
Chrome/Browser 页面状态监测已发布的帖子。项目不会执行任何 Reddit 账号操作。

## 工作流

```text
Content All in One / All content / all content
  -> pool 同步
  -> 来源筛选与 R1/R2 分配
  -> 四个槽位起草
  -> 校验
  -> 飞书审核交付
  -> 人工审核并手动发布到 Reddit
  -> 对最近 14 天内已发布帖子做可见页面监测
```

当前 pack 数量、活跃账号以及账号/Subreddit 槽位都从
`guidance/reddit/workflow/weekly.json` 读取，刻意不在本 README 中重复。

## 渐进式资源布局

| 层级 | 职责 |
|---|---|
| `guidance/reddit/workflow/` | 数量、分配、时效和同步的机器 JSON 及生成的 MD 审核页 |
| `guidance/reddit/editorial/` | 全局编辑与长度规则的机器 JSON 及生成的 MD 审核页 |
| `reference/accounts/` | 受众角度、路由和指纹的机器 JSON 及生成的 MD 审核页 |
| `reference/slots/` | 每个 Subreddit 槽位及注册表的机器 JSON 和生成的 MD 审核页 |
| `guidance/reddit/*.md` | 人工编写的运营边界、FAQ 和范例 |
| `resource/reddit/` | 非权威截图和生成的 PDF |
| `.agents/skills/` | 稳定的阶段路由、命令、输出和写入门禁 |
| `scripts/` | 运行时命令和共享实现模块 |

辅助目录保持独立：

- `config/`：飞书表 ID、字段映射和凭据模板；
- `samples/`：有效输入示例，不代表策略；
- `tests/`：回归覆盖；
- `packs/` 和 `tmp/`：被忽略的输出和临时文件。

`guidance/`、`reference/` 和 `resource/` 都是活跃内容层，可能经常变化。
`.agents/skills/` 保存相对稳定的阶段调用逻辑，只有工作流阶段、命令、输出或
写入门禁变化时才需要修改。这是维护边界，不是内容规则优先级。

当内容规则互相作用时，按 `Guidance > Subreddit > Audience angle` 处理：
先满足全局 Disclosure 和语言要求；再满足 Subreddit 的 subrule、有效的
Category/Post Type 和原生风格；最后才是偏好的技术角度和账号指纹。上层始终
优先，同时来源事实约束每一层。

## 规则文件格式

规则配置有两个需要同步的表面：

- **JSON** 是 AI 工作流阶段和 Python 校验器读取的底层机器合同。
- **Markdown** 是供人工检查的上层审核表面。

Markdown 审核页由生成得到，不能独立编辑。JSON 规则变更后运行
`python3 scripts/render_rule_docs.py`；用 `--check` 在审核页过期时失败。
从 [Editorial rules](guidance/reddit/editorial/RULES.md)、
[Workflow rules](guidance/reddit/workflow/RULES.md)、
[Account rules](reference/accounts/RULES.md)、
[Topic rules](reference/TOPIC_RULES.md) 或
[Subreddit registry](reference/slots/RULES.md) 开始查看。

仅在需要某一层时读取 [reference/README.md](reference/README.md)、
[guidance/reddit/README.md](guidance/reddit/README.md)、
[resource/reddit/README.md](resource/reddit/README.md) 和
[scripts/README.md](scripts/README.md)。

## Skills

| Skill | 结果 |
|---|---|
| `reddit-weekly` | 完整的四槽位工作流 |
| `reddit-pool-sync` | 来源池预览或授权同步 |
| `reddit-source-screen` | 来源适配度和 lane 分配 |
| `reddit-pack-draft` | 只生成草稿 JSON，不写入 |
| `reddit-pack-validate` | 只读校验 |
| `reddit-pack-write` | 飞书审核预览或授权写入 |
| `reddit-browser-monitor` | 可见指标和评论信号预览或授权写入 |

每个 Skill 只读取当前工作流 guidance、相关 editorial guidance、选定账号、
选定槽位和可选视觉资源。运行时校验会合并
`guidance/reddit/workflow/weekly.json` 与
`guidance/reddit/editorial/editorial_policy.json`，一旦三层指令合同被重排或
重新分配就会 fail closed。

## 来源合同

`guidance/reddit/workflow/source_sync.json` 保存当前来源 ID、类别、状态、
URL 边界、最小日期和排除来源。来源时效和旧来源回退行为位于
`guidance/reddit/workflow/weekly.json`。

## Draft JSON

```json
{
  "source_title": "...",
  "source_url": "https://official-source.example/blog/...",
  "pool_record_id": "rec...",
  "items": [
    {
      "account_code": "<configured account>",
      "content_type": "technical_post",
      "subreddit": "<configured subreddit>",
      "post_type": "<configured Post Type>",
      "title": "...",
      "body": "...",
      "disclosure": "",
      "link_policy": "<guidance value>",
      "milvus_mention_basis": "<when required by guidance>",
      "angle": "...",
      "voice_fingerprint": "<configured fingerprint>",
      "length_tier": "<configured tier>"
    }
  ]
}
```

`source_url` 是内部审核元数据。生成的内容遵循 `guidance/reddit/` 中当前的
链接和品牌 guidance。

## 安装与校验

```bash
bash scripts/setup.sh
python3 -m unittest
python3 scripts/render_rule_docs.py --check
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < samples/weekly_pack.example.json
```

## 常用预览

```bash
# 来源同步
python3 scripts/sync_blog_pool_from_content_all_in_one.py --dry-run

# 筛选
python3 scripts/screen_feishu_pool.py --dry-run

# 单个来源筛选，不写入
python3 scripts/screen_and_assign.py --url "https://milvus.io/blog/example" --title "Example" --no-fetch

# 校验和交付预览
python3 scripts/append_pack_to_feishu.py --validate-only --weekly < samples/weekly_pack.example.json
python3 scripts/append_pack_to_feishu.py --weekly --dry-run < samples/weekly_pack.example.json

# 已发布帖子监测目标
python3 scripts/reddit_browser_monitor.py --list-targets
```

飞书真实写入需要明确授权。Reddit 发布和互动始终由人工完成。

## 变更日志

每次推送涉及行为、规则或用户工作流变化时更新 `CHANGELOG.md`。条目描述结果，
而不是罗列修改过的文件。
