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
│   ├── build_similar_user_candidates.py  # 从已评分路径构建 top-k 候选相似用户
│   ├── build_pattern_paths.py            # 构建并保存固定模式路径
│   ├── debug_query.py                    # 直接连接 Neo4j 并执行验证查询
│   ├── read_patient_pattern_result.py    # 读取本地离线保存的路径结果
│   ├── run_api.py                        # 启动本地 HTTP 调试服务
│   └── score_pattern_paths.py            # 对离线保存的 pattern paths 打分
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
- `python scripts/run_similar_user_pipeline.py <patient_id> --base-date <YYYY-MM-DD> --window-days <days>`
  一键执行固定模式 path 检索保存、path 打分和候选相似用户聚合排序。
- `python scripts/predict_training_tasks.py <patient_id> --base-date <YYYY-MM-DD> --window-days <days>`
  一键执行相似用户候选生成并预测训练任务。
- `python scripts/evaluate_predict_training_tasks.py [patient_ids_file] --base-date <YYYY-MM-DD> --window-days <days>`
  评估 `base_date` 当天训练任务预测表现；可传用户列表文件，也可不传并自动从 Neo4j 读取全量 Patient ID。
- `python scripts/build_similar_user_candidates.py <patient_id>`
  读取已保存的 scored paths，并按 `config/settings.yaml` 中的 `query.candidate_ranking.candidate_top_k` 返回排序后的候选相似用户。
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
python scripts/run_similar_user_pipeline.py <patient_id> --base-date 2022-05-22 --window-days 14
python scripts/run_similar_user_pipeline.py <patient_id> --base-date 2022-05-22 --window-days 14 --config config/settings.yaml
python scripts/run_similar_user_pipeline.py <patient_id> --base-date 2022-05-22 --window-days 14 --skip-path-build
python scripts/run_similar_user_pipeline.py <patient_id> --base-date 2022-05-22 --window-days 14 --output-level scores
python scripts/run_similar_user_pipeline.py <patient_id> --base-date 2022-05-22 --window-days 14 --output-level full

# 运行固定模式路径检索并保存离线结果
python scripts/build_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --window-days 14
python scripts/build_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --window-days 14 --config config/settings.yaml
python scripts/build_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --window-days 14 --query-family training_order
python scripts/build_pattern_paths.py --source-id <patient_id> --patterns-from-config --base-date 2022-05-22 --window-days 14 --query-family training_order
python scripts/run_monthly_pattern_paths.py --window-days 14 --query-family training_order

# 从 Neo4j 同步 disease/symptom/unknown direct path 到 SQLite
python scripts/sync_direct_path_cache.py
python scripts/sync_direct_path_cache.py --pattern disease_patient
python scripts/sync_direct_path_cache.py --pattern symptom_patient
python scripts/sync_direct_path_cache.py --pattern unknown_patient
python scripts/sync_direct_path_cache.py --pattern disease_patient --force-full-refresh

# 基于 direct path 缓存或 Neo4j 构建疾病/症状/未知实体开头的 path 结果
python scripts/build_direct_entity_paths.py
python scripts/build_direct_entity_paths.py --disease-id AU_DIS_0029
python scripts/build_direct_entity_paths.py --symptom-id <symptom_id>
python scripts/build_direct_entity_paths.py --unknown-id <unknown_id>

# 对已保存的固定模式路径打分
python scripts/score_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --window-days 14 --query-family training_order
python scripts/score_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --window-days 14 --query-family training_order --config config/settings.yaml
python scripts/score_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --window-days 14 --query-family training_order --path-index 0
python scripts/score_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --window-days 14 --query-family training_order --scored-paths-dir data/scored_pattern_paths
python scripts/score_pattern_paths.py --source-id <patient_id> --patterns-from-config --base-date 2022-05-22 --window-days 14 --query-family training_order

# 读取已保存的固定模式路径结果
python scripts/read_patient_pattern_result.py <patient_id>
python scripts/read_patient_pattern_result.py <patient_id> --config config/settings.yaml

# 从已保存 scored paths 构建候选相似用户
python scripts/build_similar_user_candidates.py <patient_id>
python scripts/build_similar_user_candidates.py <patient_id> --config config/settings.yaml
python scripts/build_similar_user_candidates.py <patient_id> --scored-paths-dir data/scored_pattern_paths
python scripts/build_similar_user_candidates.py <patient_id> --candidates-dir data/similar_user_candidates

# 单用户训练任务预测
python scripts/predict_training_tasks.py <patient_id> --base-date 2022-05-22 --window-days 14
python scripts/predict_training_tasks.py <patient_id> --base-date 2022-05-22 --window-days 14 --skip-path-build
python scripts/predict_training_tasks.py <patient_id> --base-date 2022-05-22 --window-days 14 --dry-run --output-level full

# 批量评估（传用户列表文件）
python scripts/evaluate_predict_training_tasks.py data/patient_ids.txt --base-date 2022-05-22 --window-days 14 --skip-path-build

# 批量评估（不传用户列表，自动从 Neo4j 读取全量 Patient ID）
python scripts/evaluate_predict_training_tasks.py --base-date 2022-05-22 --window-days 14 --skip-path-build

# 批量评估（不传用户列表，只评估 base_date 当天有训练记录的用户）
python scripts/evaluate_predict_training_tasks.py --base-date 2022-05-22 --window-days 14 --active-on-base-date --limit 40 --dry-run

# 小样本冒烟：限制评估前 N 个用户，并跳过 LLM 调用
python scripts/evaluate_predict_training_tasks.py --base-date 2022-05-22 --window-days 14 --limit 10 --dry-run

# 调参实验：按实验 YAML 批量运行，并按 stage 隔离输出目录
python scripts/run_evaluation_grid.py --experiment-config config/experiments/evaluation_grid.yaml
python scripts/run_evaluation_grid.py --experiment-config config/experiments/evaluation_grid.yaml --dry-run
python scripts/run_evaluation_grid.py --experiment-config config/experiments/evaluation_grid.yaml --force
python scripts/run_evaluation_grid.py --experiment-config config/experiments/evaluation_grid.yaml --write-promoted-baseline
```

`run_similar_user_pipeline.py` 默认会先重新生成并保存固定模式 path，再读取保存结果打分并生成候选用户。如果已经有可用的离线路径结果，可以使用 `--skip-path-build` 跳过 path 检索。脚本默认使用 `--output-level ids`，候选用户仅以 `candidate_ids` 列出全部 `patient_id`；使用 `--output-level scores` 时输出 `patient_id` 和 `candidate_score`；使用 `--output-level full` 时输出完整 `candidate_result` 和候选明细。

`build_pattern_paths.py --patterns-from-config` 会读取 `query.candidate_ranking.patterns` 并依次构建这些 patient 起点模式的离线 path；如果 YAML 中配置了 `disease_patient`、`symptom_patient`、`unknown_patient` 这类 direct 模式，脚本会报错，避免把 patient_id 与 disease_id/symptom_id/unknown_id 混用。建议显式传入 `--query-family training_order`，这样生成的 `data/pattern_paths/{path_key}/...` 与后续评分命令使用的缓存上下文完全一致。

`score_pattern_paths.py` 默认会保存评分明细和摘要。`--patterns-from-config` 会读取 `query.candidate_ranking.patterns` 并依次评分这些 patient 起点模式；`--path-index` 仅用于单条 path 调试，不会保存评分文件。评分复用已保存 path 时，应传入与构建 path 相同的 `--base-date`、`--window-days` 和 `--query-family`，脚本会用这些参数定位并校验对应的 `path_key`。

`build_similar_user_candidates.py` 读取配置文件中的 `query.candidate_ranking`，默认会保存完整候选明细和轻量摘要到 `data/similar_user_candidates/`。如需调整候选返回数量，直接修改 YAML：

```yaml
query:
  candidate_ranking:
    patterns:
      - "patient_game_patient"
      - "patient_disease_patient"
      - "patient_symptom_patient"
      - "patient_unknown_patient"
    candidate_top_k: 10
```

### 缓存 key 与配置变更关系

离线路径、路径评分和候选用户结果分别用不同 key 隔离缓存。写实验 YAML 时，可以先判断本次修改影响哪一层 key，再决定是否能使用 `skip_path_build` / `skip_path_scoring` 复用已有结果。

`path_key` 决定原始 path 缓存目录，保存到 `data/pattern_paths/{path_key}/{pattern}/...`。它由以下内容决定：

- `base.base_date` 或命令行 `--base-date`
- `base.window_days` 或命令行 `--window-days`
- `base.query_family` 或命令行 `--query-family`
- `query.graph_path_limit` 整段配置

如果改了以上任一项，对应的 `path_key` 会变化，需要已有同 key 的 path 文件才能设置 `skip_path_build: true`。`query.candidate_ranking.patterns` 不写进 `path_key` 本身，但每个 pattern 是 `path_key` 下的子目录；新增或删除 pattern 时，也要确认对应 pattern 的 path 文件是否已经生成。

`scored_key` 决定已评分 path 缓存目录，保存到 `data/scored_pattern_paths/{scored_key}/{pattern}/...`。它由以下内容决定：

- 上一层的 `path_key`
- `query.score_pattern_paths.top_k`

如果改了 `base_date`、`window_days`、`query_family`、`query.graph_path_limit` 或 `query.score_pattern_paths.top_k`，对应的 `scored_key` 会变化，需要已有同 key 的 scored path 文件才能设置 `skip_path_scoring: true`。

`candidate_key` 决定候选相似用户缓存目录，保存到 `data/similar_user_candidates/{candidate_key}/...`。它由以下内容决定：

- 上一层的 `scored_key`
- `query.candidate_ranking.patterns`
- `query.candidate_ranking.candidate_top_k`
- `query.candidate_ranking.total_score_match_top_k`
- `query.candidate_ranking.disease_course_window_days`
- `query.candidate_ranking.scoring`

如果只改这些候选聚合参数，通常可以继续复用已有 path 和 scored path，也就是可以保留 `skip_path_build: true` 和 `skip_path_scoring: true`，让程序重新生成新的 candidate 缓存。

`query.training_task_prediction`、`task_top_k`、`use_llm`、prompt 模板等预测评估参数不进入 path、scored path 或 candidate key。它们主要影响预测结果和评估输出；在 `run_evaluation_grid.py` 中，不同实验会通过不同 run 目录隔离评估结果。

常见判断方式：

| 修改内容 | path_key | scored_key | candidate_key | skip 建议 |
| --- | --- | --- | --- | --- |
| `base_date` / `window_days` / `query_family` | 变 | 变 | 变 | 不能跳过，除非对应 key 缓存已存在 |
| `query.graph_path_limit` | 变 | 变 | 变 | 不能跳过，除非对应 key 缓存已存在 |
| `query.score_pattern_paths.top_k` | 不变 | 变 | 变 | 可跳过 path build；不能跳过 scoring，除非 scored 缓存已存在 |
| `query.candidate_ranking.patterns` | 不变 | 不变 | 变 | 可跳过 build/scoring，但要确保每个 pattern 的 scored 文件存在 |
| `candidate_top_k` / `total_score_match_top_k` / `disease_course_window_days` / `candidate_ranking.scoring` | 不变 | 不变 | 变 | 可跳过 build/scoring |
| `training_task_prediction` / `task_top_k` / prompt 相关参数 | 不变 | 不变 | 不变 | 可跳过 build/scoring，候选缓存也可复用 |

一句话规则：改了 path 层参数就要有新的 path；改了 scoring 层参数就要有新的 scored path；只改候选或 prompt 参数时，通常可以复用前两层缓存。

## 目录说明

- `config/`：统一 YAML 配置和配置加载入口
- `data/pattern_paths/`：固定模式路径的离线 JSONL 数据
- `data/scored_pattern_paths/`：固定模式路径评分后的 detail/summary JSON 数据
- `data/similar_user_candidates/`：候选相似用户聚合后的 detail/summary JSON 数据
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
    patterns:            # 候选聚合读取哪些已保存 scored path 模式
      - "patient_game_patient"
      - "patient_disease_patient"
      - "patient_symptom_patient"
      - "patient_unknown_patient"
    candidate_top_k: 10  # 最终返回多少个候选相似用户
```

`predict_training_tasks.py` 支持 `--dry-run`（跳过 LLM，仅验证链路）和 `--skip-path-build`（复用已保存 path 结果）。

### 完成度与活跃度证据解释

训练任务推荐可以把相似用户任务记录中的完成度和活跃度作为附加证据。当前业务取值是二值信号：

- 完成度：`完成` / `未完成`
- 活跃度：`是` / `否`

这两个字段不建议作为硬过滤条件，更适合用于解释证据强弱和辅助排序：

| 活跃度 | 完成度 | 证据解释 |
| --- | --- | --- |
| 活跃 | 完成 | 最强正证据。说明活跃相似用户做了这个任务并完成了，推荐价值最高。 |
| 活跃 | 未完成 | 重要但有风险的证据。说明任务确实出现在活跃相似用户训练中，但可能偏难或体验不好。适合保留，但排序应低于“活跃 + 完成”。 |
| 不活跃 | 完成 | 中等证据。任务可完成，但来源用户不活跃，证据稳定性弱。 |
| 不活跃 | 未完成 | 最弱证据。一般只作为补充信息，不应主导推荐。 |

推荐策略上，活跃度更适合作为“证据可信度”信号，完成度更适合作为“任务适配质量”信号。第一版实验建议先把这些统计写入 prompt 或任务证据明细，不直接删除候选任务，避免因为二值信号过强而损失候选池覆盖率。

### 目标用户完成度与活跃度解释

目标用户自己的完成度和活跃度更适合用于判断个体适配风险，而不是相似用户证据强弱：

| 活跃度 | 完成度 | 个体适配解释 |
| --- | --- | --- |
| 活跃 | 完成 | 目标用户状态好，且该任务可完成。这个任务可作为强正向历史证据。 |
| 活跃 | 未完成 | 目标用户愿意参与，但该任务没完成。可能是难度偏高或任务不适配。任务可保留为训练目标，但推荐时要谨慎。 |
| 不活跃 | 完成 | 目标用户整体参与度弱，但该任务曾经能完成。适合作为低风险、恢复训练的候选。 |
| 不活跃 | 未完成 | 目标用户参与弱，且任务没完成。风险最高，不应作为优先推荐，除非有非常强的相似用户证据或业务明确要训练该能力。 |

一句话综述：相似用户的完成度/活跃度用于评估“证据质量”；目标用户的完成度/活跃度用于评估“个体适配风险”。

`evaluate_predict_training_tasks.py` 评估的是 `base_date` 当天真实训练任务与预测任务集合的命中情况；`patient_ids_file` 可选，不传时会通过 Neo4j 查询全量 Patient ID。`--active-on-base-date` 会在不传 `patient_ids_file` 时只读取 `base_date` 当天有训练记录的用户，适合减少 `actual_game_ids` 为空的不可评估样本。`--limit` 可用于小样本冒烟。

评估脚本默认会输出两个文件：

- `data/evaluation/predict_training_tasks_summary.json`：整体指标汇总，例如 `total_count`、`failed_count`、`task_hit_rate`、`micro_precision`、`micro_recall`。
- `data/evaluation/predict_training_tasks_details.jsonl`：逐用户明细，每行一个 JSON 对象，包含 `patient_id`、`status`、`predicted_game_ids`、`actual_game_ids`、`matched_game_ids`、`precision`、`recall`、`f1`。如果某个用户失败，会记录 `error_type` 和 `error_message`，用于定位 `failed_count` 的原因。

查看失败原因示例：

```bash
grep '"status": "failed"' data/evaluation/predict_training_tasks_details.jsonl | head -n 5
```

### 评估调参实验

`scripts/run_evaluation_grid.py` 用于按实验 YAML 批量运行训练任务预测评估。推荐一个阶段一份 YAML，避免 10 用户粗筛、100 用户复验和多日期验证互相覆盖：

```text
config/experiments/evaluation_grid_coarse_10_users.yaml
config/experiments/evaluation_grid_validate_100_users.yaml
config/experiments/evaluation_grid_multi_date.yaml
```

每份实验 YAML 通过 `stage` 隔离输出目录。例如：

```yaml
stage: "coarse_10_users"

base:
  base_date: "2023-10-15"
  window_days: 14
  task_top_k: 7
  use_llm: true
  skip_path_build: true
  limit: 10

baseline_overrides:
  query.candidate_ranking.disease_course_window_days: 14
  query.candidate_ranking.total_score_match_top_k: 1

experiments:
  - name: baseline_best
    overrides: {}

  - name: prompt_template_v1
    overrides:
      query.training_task_prediction.prompt_template_name: "TASK_PREDICTION_PROMPT_TEMPLATE_V1"
```

实际参数合并规则：

```text
settings.yaml + baseline_overrides + 当前 experiment.overrides
```

如果 `experiment.overrides` 和 `baseline_overrides` 有相同参数，以 `experiment.overrides` 为准。

执行 10 用户粗筛：

```bash
python scripts/run_evaluation_grid.py \
  --experiment-config config/experiments/evaluation_grid_coarse_10_users.yaml
```

执行 100 用户复验时，复制一份新 YAML，修改 `stage` 和 `base.limit`：

```yaml
stage: "validate_100_users"

base:
  limit: 100
```

然后执行：

```bash
python scripts/run_evaluation_grid.py \
  --experiment-config config/experiments/evaluation_grid_validate_100_users.yaml
```

输出目录会按 `stage` 自动分开：

```text
data/evaluation_grid/coarse-10-users/
data/evaluation_grid/validate-100-users/
```

每个 stage 目录下会生成：

```text
generated_configs/   # 每组实验生成的临时 settings YAML
runs/                # 每组实验的评估输出
logs/                # 每组实验日志
leaderboard.csv      # 按指标排序的排行榜
leaderboard.json
grid_summary.json
```

如果某组实验目录下已经存在 `predict_training_tasks_summary.json`，默认会跳过；需要强制重跑时加 `--force`。

回写推荐基准参数时使用：

```bash
python scripts/run_evaluation_grid.py \
  --experiment-config config/experiments/evaluation_grid_coarse_10_users.yaml \
  --write-promoted-baseline
```

该命令会把 leaderboard 第一名写入当前 `--experiment-config` 指定的 YAML 文件的 `promoted_baseline_overrides`，但不会修改正在生效的 `baseline_overrides`。如果文件中已经存在 `promoted_baseline_overrides`，旧块会被注释保留，新块写在后面。确认后可人工将 `promoted_baseline_overrides.overrides` 提升到 `baseline_overrides`。

## 特定模式路径主流程

下面这段流程用于说明：当程序需要获取某个患者在固定模式下的路径时，可以如何利用患者训练日期、统计查询和路径查询进行编排。

```text
开始
  |
  v
输入 patient_id
  |
  v
外部输入 base_date / window_days
  |
  v
构建 path_window
  - start_date = base_date - window_days
  - end_date = base_date
  - 语义: [start_date, end_date)
  |
  v
按 path_window 调用统计查询
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
  - get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_date_range(...)
  |
  v
拿到 paths
  |
  v
组装结果
  - patient_id
  - retrieval_context
    - base_date
    - path_window
    - window_statistics
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
  "ordered_training_dates": [],
  "first_training_date": null,
  "last_training_date": null,
  "training_date_count": 0,
  "retrieval_context": {
    "base_date": "2022-05-22",
    "path_window": {
      "base_date": "2022-05-22",
      "start_date": "2022-05-08",
      "end_date": "2022-05-22",
      "window_days": 14,
      "range_semantics": "[start_date, end_date)"
    },
    "window_statistics": {
      "totalPaths": 20,
      "gCount": 5,
      "p2Count": 6
    },
    "limit_recommendation": {"per_g": 5, "limit": 10},
    "paths": [
      {
        "row": {
          "p": {"id": "40", "name": "患者_40", "性别": "女"},
          "s1": {"id": "40_20220516", "name": "事件_40_20220516", "训练日期": "2022-05-16", "执行年龄": "15.0", "执行学历": "小学6年级"},
          "i1": {"id": "40_20220516_8_x", "name": "任务_x"},
          "g": {"id": "8", "name": "打怪物"},
          "i2": {"id": "20102799_20220510_8_y", "name": "任务_y"},
          "s2": {"id": "20102799_20220510", "name": "事件_20102799_20220510", "训练日期": "2022-05-10", "执行年龄": "89.0", "执行学历": "初中"},
          "p2": {"id": "20102799", "name": "患者_20102799", "性别": "女"}
        }
      }
    ]
  }
}
```

其中 `retrieval_context.path_window` 是 path 生成的唯一时间范围来源，使用左闭右开语义：`start_date <= 训练日期 < end_date`。

这样设计的原因是：

- 避免“小文件过多”的问题
- 方便追加写入和流式读取
- 后续新增其他模式时，只需增加新的 `pattern` 文件
- 读取时可以先按 `pattern` 找文件，再按 `patient_id` 找对应记录

建议将“离线存储格式”和“运行时类对象”分开处理：

- 保存时：保留结构化 JSON 数据
- 读取时：再根据 `pattern` 转换成对应的领域类
