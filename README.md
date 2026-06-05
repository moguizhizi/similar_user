# similar_user

这是一个基于 Neo4j 知识图谱实现相似用户检索和训练任务推荐的项目。

当前仓库包含患者 path 相似用户候选生成、非患者 direct entity 候选生成、训练任务预测、批量评估、实验网格、用户中心缓存和 HTTP/API 调试入口。

## 代码目录

```text
similar_user/
├── config/
│   ├── settings.yaml                 # 统一配置：Neo4j、查询、候选、预测和缓存
│   ├── settings.py                   # YAML 配置加载入口
│   └── experiments/                  # 评估实验 YAML
├── data/
│   ├── pattern_paths/                # raw path 离线结果
│   ├── scored_pattern_paths/         # scored path 结果
│   ├── similar_user_candidates/      # topK 候选相似用户结果
│   └── user_cache/                   # 用户中心缓存索引和文件
├── experiments/
│   └── neural_sequence_baseline/     # 独立神经序列 baseline 实验
├── logs/
│   └── similar_user.log              # 默认日志文件
├── scripts/
│   ├── build_pattern_paths.py        # 构建并保存患者固定模式 raw paths
│   ├── score_pattern_paths.py        # 对患者 fixed-pattern paths 打分
│   ├── build_similar_user_candidates.py
│   ├── sync_direct_path_cache.py     # 同步 direct path SQLite 缓存
│   ├── build_direct_entity_paths.py  # 构建 disease/symptom/unknown raw paths
│   ├── score_direct_entity_paths.py  # 对 direct entity paths 打分
│   ├── predict_training_tasks.py     # 患者路径训练任务预测
│   ├── predict_training_tasks_from_direct_entity.py
│   ├── predict_training_tasks_unified.py
│   ├── evaluate_predict_training_tasks.py
│   ├── evaluate_direct_entity_profiles.py
│   ├── run_evaluation_grid.py
│   ├── cleanup_user_cache.py
│   ├── run_api.py                    # http.server 调试接口
│   └── run_fastapi.py                # FastAPI 外部预测接口
├── src/similar_user/
│   ├── api/
│   │   ├── app.py                    # http.server 调试接口，提供 /health/neo4j 和 /query
│   │   ├── fastapi_app.py            # FastAPI 入口，提供 /training-task/predict
│   │   ├── external_task_prediction.py
│   │   ├── cache_cleanup_scheduler.py
│   │   ├── routes/
│   │   └── schemas.py
│   ├── data_access/
│   │   ├── cypher_queries/            # 按主题拆分的 Cypher 查询定义
│   │   ├── kg_repository.py           # 图谱读取仓储
│   │   ├── direct_path_cache_store.py # direct path SQLite 缓存
│   │   ├── user_cache_index.py        # 用户中心缓存索引
│   │   └── neo4j_client.py            # Neo4j 驱动封装
│   ├── domain/
│   │   ├── graph_schema.py           # 固定路径模式定义
│   │   ├── item.py                   # TaskInstanceSet / TaskInstance / Game 等节点模型
│   │   ├── path_models.py            # 固定模式路径领域对象
│   │   └── user.py                   # 患者领域模型
│   ├── pipelines/                    # 构图、同步、相似度计算等批处理入口
│   ├── services/
│   │   ├── path_scoring.py           # 固定模式路径规则打分
│   │   ├── task_prediction.py        # 患者路径训练任务预测
│   │   ├── task_prediction_fallback.py
│   │   ├── direct_entity_fallback_prediction.py
│   │   ├── task_recommendation_validation.py
│   │   ├── similarity/               # 相似度候选聚合
│   │   └── user_service.py
│   └── utils/
│       ├── logger.py                 # 日志工具
│       ├── metrics.py                # 指标工具
│       ├── pattern_storage.py        # path 离线存取
│       └── user_cache_paths.py       # 用户缓存路径工具
├── tests/                            # 针对脚本、服务、缓存和数据访问的测试
├── pyproject.toml                    # 项目依赖声明与打包配置
└── README.md
```

## 当前可用能力

- `python scripts/debug_query.py`
  用于直接验证 `config/settings.yaml` 中的 Neo4j 连接是否可用。
- `python scripts/run_api.py --host 127.0.0.1 --port 8010`
  启动本地 http.server 调试服务。
- `python scripts/run_fastapi.py --host 127.0.0.1 --port 8000`
  启动 FastAPI 外部预测服务。
- `python scripts/run_similar_user_pipeline.py <patient_id> --base-date <YYYY-MM-DD>`
  一键执行固定模式 path 检索保存、path 打分和候选相似用户聚合排序。
- `python scripts/predict_training_tasks.py <patient_id> --base-date <YYYY-MM-DD>`
  从患者 path 候选生成训练任务预测。
- `python scripts/predict_training_tasks_from_direct_entity.py --patient-id <patient_id> --base-date <YYYY-MM-DD> --age <age> --education <education> --gender <gender> --disease-id <disease_id>`
  从非患者 direct entity 画像生成训练任务预测。
- `python scripts/predict_training_tasks_unified.py --patient-id <patient_id> --base-date <YYYY-MM-DD>`
  按患者是否存在自动路由到患者 path 或 direct entity 预测流程。
- `python scripts/evaluate_predict_training_tasks.py --base-date <YYYY-MM-DD>`
  评估 `base_date` 当天有训练记录的患者任务预测表现。
- `python scripts/evaluate_direct_entity_profiles.py --profiles <profiles.jsonl>`
  评估 direct entity 或 unified profile 输入。
- `python scripts/build_similar_user_candidates.py <patient_id> --base-date <YYYY-MM-DD>`
  读取已保存的 scored paths，并按 `config/settings.yaml` 中的 `query.candidate_ranking.candidate_top_k` 返回排序后的候选相似用户。
- `GET /health/neo4j`
  用于检查 Neo4j 是否可连接。
- `POST /query`
  用于提交 Cypher 查询并返回结果，适合本地调试。
- `POST /training-task/predict`
  FastAPI 外部训练任务预测接口。

## 脚本用法

以下脚本默认读取 `config/settings.yaml`。需要临时指定另一份统一配置文件时，支持 `--config` 的脚本可以传入配置路径。

```bash
# 验证 Neo4j 连接
python scripts/debug_query.py

# 从 path 生成到候选用户生成的一键主流程
python scripts/run_similar_user_pipeline.py <patient_id> --base-date 2022-05-22
python scripts/run_similar_user_pipeline.py <patient_id> --base-date 2022-05-22 --config config/settings.yaml
python scripts/run_similar_user_pipeline.py <patient_id> --base-date 2022-05-22 --output-level scores
python scripts/run_similar_user_pipeline.py <patient_id> --base-date 2022-05-22 --output-level full

# 运行固定模式路径检索并保存离线结果
python scripts/build_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22
python scripts/build_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --config config/settings.yaml
python scripts/build_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --query-family training_order_source_window
python scripts/build_pattern_paths.py --source-id <patient_id> --patterns-from-config --base-date 2022-05-22 --query-family training_order_dual_window
python scripts/run_monthly_pattern_paths.py --query-family training_order_source_window

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
python scripts/score_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --query-family training_order_source_window
python scripts/score_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --query-family training_order_source_window --config config/settings.yaml
python scripts/score_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --query-family training_order_source_window --path-index 0
python scripts/score_pattern_paths.py --source-id <patient_id> --pattern patient_game_patient --base-date 2022-05-22 --query-family training_order_source_window --scored-paths-dir data/scored_pattern_paths
python scripts/score_pattern_paths.py --source-id <patient_id> --patterns-from-config --base-date 2022-05-22 --query-family training_order_dual_window

# 读取已保存的固定模式路径结果
python scripts/read_patient_pattern_result.py <patient_id> --base-date 2022-05-22
python scripts/read_patient_pattern_result.py <patient_id> --base-date 2022-05-22 --config config/settings.yaml --query-family training_order_source_window

# 从已保存 scored paths 构建候选相似用户
python scripts/build_similar_user_candidates.py <patient_id> --base-date 2022-05-22
python scripts/build_similar_user_candidates.py <patient_id> --base-date 2022-05-22 --config config/settings.yaml
python scripts/build_similar_user_candidates.py <patient_id> --base-date 2022-05-22 --scored-paths-dir data/scored_pattern_paths
python scripts/build_similar_user_candidates.py <patient_id> --base-date 2022-05-22 --candidates-dir data/similar_user_candidates

# 患者路径单用户训练任务预测
python scripts/predict_training_tasks.py <patient_id> --base-date 2022-05-22
python scripts/predict_training_tasks.py <patient_id> --base-date 2022-05-22 --dry-run --output-level full

# 非患者 direct entity 训练任务预测
python scripts/predict_training_tasks_from_direct_entity.py --patient-id <patient_id> --base-date 2022-05-22 --age 68 --education 初中 --gender 女 --disease-id AU_DIS_0029
python scripts/predict_training_tasks_from_direct_entity.py --patient-id <patient_id> --base-date 2022-05-22 --age 68 --education 初中 --gender 女 --disease-name 认知障碍 --dry-run --output-level full

# 统一入口训练任务预测
python scripts/predict_training_tasks_unified.py --patient-id <patient_id> --base-date 2022-05-22
python scripts/predict_training_tasks_unified.py --patient-id <patient_id> --base-date 2022-05-22 --age 68 --education 初中 --gender 女 --disease-name 认知障碍 --dry-run --output-level full

# 批量评估（默认生成并读取 base_date 当天有训练记录的患者列表）
python scripts/evaluate_predict_training_tasks.py --base-date 2022-05-22

# 批量评估（单个患者或小样本冒烟）
python scripts/evaluate_predict_training_tasks.py --patient-id <patient_id> --base-date 2022-05-22 --dry-run
python scripts/evaluate_predict_training_tasks.py --base-date 2022-05-22 --limit 10 --dry-run

# direct entity / unified profile 批量评估
python scripts/evaluate_direct_entity_profiles.py --profiles data/profiles.jsonl --dry-run
python scripts/evaluate_direct_entity_profiles.py --profiles data/profiles.jsonl --prediction-mode unified --dry-run

# 调参实验：按实验 YAML 批量运行，并按 stage 隔离输出目录
python scripts/run_evaluation_grid.py --experiment-config config/experiments/evaluation_grid.yaml
python scripts/run_evaluation_grid.py --experiment-config config/experiments/evaluation_grid.yaml --dry-run
python scripts/run_evaluation_grid.py --experiment-config config/experiments/evaluation_grid.yaml --force
python scripts/run_evaluation_grid.py --experiment-config config/experiments/evaluation_grid.yaml --no-write-promoted-baseline

# HTTP 服务
python scripts/run_api.py --host 127.0.0.1 --port 8010
python scripts/run_fastapi.py --host 127.0.0.1 --port 8000
```

`run_similar_user_pipeline.py` 的 CLI 会按当前配置自动补齐 raw paths、scored paths 和候选用户缓存。脚本默认使用 `--output-level ids`，候选用户仅以 `candidate_ids` 列出全部 `patient_id`；使用 `--output-level scores` 时输出 `patient_id` 和 `candidate_score`；使用 `--output-level full` 时输出完整 `candidate_result` 和候选明细。

`build_pattern_paths.py --patterns-from-config` 会读取 `query.candidate_ranking.patterns` 并依次构建这些 patient 起点模式的离线 path；如果 YAML 中配置了 `disease_patient`、`symptom_patient`、`unknown_patient` 这类 direct 模式，脚本会报错，避免把 patient_id 与 disease_id/symptom_id/unknown_id 混用。建议显式传入当前配置使用的 `--query-family`，例如 `training_order_source_window` 或 `training_order_dual_window`，这样生成的 `data/pattern_paths/{path_key}/...` 与后续评分命令使用的缓存上下文完全一致。

`score_pattern_paths.py` 默认会保存评分明细和摘要。`--patterns-from-config` 会读取 `query.candidate_ranking.patterns` 并依次评分这些 patient 起点模式；`--path-index` 仅用于单条 path 调试，不会保存评分文件。评分复用已保存 path 时，应传入与构建 path 相同的 `--base-date` 和 `--query-family`；患者 path 窗口来自 `query.patient_path.window_days`，脚本会用这些参数定位并校验对应的 `path_key`。

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

### 训练任务预测兜底流程

训练任务预测会优先走正常候选链路：患者 path 先生成 topK 相似用户并汇总候选训练任务，非患者 direct entity path 先用疾病、症状、未知实体和画像字段生成 direct entity topK 候选，再构造候选训练任务。正常链路可使用 LLM，也可在 `use_llm=false` 时直接按候选任务排序输出。

兜底主要处理“候选或推荐证据不足，无法产出可靠任务”的情况，常见触发原因包括：

- `no_candidates`：候选用户为空；患者 path 中通常表示没有可用相似用户。
- `missing_entity_input`：非患者 direct entity path 只提供画像字段，没有疾病、症状、未知实体或疾病名称，此时跳过 direct entity path 评分，直接按画像兜底。
- `no_candidate_training_tasks`：有候选用户，但候选训练任务为空。
- `no_direct_entity_candidates`：非患者 direct entity path 的 topK 候选为空。
- `no_resolved_entity_names`：非患者 direct entity path 提供了疾病名称，但没有解析到可用 Disease/Symptom/Unknown 实体。
- `llm_error` 或 LLM 输出无法解析。
- LLM/排序结果为空。

非患者 direct entity path 中，如果 topK 候选为空，会记录类似日志：

```text
Completed fallback task prediction: patient_id=..., fallback_used=True, fallback_reason=no_direct_entity_candidates, fallback_level=profile_matched_tasks, predicted_task_count=7
```

兜底层级按证据强弱依次放宽：

- `candidate_training_tasks`：候选任务已经构造出来，但 LLM 或推荐排序失败时，直接对候选任务做确定性排序。
- `profile_matched_tasks`：按年龄、性别、学历等画像条件查询相近用户历史专属任务。
- `relaxed_age_gender_tasks`：放宽学历，仅保留年龄窗口和性别。
- `relaxed_age_education_tasks`：放宽性别，仅保留年龄窗口和学历。
- `relaxed_age_tasks`：继续放宽到更大的年龄窗口。
- `global_popular_tasks`：使用全局历史中更常见的专属任务。
- `deterministic_random_tasks`：仍然没有足够证据时，按 `patient_id`、`base_date` 和任务稳定哈希排序，给出可复现的兜底任务。

预测结果和评估明细里可以通过以下字段判断是否走了兜底：

```json
{
  "fallback_used": true,
  "fallback_reason": "no_direct_entity_candidates",
  "fallback_source": "profile_matched_tasks",
  "fallback_candidates_count": 7,
  "candidate_source": {
    "source": "task_prediction_fallback",
    "fallback_level": "profile_matched_tasks",
    "levels_used": ["profile_matched_tasks"]
  }
}
```

兜底不覆盖核心画像字段校验失败。非患者 direct entity path 可以只提供 `age`、`education`、`gender` 走画像兜底，但这三个字段本身仍然需要可用；如果缺少学历，会在进入候选查询前失败：

```text
Non-patient direct entity prediction requires: education
prediction_failure_stage=input
prediction_failure_reason=missing_education
fallback_used=False
```

这类问题应通过清洗输入 profiles、补齐画像字段，或显式扩展输入缺失场景的兜底策略来处理。

### 缓存 key 与配置变更关系

离线路径、路径评分和候选用户结果分别用不同 key 隔离缓存。写实验 YAML 时，可以先判断本次修改影响哪一层 key：未命中或过期时，pipeline 会按 raw paths -> scored paths -> topK candidates 的顺序自动补算。

#### Raw paths

`path_key` 决定原始 path 缓存。旧目录保存到 `data/pattern_paths/{path_key}/{pattern}/...`；开启 `user_cache.enabled` 后，患者来源会保存到 `data/user_cache/files/patient/{bucket}/{patient_id}/raw_paths/{query_family}/window_{window_days}/config_{config_hash}/base_{base_date}/...`。

raw paths 主要由以下因素决定：

- `base.base_date` 或命令行 `--base-date`
- `query.patient_path.window_days`
- `base.query_family` 或命令行 `--query-family`
- `query.graph_path_limit` 整段配置
- source 类型和 source id，例如患者流程里的 `patient_id`
- 具体 path pattern，例如 `patient_game_patient`、`patient_disease_patient`

如果改了以上任一项，对应 raw path 缓存可能无法命中，需要重新从 Neo4j 构建。`query.candidate_ranking.patterns` 不写进 `path_key` 本身，但每个 pattern 是 `path_key` 下的独立文件/子目录；新增或删除 pattern 时，也要确认对应 pattern 的 raw path 是否已经生成。

#### Scored paths

`scored_key` 决定已评分 path 缓存。旧目录保存到 `data/scored_pattern_paths/{scored_key}/{pattern}/...`；开启 `user_cache.enabled` 后，患者来源会保存到 `data/user_cache/files/patient/{bucket}/{patient_id}/scored_paths/{query_family}/window_{window_days}/config_{config_hash}/base_{base_date}/...`。

scored paths 主要由以下因素决定：

- 上一层的 `path_key`
- `query.score_pattern_paths.top_k`
- path scoring 规则及其相关配置
- source 类型、source id 和具体 path pattern

如果改了 `base_date`、`window_days`、`query_family`、`query.graph_path_limit`、raw path 输入、评分规则或 `query.score_pattern_paths.top_k`，对应 scored path 缓存可能无法命中，需要重新评分。

#### TopK candidates

`candidate_key` 决定候选相似用户缓存。旧目录保存到 `data/similar_user_candidates/{candidate_key}/...`；开启 `user_cache.enabled` 后，患者来源会保存到 `data/user_cache/files/patient/{bucket}/{patient_id}/topk_candidates/{query_family}/window_{window_days}/config_{config_hash}/base_{base_date}/...`。

topK candidates 主要由以下因素决定：

- 上一层的 `scored_key`
- `query.candidate_ranking.patterns`
- `query.candidate_ranking.candidate_top_k`
- `query.candidate_ranking.total_score_match_top_k`
- `query.candidate_ranking.disease_course_window_days`
- `query.candidate_ranking.scoring`
- direct entity scored paths 是否参与候选聚合，即 `query.direct_entity_path_scoring.use_when_patient_exists`

如果只改这些候选聚合参数，通常可以继续复用已有 raw paths 和 scored paths，只重新生成 topK candidates。候选用户缓存命中时，`user_cache_hit=true`；未命中但 scored paths 可用时，会直接从 scored paths 聚合生成新的 topK candidates。

`query.training_task_prediction`、`task_top_k`、`use_llm`、prompt 模板等预测评估参数不进入 path、scored path 或 candidate key。它们主要影响预测结果和评估输出；在 `run_evaluation_grid.py` 中，不同实验会通过不同 run 目录隔离评估结果。

常见判断方式：

| 修改内容 | raw paths | scored paths | topK candidates | 处理方式 |
| --- | --- | --- | --- | --- |
| `base_date` / `window_days` / `query_family` | 可能变 | 可能变 | 可能变 | 命中可复用；未命中自动从缺失层开始补算 |
| `query.graph_path_limit` | 变 | 变 | 变 | 需要新的 raw paths，后续层也会重新生成 |
| `query.score_pattern_paths.top_k` | 不变 | 变 | 变 | raw paths 可复用；scored paths 和 topK candidates 重新生成 |
| `query.candidate_ranking.patterns` | 不变 | 不变 | 变 | raw/scored 可复用，但新增 pattern 必须已有 scored paths |
| `candidate_top_k` / `total_score_match_top_k` / `disease_course_window_days` / `candidate_ranking.scoring` | 不变 | 不变 | 变 | 只重新生成 topK candidates |
| `direct_entity_path_scoring.use_when_patient_exists` | 不变 | 可能变 | 变 | direct entity scored paths 可能新增，topK candidates 需要重新聚合 |
| `training_task_prediction` / `task_top_k` / prompt 相关参数 | 不变 | 不变 | 不变 | 三层缓存均可复用 |

一句话规则：改了 path 层参数就要有新的 path；改了 scoring 层参数就要有新的 scored path；只改候选或 prompt 参数时，通常可以复用前两层缓存。

### 用户缓存 SQLite 索引表

开启 `user_cache.enabled` 后，raw paths、scored paths 和 topK candidates 的文件会保存到 `user_cache.sqlite_path` 同级目录下的 `files/` 中；SQLite 只负责保存索引。比如：

```yaml
user_cache:
  enabled: true
  sqlite_path: "data/user_cache/cache_index.sqlite"
```

对应文件根目录是：

```text
data/user_cache/files/...
```

如果实验配置把 `sqlite_path` 改成：

```yaml
user_cache.sqlite_path: "data/user_cache/cache_missing_scenarios_10/cache_index.sqlite"
```

对应文件根目录就是：

```text
data/user_cache/cache_missing_scenarios_10/files/...
```

用户中心缓存索引表只有一张核心表：`user_cache_entries`，定义在 `src/similar_user/data_access/user_cache_index.py`。它记录每个缓存文件属于哪个 source、哪一层缓存、哪组配置和哪个 base date。

主要字段：

| 字段 | 含义 |
| --- | --- |
| `cache_type` | 缓存层级，支持 `raw_paths`、`scored_paths`、`scored_direct_entity_paths`、`topk_candidates` |
| `patient_id` | 消费该缓存的患者 ID；direct entity 场景也会填一个稳定 source ID |
| `source_type` | source 类型，例如 `patient` 或 `direct_entity_profile` |
| `source_id` | source 唯一 ID；患者场景通常等于 `patient_id` |
| `query_family` | 查询族，例如 `training_order_dual_window` |
| `window_days` | path 或候选窗口天数 |
| `config_hash` | 当前缓存层配置 hash；raw/scored/topK 各自独立 |
| `cached_base_date` | 这条缓存生成时使用的 base date |
| `valid_days` | 这条缓存从 `cached_base_date` 起可复用多少天 |
| `data_path` | 实际 detail/raw 文件路径 |
| `payload_json` | 附加上下文，例如 path key、score top_k、candidate key 组成信息 |
| `created_at` / `updated_at` | 索引写入和更新时间 |

缓存是否有效由 `cached_base_date` 和 `valid_days` 决定：

```text
0 <= request_base_date - cached_base_date <= valid_days
```

例如 `request_base_date=2026-05-25`、`cached_base_date=2026-05-17`、`valid_days=7` 时，差值为 8 天，所以这条缓存过期。

#### 有效期配置对应关系

`valid_days` 不是独立手写字段，而是在写入 `user_cache_entries` 时由 `config/settings.yaml` 的 `user_cache.*_valid_days` 配置填入。患者 path 和非患者 direct entity path 共用同一张 `user_cache_entries` 表，但各阶段使用的配置项不同：

| 流程 | 阶段 | SQLite `cache_type` | 典型 `source_type` | `valid_days` 来源 |
| --- | --- | --- | --- | --- |
| 患者 path | raw paths | `raw_paths` | `patient` | `user_cache.patient_raw_paths_valid_days` |
| 患者 path | scored paths | `scored_paths` | `patient` | `user_cache.patient_scored_paths_valid_days` |
| 患者 path | topK candidates | `topk_candidates` | `patient` | `user_cache.topk_candidates_valid_days` |
| 非患者 direct entity path | direct raw paths | `raw_paths` | `disease` / `symptom` / `unknown` | `user_cache.direct_raw_paths_valid_days` |
| 非患者 direct entity path | scored direct entity paths | `scored_direct_entity_paths` | `direct_entity_profile` | `user_cache.direct_scored_paths_valid_days` |
| 非患者 direct entity path | topK candidates | `topk_candidates` | `direct_entity_profile` | `user_cache.topk_candidates_valid_days` |

因此，topK candidates 的有效期标记在两条流程中是同一套：都使用 `cache_type='topk_candidates'` 和 `user_cache.topk_candidates_valid_days`。区别在于患者 path 的 `source_type='patient'`，非患者 direct entity path 的 `source_type='direct_entity_profile'`、`query_family='direct_entity'`。

direct entity scored path 在 SQLite 中登记为 `cache_type='scored_direct_entity_paths'`；它的文件目录为了沿用 scored path 存储结构，会落在 `scored_paths/direct_entity/...` 下。判断是否过期时以 SQLite 里的 `cache_type`、`cached_base_date` 和 `valid_days` 为准。

常用查看命令：

```bash
sqlite3 data/user_cache/cache_missing_scenarios_10/cache_index.sqlite \
"SELECT cache_type, patient_id, source_type, source_id, query_family,
        cached_base_date, valid_days, data_path
 FROM user_cache_entries
 WHERE patient_id='30134797'
 ORDER BY cache_type, data_path;"
```

标记某个患者的 topK candidates 过期时，可以只改索引，不删文件：

```bash
sqlite3 data/user_cache/cache_missing_scenarios_10/cache_index.sqlite \
"UPDATE user_cache_entries
 SET cached_base_date='2026-05-17'
 WHERE cache_type='topk_candidates'
   AND patient_id='30134797';"
```

验证 topK 过期场景时，预期流程是：

```text
topK candidates 过期
-> scored paths 仍有效
-> 不 rebuild raw
-> 不 rescore paths
-> 从 scored paths 重新聚合 topK candidates
-> 写入新的 topK candidates 索引和文件
```

验证 scored paths 缺失时，可以删除对应患者的 `scored_paths/` 和 `topk_candidates/` 文件，让索引指向不存在的文件；读取时会懒删除 stale index，然后从有效 raw paths 重新评分。

验证 raw paths 缺失时，可以删除对应患者的 `raw_paths/`、`scored_paths/` 和 `topk_candidates/` 文件；读取时会懒删除 stale index，然后从 Neo4j 重新 build raw paths，再评分并生成 topK candidates。

另有一套 direct path SQLite 缓存用于非患者 direct entity path 查询，核心表在 `src/similar_user/data_access/direct_path_cache_store.py` 中，包括 `direct_paths`、`source_nodes`、`taskset_nodes`、`patient_nodes` 和 `direct_path_sync_state`。这套表服务于 direct path 本身的离线同步，和上面的 `user_cache_entries` 用户中心 pipeline 缓存索引是两套机制。

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
  patient_path:
    window_days: 14  # 患者开头 path 检索窗口；CLI 不再传 --window-days
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

`predict_training_tasks.py` 支持 `--dry-run`（跳过 LLM，仅验证链路）和 `--include-prompt`（在 full 输出中包含生成的 prompt）。患者 path、scored path 和 topK candidates 会按配置自动读取或补算。

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

`evaluate_predict_training_tasks.py` 评估的是 `base_date` 当天真实训练任务与预测任务集合的命中情况。不传 `--patient-id` 时，脚本会在 `--patient-list-dir` 下查找或生成 `base_date` 当天有训练记录的患者列表；`--patient-id` 可用于只评估单个患者，`--limit` 可用于小样本冒烟。

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
  use_llm: true
  limit: 10

baseline_overrides:
  query.patient_path.window_days: 14
  query.training_task_prediction.task_top_k: 7
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

`base.evaluation_script` 控制每组实验调用哪个评估入口：

| 取值 | 调用脚本 | 适用场景 |
| --- | --- | --- |
| `evaluate_predict_training_tasks` 或不填 | `scripts/evaluate_predict_training_tasks.py` | 已存在患者 ID 的 patient path 评估 |
| `direct_entity_profiles` | `scripts/evaluate_direct_entity_profiles.py --prediction-mode direct_entity` | 非患者 direct entity profile 评估 |
| `unified_prediction` | `scripts/evaluate_direct_entity_profiles.py --prediction-mode unified` | 先判断患者是否存在，再自动路由的统一评估 |

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

`run_evaluation_grid.py` 默认会在完成排行榜后回写 `promoted_baseline_overrides` 和 `promoted_candidate_overrides`；如只想跑实验、不改实验 YAML，可使用：

```bash
python scripts/run_evaluation_grid.py \
  --experiment-config config/experiments/evaluation_grid_coarse_10_users.yaml \
  --no-write-promoted-baseline
```

默认回写时，脚本会把 leaderboard 第一名写入当前 `--experiment-config` 指定的 YAML 文件的 `promoted_baseline_overrides`，并写入若干 `promoted_candidate_overrides`，但不会修改正在生效的 `baseline_overrides`。如果文件中已经存在推荐块，旧块会被注释保留，新块写在后面。确认后可人工将 `promoted_baseline_overrides.overrides` 提升到 `baseline_overrides`。

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
