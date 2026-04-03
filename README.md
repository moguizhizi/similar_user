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
