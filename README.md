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

## Query 配置说明

`config/query.yaml` 中的 `graph_path_limit.per_g_strategy` 当前支持以下取值：

- `band`：按 `gCount` 命中 `bands` 配置中的区间，直接使用对应的 `per_g`
- `p2_div_g`：按 `ceil(p2Count / gCount)` 计算 `per_g`

一个示例配置如下：

```yaml
graph_path_limit:
  per_g_strategy: "band"
  bands:
    - max_g_count: 49
      per_g: 10
    - max_g_count: 199
      per_g: 6
    - per_g: 4
  max_limit_source: "total_paths"
```

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
按训练日期切分并调用统计查询
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
调用 recommend_graph_path_limit(total_paths, g_count, p2_count)
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
  - get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_start_date(...)
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

## 离线保存约定

对于固定模式路径的离线保存，建议按 `pattern` 维度存储 JSONL，而不是按“每个用户一个 JSON 文件”拆分。

推荐目录和文件形式如下：

```text
data/
└── pattern_paths/
    └── PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT.jsonl
```

其中：

- 一个 `pattern` 对应一个 JSONL 文件
- 每一行代表一个用户在该模式下的一批路径结果
- 每行都保留 `patient_id` 和 `pattern` 字段，便于后续读取和校验

推荐的单行数据结构如下：

```json
{
  "patient_id": "40",
  "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
  "paths": [
    {
      "p": {"id": "40", "name": "患者_40", "性别": "女"},
      "s1": {"id": "40_20220401", "name": "事件_40_20220401", "训练日期": "2022-04-01", "执行年龄": "15.0", "执行学历": "小学6年级"},
      "i1": {"id": "40_20220401_8_x", "name": "任务_x"},
      "g": {"id": "8", "name": "打怪物"},
      "i2": {"id": "20102799_20230123_8_y", "name": "任务_y"},
      "s2": {"id": "20102799_20230123", "name": "事件_20102799_20230123", "训练日期": "2023-01-23", "执行年龄": "89.0", "执行学历": "初中"},
      "p2": {"id": "20102799", "name": "患者_20102799", "性别": "女"}
    }
  ]
}
```

这样设计的原因是：

- 避免“小文件过多”的问题
- 方便追加写入和流式读取
- 后续新增其他模式时，只需增加新的 `pattern` 文件
- 读取时可以先按 `pattern` 找文件，再按 `patient_id` 找对应记录

建议将“离线存储格式”和“运行时类对象”分开处理：

- 保存时：保留结构化 JSON 数据
- 读取时：再根据 `pattern` 转换成对应的领域类
