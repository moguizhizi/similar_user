# similar_user

这是一个基于 Neo4j 知识图谱实现相似用户检索的项目骨架。

当前仓库已经包含最小可运行的 Neo4j 连接脚本和 HTTP 调试接口，便于后续继续补充相似用户检索逻辑。

## 代码目录

```text
similar_user/
├── config/
│   ├── neo4j.yaml              # Neo4j 连接配置
│   ├── similarity.yaml         # 相似度相关配置占位
│   └── settings.py             # YAML 配置加载入口
├── scripts/
│   ├── debug_query.py          # 直接连接 Neo4j 并执行验证查询
│   └── run_api.py              # 启动本地 HTTP 调试服务
├── src/similar_user/
│   ├── api/
│   │   ├── app.py              # 最小 HTTP 服务，提供 /health/neo4j 和 /query
│   │   ├── routes/             # 业务路由占位
│   │   └── schemas.py          # 请求与响应结构占位
│   ├── data_access/
│   │   ├── neo4j_client.py     # Neo4j 驱动封装
│   │   ├── cypher_queries.py   # Cypher 查询定义占位
│   │   └── kg_repository.py    # 图谱读取仓储接口占位
│   ├── domain/                 # 用户、物品、图谱结构等领域模型
│   ├── pipelines/              # 构图、同步、相似度计算等批处理入口
│   ├── services/               # 业务服务层
│   └── utils/                  # 日志、指标、辅助函数
├── tests/
│   ├── test_neo4j_client.py    # Neo4j 客户端和调试脚本测试
│   └── test_api_app.py         # HTTP 健康检查与查询接口测试
└── README.md
```

## 当前可用能力

- `python scripts/debug_query.py`
  用于直接验证 `config/neo4j.yaml` 中的 Neo4j 连接是否可用。
- `python scripts/run_api.py --host 127.0.0.1 --port 8010`
  启动本地 HTTP 服务。
- `GET /health/neo4j`
  用于检查 Neo4j 是否可连接。
- `POST /query`
  用于提交 Cypher 查询并返回结果，适合本地调试。

## 目录说明

- `config/`：配置文件与配置加载
- `src/similar_user/data_access/`：Neo4j 访问与仓储接口
- `src/similar_user/domain/`：领域数据结构
- `src/similar_user/services/`：核心业务逻辑
- `src/similar_user/pipelines/`：批处理或同步任务入口
- `src/similar_user/api/`：服务化接口
- `src/similar_user/utils/`：通用工具
- `tests/`：针对性测试
- `scripts/`：临时调试脚本

## 特定模式路径主流程

下面这段流程用于说明：当程序需要获取某个患者在固定模式下的路径时，可以如何利用患者训练日期、统计查询和路径查询进行编排。

```text
开始
  |
  v
输入 patient_id
  |
  v
调用 get_patient_ordered_training_dates(patient_id)
  |
  v
是否拿到训练日期?
  | \
  |  \ 否
  |   v
  |  返回空结果
  |
  v 是
构建训练日期上下文
  - ordered_training_dates
  - first_training_date
  - last_training_date
  - training_date_count
  |
  v
选择统计口径
  - 无条件统计
  - 或带训练日期约束统计
  |
  v
调用统计查询
  |
  v
拿到 total_paths / g_count / p2_count
  |
  v
total_paths == 0 ?
  | \
  |  \ 是
  |   v
  |  返回仅含上下文的空结果
  |
  v 否
调用 recommend_graph_path_limit(total_paths, g_count)
  |
  v
拿到 per_g / limit
  |
  v
limit <= 0 ?
  | \
  |  \ 是
  |   v
  |  返回仅含统计和上下文的空结果
  |
  v 否
调用路径查询
  - get_patient_task_set_task_game_task_set_patient_randomized_paths(...)
  - 如果后续有 dated 版路径查询，这里切换到 dated 版
  |
  v
拿到 paths
  |
  v
组装结果
  - patient_id
  - ordered_training_dates
  - statistics
  - limit_recommendation
  - paths
  |
  v
返回结果
```
