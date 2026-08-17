# Runtime Scripts

从项目根目录运行命令：`python3 scripts/...`。

## 工作流命令

- `sync_blog_pool_from_content_all_in_one.py`：预览或同步来源行。
- `screen_feishu_pool.py`：筛选待处理的飞书池行。
- `screen_and_assign.py`：筛选单个来源，或提供筛选引擎。
- `append_pack.py`：不产生外部写入，校验草稿 JSON。
- `append_pack_to_feishu.py`：校验、预览或写入审核草稿。
- `reddit_browser_monitor.py`：校验浏览器观察结果，并预览或写入已发布帖子
  的监测字段。
- `list_feishu_pool.py`：查看当前池行。

## 安装与维护

- `setup.sh`：创建本地运行时环境。
- `setup_feishu_tables.py`：创建或协调飞书表。
- `render_rule_docs.py`：从 `guidance/` 和 `reference/` 下的机器 JSON 生成或
  检查人工可读的 Markdown 审核视图。
- `rebuild_reddit_resources.py`：把 `guidance/reddit/` 下的 Markdown 渲染成
  `resource/reddit/pdfs/` 下的 PDF。

## 共享运行时模块

- `resource_paths.py`：唯一权威的文件系统路径映射。
- `weekly_post_rules.py`：周策略加载器和辅助函数。
- `feishu_client.py`、`feishu_docs.py`：飞书传输和文档辅助。
- `official_blog_catalog.py`、`fetch_blog.py`：官方博客元数据和正文获取辅助。
