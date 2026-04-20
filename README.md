# similar_user

这是一个基于 Neo4j 知识图谱实现相似用户检索的项目骨架。

当前仓库已经包含最小可运行的 Neo4j 连接脚本和 HTTP 调试接口，便于后续继续补充相似用户检索逻辑。

## 代码目录

```text
similar_user/
├── config/
│   ├── settings.yaml           # 统一配置：Neo4j、查询、候选排序和相似度
│   └── settings.py             # YAML 配置加载入口
├── data/
│   └── pattern_paths/          # 固定模式路径离线结果存储
├── logs/
│   └── similar_user.log        # 默认日志文件
├── scripts/
│   ├── build_similar_user_candidates.py  # 从 top-k 评分路径构建 top-k 候选相似用户
│   ├── debug_patient_pattern_paths.py    # 调试固定模式路径查询
│   ├── debug_query.py                    # 直接连接 Neo4j 并执行验证查询
│   ├── read_patient_pattern_result.py    # 读取本地离线保存的路径结果
│   ├── run_api.py                        # 启动本地 HTTP 调试服务
│   └── score_patient_pattern_result.py   # 对离线保存的路径结果打分
├── src/similar_user/
│   ├── api/
│   │   ├── app.py              # 最小 HTTP 服务，提供 /health/neo4j 和 /query
│   │   ├── routes/
│   │   │   └── user_routes.py  # 用户查询路由
│   │   └── schemas.py          # 请求与响应结构
│   ├── data_access/
│   │   ├── cypher_queries/              # 按主题拆分的 Cypher 查询定义
│   │   │   ├── __init__.py              # 查询常量导出入口
│   │   │   ├── patient_dates.py         # 患者训练日期、游戏与常模分查询
│   │   │   ├── pattern_paths.py         # 固定模式路径查询
│   │   │   └── pattern_statistics.py    # 固定模式路径统计查询
│   │   ├── kg_repository.py             # 图谱读取仓储
│   │   └── neo4j_client.py              # Neo4j 驱动封装
│   ├── domain/
│   │   ├── graph_schema.py     # 固定路径模式定义
│   │   ├── item.py             # TaskInstanceSet / TaskInstance / Game 节点模型
│   │   ├── path_models.py      # 固定模式路径领域对象
│   │   └── user.py             # 患者领域模型
│   ├── pipelines/              # 构图、同步、相似度计算等批处理入口
│   ├── services/
│   │   ├── path_scoring.py     # 固定模式路径规则打分
│   │   ├── similarity/         # 相似度服务实现
│   │   │   ├── base.py         # 相似度计算基础接口
│   │   │   ├── embedding.py    # Embedding 相似度方法占位
│   │   │   ├── graph_similarity.py      # 图谱相似度方法占位
│   │   │   └── utils.py        # 相似度辅助计算
│   │   └── user_service.py     # 用户查询服务
│   └── utils/
│       ├── logger.py           # 日志工具
│       ├── metrics.py          # 指标工具
│       ├── helpers.py          # 辅助函数
│       └── pattern_storage.py  # 固定模式路径离线存取
├── tests/
│   ├── test_api_app.py         # HTTP 健康检查与查询接口测试
│   ├── test_domain_models.py   # 领域模型测试
│   ├── test_kg_repository.py   # 图谱仓储测试
│   ├── test_logger.py          # 日志工具测试
│   ├── test_neo4j_client.py    # Neo4j 客户端测试
│   ├── test_path_scoring.py              # 路径打分测试
│   ├── test_pattern_storage.py           # 离线存储测试
│   ├── test_read_patient_pattern_result.py # 离线读取脚本测试
│   ├── test_similar_user_candidates.py   # 候选相似用户构建测试
│   ├── test_similarity_utils.py          # 相似度辅助计算测试
│   └── test_user_service.py              # 用户服务测试
├── pyproject.toml              # 项目依赖声明与打包配置
└── README.md
```

## 当前可用能力

- `python scripts/debug_query.py`
  用于直接验证 `config/settings.yaml` 中的 Neo4j 连接是否可用。
- `python scripts/run_api.py --host 127.0.0.1 --port 8010`
  启动本地 HTTP 服务。
- `python scripts/run_similar_user_pipeline.py <patient_id>`
  一键执行固定模式 path 检索保存、path 打分和候选相似用户聚合排序。
- `python scripts/build_similar_user_candidates.py <patient_id>`
  按 `config/settings.yaml` 中的 `query.candidate_ranking.path_top_k` 先保留高分 path 作为证据来源，再按 `query.candidate_ranking.candidate_top_k` 返回排序后的候选相似用户。
- `GET /health/neo4j`
  用于检查 Neo4j 是否可连接。
- `POST /query`
  用于提交 Cypher 查询并返回结果，适合本地调试。

## 脚本用法

以下脚本默认读取 `config/settings.yaml`。需要临时指定另一份统一配置文件时，支持 `--config` 的脚本可以传入配置路径。

```bash
# 验证 Neo4j 连接
python scripts/debug_query.py

# 从 path 生成到候选用户生成的一键主流程
python scripts/run_similar_user_pipeline.py <patient_id>
python scripts/run_similar_user_pipeline.py <patient_id> --config config/settings.yaml
python scripts/run_similar_user_pipeline.py <patient_id> --skip-path-build
python scripts/run_similar_user_pipeline.py <patient_id> --full-output

# 运行固定模式路径检索并保存离线结果
python scripts/debug_patient_pattern_paths.py <patient_id>
python scripts/debug_patient_pattern_paths.py <patient_id> --config config/settings.yaml

# 对已保存的固定模式路径打分
python scripts/score_patient_pattern_result.py <patient_id>
python scripts/score_patient_pattern_result.py <patient_id> --config config/settings.yaml
python scripts/score_patient_pattern_result.py <patient_id> --path-index 0
python scripts/score_patient_pattern_result.py <patient_id> --top-k 20

# 读取已保存的固定模式路径结果
python scripts/read_patient_pattern_result.py <patient_id>
python scripts/read_patient_pattern_result.py <patient_id> --config config/settings.yaml

# 从配置的 path_top_k / candidate_top_k 构建候选相似用户
python scripts/build_similar_user_candidates.py <patient_id>
python scripts/build_similar_user_candidates.py <patient_id> --config config/settings.yaml
```

`run_similar_user_pipeline.py` 默认会先重新生成并保存固定模式 path，再读取保存结果打分并生成候选用户。如果已经有可用的离线路径结果，可以使用 `--skip-path-build` 跳过 path 检索。脚本默认只输出核心摘要，候选用户仅以 `candidate_ids` 列出全部 `patient_id`。需要查看完整 `candidate_result` 和候选明细时，使用 `--full-output`。

`build_similar_user_candidates.py` 读取配置文件中的 `query.candidate_ranking`；如需调整候选排序范围，直接修改 YAML：

```yaml
query:
  candidate_ranking:
    path_top_k: 50
    candidate_top_k: 10
```

## 目录说明

- `config/`：统一 YAML 配置和配置加载入口
- `data/pattern_paths/`：固定模式路径的离线 JSONL 数据
- `logs/`：运行日志输出
- `src/similar_user/data_access/`：Neo4j 访问与仓储封装
- `src/similar_user/domain/`：图谱节点、路径模式和领域模型
- `src/similar_user/services/`：用户服务、相似度服务和路径打分逻辑
- `src/similar_user/pipelines/`：批处理或同步任务入口
- `src/similar_user/api/`：HTTP 服务入口、路由与数据结构
- `src/similar_user/utils/`：日志、指标、辅助函数和离线存储工具
- `tests/`：针对性测试
- `scripts/`：本地调试、离线读取和路径打分脚本

## 配置说明

`config/settings.yaml` 统一归纳 Neo4j、查询、候选排序和相似度配置。`query.graph_path_limit.per_g_strategy` 当前支持以下取值：

- `band`：按 `gCount` 命中 `bands` 配置中的区间，直接使用对应的 `per_g`
- `p2_div_g`：按 `ceil(p2Count / gCount)` 计算 `per_g`

一个示例配置如下：

```yaml
query:
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

候选用户聚合排序使用 `query.candidate_ranking` 配置：

```yaml
query:
  candidate_ranking:
    path_top_k: 50       # 先保留多少条高分 path 作为证据来源
    candidate_top_k: 10  # 最终返回多少个候选相似用户
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
  - get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date(...)
  |
  v
拿到 paths
  |
  v
组装结果
  - patient_id
  - ordered_training_dates
  - statistics
    - split_training_date
    - before_split
    - post_split_games
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
  "ordered_training_dates": ["2022-04-01", "2022-04-08", "2022-04-15", "2022-04-22", "2022-04-29"],
  "statistics": {
    "split_training_date": "2022-04-22",
    "before_split": {
      "totalPaths": 20,
      "gCount": 5,
      "p2Count": 6
    },
    "post_split_games": [
      {"trainingDate": "2022-04-22", "games": [{"id": "8", "name": "打怪物"}]},
      {"trainingDate": "2022-04-29", "games": [{"id": "15", "name": "拼图"}]}
    ]
  },
  "limit_recommendation": {"per_g": 5, "limit": 10},
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

其中 `statistics.post_split_games` 表示从切分点开始收集到的后半段游戏数据，用于表达切分后的观察窗口；它不是严格不重叠意义上的“验证集”。

这样设计的原因是：

- 避免“小文件过多”的问题
- 方便追加写入和流式读取
- 后续新增其他模式时，只需增加新的 `pattern` 文件
- 读取时可以先按 `pattern` 找文件，再按 `patient_id` 找对应记录

建议将“离线存储格式”和“运行时类对象”分开处理：

- 保存时：保留结构化 JSON 数据
- 读取时：再根据 `pattern` 转换成对应的领域类
