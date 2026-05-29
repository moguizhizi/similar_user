# Cypher Query Directory

本目录维护业务查询使用的 Cypher 语句。需要查某条语句时，优先看“按场景查”；需要确认完整归属时，再看“按文件查”。

## 按场景查

### 患者入口查询

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 查询全库患者 ID | `PATIENT_IDS_QUERY` | `patients.py` | 无 | `patient_id` |
| 判断指定 Patient 节点是否存在 | `PATIENT_EXISTS_QUERY` | `patients.py` | `patient_id` | `exists` |
| 查询指定日期有训练记录的患者 ID | `PATIENT_IDS_WITH_TRAINING_ON_DATE_QUERY` | `patients.py` | `base_date` | `patient_id` |
| 查询指定日期有训练记录的患者 ID，并在查询阶段限制数量 | `PATIENT_IDS_WITH_TRAINING_ON_DATE_LIMIT_QUERY` | `patients.py` | `base_date`, `limit` | `patient_id` |
| 查询可作为 source patient 的二级脑能力患者 ID | `SOURCE_PATIENT_IDS_WITH_SECONDARY_ABILITY_SCORES_QUERY` | `patients.py` | 无 | `patient_id` |

### 患者训练历史

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 查询患者从某日期开始的训练日期与游戏集合 | `PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY` | `patient_training_history.py` | `patient_id`, `start_date` | `trainingDate`, `games` |
| 查询患者训练日期的有序列表 | `PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY` | `patient_training_history.py` | `patient_id` | `orderedDatesa` |
| 查询患者带总分的训练时间点 | `PATIENT_TOTAL_SCORE_TIMEPOINTS_QUERY` | `patient_training_history.py` | `patient_id` | `instance_set_id`, `training_date`, `total_score` |
| 查询患者指定训练日期的总分 | `PATIENT_TOTAL_SCORE_BY_DATE_QUERY` | `patient_training_history.py` | `patient_id`, `training_date` | `instance_set_id`, `training_date`, `total_score` |
| 查询患者训练任务历史明细 | `PATIENT_TRAINING_TASK_HISTORY_QUERY` | `patient_training_history.py` | `patient_id` | `trainingDate`, `s`, `i`, `g` |
| 查询患者左闭右开日期窗口内的游戏历史 | `PATIENT_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY` | `patient_training_history.py` | `patient_id`, `start_date`, `end_date` | `trainingDate`, `g` |
| 查询患者左闭右开日期窗口内的专属任务游戏历史 | `PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY` | `patient_training_history.py` | `patient_id`, `start_date`, `end_date` | `trainingDate`, `g` |

### 患者游戏集合

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 查询全库训练记录中出现过的去重游戏 | `DISTINCT_TRAINING_GAMES_QUERY` | `patient_game_queries.py` | 无 | `g` |
| 查询患者早于 end_date 的去重游戏 | `PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY` | `patient_game_queries.py` | `patient_id`, `end_date` | `g` |
| 查询患者从某日期开始的去重游戏 | `PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY` | `patient_game_queries.py` | `patient_id`, `start_date` | `g` |
| 查询患者左闭右开日期区间内的去重游戏 | `PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY` | `patient_game_queries.py` | `patient_id`, `start_date`, `end_date` | `g` |
| 查询患者早于 end_date 的游戏记录（不去重） | `PATIENT_GAMES_BY_END_DATE_QUERY` | `patient_game_queries.py` | `patient_id`, `end_date` | `g` |
| 查询患者从某日期开始的游戏记录（不去重） | `PATIENT_GAMES_BY_START_DATE_QUERY` | `patient_game_queries.py` | `patient_id`, `start_date` | `g` |
| 查询患者左闭右开日期区间内的游戏记录（不去重） | `PATIENT_GAMES_BY_DATE_RANGE_QUERY` | `patient_game_queries.py` | `patient_id`, `start_date`, `end_date` | `g` |

### 患者实体集合

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 查询患者在 base_date 当天或之前最近有效日期的画像实体 | `PATIENT_PROFILE_ENTITIES_BY_EFFECTIVE_DATE_QUERY` | `patient_entity_queries.py` | `patient_id`, `base_date` | `effective_date`, `diseases`, `symptoms`, `unknowns` |
| 查询患者用于 direct entity path 评分的最近画像、校准年龄和实体 id 列表 | `PATIENT_DIRECT_ENTITY_SCORING_PROFILE_QUERY` | `patient_entity_queries.py` | `patient_id`, `base_date` | `patient_id`, `effective_date`, `gender`, `education`, `profile_age`, `age_at_base_date`, `disease_ids`, `symptom_ids`, `unknown_ids` |
| 按患者最近画像实体、性别、执行学历和基于 `base_date` 校准后的执行年龄范围查询专属任务相关游戏 | `PATIENT_PROFILE_GENDER_EDUCATION_AGE_EXCLUSIVE_TASK_GAME_QUERY` | `patient_entity_queries.py` | `patient_id`, `base_date`, `age_window` | `g`, `profile_age`, `age_at_base_date`, `profile_gender`, `profile_education`, `support_sources`, `support_count` |
| 按患者最近画像实体、性别、执行学历、基于 `base_date` 校准后的执行年龄范围和候选训练日期窗口查询专属任务相关游戏 | `PATIENT_PROFILE_GENDER_EDUCATION_AGE_WINDOWED_EXCLUSIVE_TASK_GAME_QUERY` | `patient_entity_queries.py` | `patient_id`, `base_date`, `age_window`, `profile_candidate_training_window_days` | `g`, `profile_age`, `age_at_base_date`, `profile_gender`, `profile_education`, `support_sources`, `support_count` |
| 查询患者从某日期开始的去重任务实例 | `PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY` | `patient_entity_queries.py` | `patient_id`, `start_date` | `i1` |
| 查询患者早于 end_date 的去重任务实例 | `PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY` | `patient_entity_queries.py` | `patient_id`, `end_date` | `i1` |
| 查询患者左闭右开日期区间内的去重任务实例 | `PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY` | `patient_entity_queries.py` | `patient_id`, `start_date`, `end_date` | `i1` |
| 查询患者左闭右开日期区间内的去重症状 | `PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY` | `patient_entity_queries.py` | `patient_id`, `start_date`, `end_date` | `sym` |
| 查询患者左闭右开日期区间内的去重疾病 | `PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY` | `patient_entity_queries.py` | `patient_id`, `start_date`, `end_date` | `dis` |
| 查询患者左闭右开日期区间内的去重 unknown 节点 | `PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY` | `patient_entity_queries.py` | `patient_id`, `start_date`, `end_date` | `un` |

### Direct Source Path 元数据

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 查询所有疾病 direct path source 及最新训练日期 | `DISEASE_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY` | `pattern_paths.py` | 无 | `source_id`, `source_name`, `path_count`, `latest_training_date` |
| 查询所有症状 direct path source 及最新训练日期 | `SYMPTOM_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY` | `pattern_paths.py` | 无 | `source_id`, `source_name`, `path_count`, `latest_training_date` |
| 查询所有 unknown direct path source 及最新训练日期 | `UNKNOWN_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY` | `pattern_paths.py` | 无 | `source_id`, `source_name`, `path_count`, `latest_training_date` |
| 查询单个疾病 direct path 最新训练日期 | `DISEASE_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY` | `pattern_paths.py` | `source_id` | `latest_training_date` |
| 查询单个症状 direct path 最新训练日期 | `SYMPTOM_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY` | `pattern_paths.py` | `source_id` | `latest_training_date` |
| 查询单个 unknown direct path 最新训练日期 | `UNKNOWN_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY` | `pattern_paths.py` | `source_id` | `latest_training_date` |

### 兜底任务推荐

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 按年龄、性别、学历和日期查询兜底专属训练任务 | `PROFILE_MATCHED_EXCLUSIVE_TASKS_QUERY` | `fallback_task_queries.py` | `base_date`, `age`, `min_age`, `max_age`, `gender`, `education`, `limit` | `g`, `support_count`, `patient_count`, `latest_training_date` |
| 按日期查询全局热门专属训练任务 | `GLOBAL_POPULAR_EXCLUSIVE_TASKS_QUERY` | `fallback_task_queries.py` | `base_date`, `limit` | `g`, `support_count`, `patient_count`, `latest_training_date` |

### Direct Entity 名称解析

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 按输入名称解析 Disease/Symptom/Unknown 实体 | `DIRECT_ENTITY_NAME_RESOLUTION_QUERY` | `direct_entity_resolution.py` | `entity_name` | `entity_type`, `entity_id`, `entity_name` |
| 列出 Disease/Symptom/Unknown 的标准名和别名 | `DIRECT_ENTITY_ALIAS_INDEX_QUERY` | `direct_entity_resolution.py` | 无 | `entity_type`, `entity_id`, `entity_name`, `alias_label` |

### 两个患者的集合比较

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 早于 end_date 比较游戏集合 | `PATIENT_GAME_SET_COMPARISON_BY_END_DATE_QUERY` | `patient_comparison_queries.py` | `primary_patient_id`, `comparison_patient_id`, `end_date` | `games1`, `games2` |
| 从某日期开始比较游戏集合 | `PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY` | `patient_comparison_queries.py` | `primary_patient_id`, `comparison_patient_id`, `start_date` | `games1`, `games2` |
| 在左闭右开日期区间内比较游戏集合 | `PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY` | `patient_comparison_queries.py` | `primary_patient_id`, `comparison_patient_id`, `start_date`, `end_date` | `games1`, `games2` |
| 早于 end_date 比较症状集合 | `PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY` | `patient_comparison_queries.py` | `primary_patient_id`, `comparison_patient_id`, `end_date` | `symptoms1`, `symptoms2` |
| 早于 end_date 比较疾病集合 | `PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY` | `patient_comparison_queries.py` | `primary_patient_id`, `comparison_patient_id`, `end_date` | `diseases1`, `diseases2` |
| 早于 end_date 比较 unknown 集合 | `PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY` | `patient_comparison_queries.py` | `primary_patient_id`, `comparison_patient_id`, `end_date` | `unknowns1`, `unknowns2` |

### 候选用户评分

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 查询两个患者共同游戏上的常模分序列 | `PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY` | `patient_score_queries.py` | `primary_patient_id`, `comparison_patient_id`, `end_date` | `game`, `scores_p1`, `scores_p2` |
| 查询患者左闭右开病程窗口内有二级脑能力值的 TaskInstanceSet | `PATIENT_SECONDARY_ABILITY_SCORES_BY_DISEASE_COURSE_WINDOW_QUERY` | `patient_comparison_queries.py` | `patient_id`, `base_date`, `disease_course_window_days` | `effective_ability_date`, `instance_set_id`, `training_date`, `secondary_ability_scores` |
| 查询患者左闭右开病程窗口内有总分的 TaskInstanceSet | `PATIENT_TOTAL_SCORES_BY_DISEASE_COURSE_WINDOW_QUERY` | `patient_comparison_queries.py` | `patient_id`, `base_date`, `disease_course_window_days` | `effective_total_score_date`, `instance_set_id`, `training_date`, `total_score` |

### 实体扩展查询

这类查询用于从一个起点实体扩展到相关图谱上下文，不注册为 `PathPattern`。结构化归属见 `graph_query_registry.py`。

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 从疾病扩展到相关游戏，每个游戏随机保留一条路径 | `DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY` | `entity_expansions.py` | `disease_id` | `row` |
| 从疾病扩展到专属任务相关游戏，每个游戏随机保留一条路径 | `DISEASE_TASKSET_EXCLUSIVE_TASK_GAME_SAMPLED_PER_GAME_QUERY` | `entity_expansions.py` | `disease_id` | `row` |
| 按疾病、执行学历和执行年龄范围查询专属任务相关游戏 | `DISEASE_EDUCATION_AGE_EXCLUSIVE_TASK_GAME_QUERY` | `entity_expansions.py` | `disease_id`, `education`, `min_age`, `max_age` | `g`, `support_count`, `taskset_count`, `task_instance_count` |
| 从症状扩展到相关游戏，每个游戏随机保留一条路径 | `SYMPTOM_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY` | `entity_expansions.py` | `symptom_id` | `row` |
| 从症状扩展到专属任务相关游戏，每个游戏随机保留一条路径 | `SYMPTOM_TASKSET_EXCLUSIVE_TASK_GAME_SAMPLED_PER_GAME_QUERY` | `entity_expansions.py` | `symptom_id` | `row` |
| 按症状、执行学历和执行年龄范围查询专属任务相关游戏 | `SYMPTOM_EDUCATION_AGE_EXCLUSIVE_TASK_GAME_QUERY` | `entity_expansions.py` | `symptom_id`, `education`, `min_age`, `max_age` | `g`, `support_count`, `taskset_count`, `task_instance_count` |
| 从未知节点扩展到相关游戏，每个游戏随机保留一条路径 | `UNKNOWN_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY` | `entity_expansions.py` | `unknown_id` | `row` |
| 从未知节点扩展到专属任务相关游戏，每个游戏随机保留一条路径 | `UNKNOWN_TASKSET_EXCLUSIVE_TASK_GAME_SAMPLED_PER_GAME_QUERY` | `entity_expansions.py` | `unknown_id` | `row` |
| 按未知节点、执行学历和执行年龄范围查询专属任务相关游戏 | `UNKNOWN_EDUCATION_AGE_EXCLUSIVE_TASK_GAME_QUERY` | `entity_expansions.py` | `unknown_id`, `education`, `min_age`, `max_age` | `g`, `support_count`, `taskset_count`, `task_instance_count` |

### 固定模式 path 检索

固定模式为：

```text
Patient -- TaskInstanceSet -- TaskInstance -- Game -- TaskInstance -- TaskInstanceSet -- Patient
Patient -- TaskInstanceSet -- Disease -- TaskInstanceSet -- Patient
Patient -- TaskInstanceSet -- Symptom -- TaskInstanceSet -- Patient
Patient -- TaskInstanceSet -- Unknown -- TaskInstanceSet -- Patient
Disease -- TaskInstanceSet -- Patient
```

`training_order_source_window` 系列 path 和统计查询会额外要求两侧 `TaskInstanceSet` 的 `总分` 均非空；`date_window` 系列不加这个约束。`*_dual_window` family 保留 `training_order_source_window` 的时间顺序约束，并额外要求 `s1` 和 `s2` 的训练日期都落在同一个左闭右开窗口 `[start_date, end_date)` 中。

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 仅要求两侧训练日期非空，随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `patient_id`, `per_g`, `limit` | `row` |
| 按 s1 从某日期开始随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| 按 s1 早于 end_date 随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| 按 s1 左闭右开日期区间随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `patient_id`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 从某日期开始随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 早于 end_date 随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 左闭右开日期区间随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按游戏局部采样随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_LOCAL_SAMPLING_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序和年龄接近随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_AGE_ONLY_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近和学历一致随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_AGE_EDUCATION_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近和完成状态随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_LAYER1_AGE_COMPLETION_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近、完成状态和学历一致随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_LAYER2_EDUCATION_EXACT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近、完成状态、学历一致、活跃和任务类型一致随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_LAYER3_ACTIVITY_TASK_TYPE_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并要求 s1/s2 都在窗口内随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、局部采样，并要求 s1/s2 都在窗口内随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_LOCAL_SAMPLING_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近，并要求 s1/s2 都在窗口内随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_AGE_ONLY_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近和学历一致，并要求 s1/s2 都在窗口内随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_AGE_EDUCATION_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近、完成状态，并要求 s1/s2 都在窗口内随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_LAYER1_AGE_COMPLETION_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近、完成状态、学历一致，并要求 s1/s2 都在窗口内随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_LAYER2_EDUCATION_EXACT_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近、完成状态、学历一致、活跃和任务类型一致，并要求 s1/s2 都在窗口内随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_TRAINING_ORDER_LAYER3_ACTIVITY_TASK_TYPE_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 仅要求两侧训练日期非空，随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `patient_id`, `per_g`, `limit` | `row` |
| 按 s1 从某日期开始随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| 按 s1 早于 end_date 随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| 按 s1 左闭右开日期区间随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `patient_id`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 从某日期开始随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 早于 end_date 随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 左闭右开日期区间随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序和局部采样随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_LOCAL_SAMPLING_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序和年龄接近随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_AGE_ONLY_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近和学历一致随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_AGE_EDUCATION_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并要求 s1/s2 都在窗口内随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、局部采样，并要求 s1/s2 都在窗口内随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_LOCAL_SAMPLING_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近，并要求 s1/s2 都在窗口内随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_AGE_ONLY_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近和学历一致，并要求 s1/s2 都在窗口内随机抽取疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_AGE_EDUCATION_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 仅要求两侧训练日期非空，随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `patient_id`, `per_g`, `limit` | `row` |
| 按 s1 从某日期开始随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| 按 s1 早于 end_date 随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| 按 s1 左闭右开日期区间随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `patient_id`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 从某日期开始随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 早于 end_date 随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 左闭右开日期区间随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序和局部采样随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_LOCAL_SAMPLING_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序和年龄接近随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_AGE_ONLY_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近和学历一致随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_AGE_EDUCATION_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并要求 s1/s2 都在窗口内随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、局部采样，并要求 s1/s2 都在窗口内随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_LOCAL_SAMPLING_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近，并要求 s1/s2 都在窗口内随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_AGE_ONLY_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近和学历一致，并要求 s1/s2 都在窗口内随机抽取症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_AGE_EDUCATION_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 仅要求两侧训练日期非空，随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `patient_id`, `per_g`, `limit` | `row` |
| 按 s1 从某日期开始随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| 按 s1 早于 end_date 随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| 按 s1 左闭右开日期区间随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `patient_id`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 从某日期开始随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 早于 end_date 随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并按 s1 左闭右开日期区间随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序和局部采样随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_LOCAL_SAMPLING_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序和年龄接近随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_AGE_ONLY_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近和学历一致随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_AGE_EDUCATION_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序，并要求 s1/s2 都在窗口内随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、局部采样，并要求 s1/s2 都在窗口内随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_LOCAL_SAMPLING_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近，并要求 s1/s2 都在窗口内随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_AGE_ONLY_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 按训练日期顺序、年龄接近和学历一致，并要求 s1/s2 都在窗口内随机抽取未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_AGE_EDUCATION_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| 随机抽取疾病到患者路径，每个患者保留一条 | `DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `disease_id` | `row` |
| 按 s 从某日期开始随机抽取疾病到患者路径，每个患者保留一条 | `DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `disease_id`, `start_date` | `row` |
| 按 s 早于 end_date 随机抽取疾病到患者路径，每个患者保留一条 | `DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `disease_id`, `end_date` | `row` |
| 按 s 左闭右开日期区间随机抽取疾病到患者路径，每个患者保留一条 | `DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `disease_id`, `start_date`, `end_date` | `row` |
| 查询全部带训练日期的疾病到患者路径，用于 SQLite 缓存同步 | `DISEASE_TASKSET_PATIENT_CACHE_PATHS_QUERY` | `pattern_paths.py` | 无 | `row` |
| 按 s 从某日期开始查询疾病到患者路径，用于 SQLite 增量缓存同步 | `DISEASE_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY` | `pattern_paths.py` | `start_date` | `row` |
| 随机抽取症状到患者路径，每个患者保留一条 | `SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `symptom_id` | `row` |
| 按 s 从某日期开始随机抽取症状到患者路径，每个患者保留一条 | `SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `symptom_id`, `start_date` | `row` |
| 按 s 早于 end_date 随机抽取症状到患者路径，每个患者保留一条 | `SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `symptom_id`, `end_date` | `row` |
| 按 s 左闭右开日期区间随机抽取症状到患者路径，每个患者保留一条 | `SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `symptom_id`, `start_date`, `end_date` | `row` |
| 查询全部带训练日期的症状到患者路径，用于 SQLite 缓存同步 | `SYMPTOM_TASKSET_PATIENT_CACHE_PATHS_QUERY` | `pattern_paths.py` | 无 | `row` |
| 按 s 从某日期开始查询症状到患者路径，用于 SQLite 增量缓存同步 | `SYMPTOM_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY` | `pattern_paths.py` | `start_date` | `row` |
| 随机抽取未知到患者路径，每个患者保留一条 | `UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `unknown_id` | `row` |
| 按 s 从某日期开始随机抽取未知到患者路径，每个患者保留一条 | `UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `unknown_id`, `start_date` | `row` |
| 按 s 早于 end_date 随机抽取未知到患者路径，每个患者保留一条 | `UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `unknown_id`, `end_date` | `row` |
| 按 s 左闭右开日期区间随机抽取未知到患者路径，每个患者保留一条 | `UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | `pattern_paths.py` | `unknown_id`, `start_date`, `end_date` | `row` |
| 查询全部带训练日期的未知到患者路径，用于 SQLite 缓存同步 | `UNKNOWN_TASKSET_PATIENT_CACHE_PATHS_QUERY` | `pattern_paths.py` | 无 | `row` |
| 按 s 从某日期开始查询未知到患者路径，用于 SQLite 增量缓存同步 | `UNKNOWN_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY` | `pattern_paths.py` | `start_date` | `row` |

### 固定模式 path 统计

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 仅要求两侧训练日期非空，统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY` | `pattern_statistics.py` | `patient_id` | `totalPaths`, `gCount`, `p2Count` |
| 按 s1 从某日期开始统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date` | `totalPaths`, `gCount`, `p2Count` |
| 按 s1 早于 end_date 统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| 按 s1 左闭右开日期区间统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| 按训练日期顺序统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY` | `pattern_statistics.py` | `patient_id` | `totalPaths`, `gCount`, `p2Count` |
| 按训练日期顺序，并按 s1 早于 end_date 统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| 按训练日期顺序，并按 s1 从某日期开始统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date` | `totalPaths`, `gCount`, `p2Count` |
| 按训练日期顺序，并按 s1 左闭右开日期区间统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| 按训练日期顺序，并要求 s1/s2 都在窗口内统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_DUAL_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| 仅要求两侧训练日期非空，统计疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY` | `pattern_statistics.py` | `patient_id` | `totalPaths`, `disCount`, `p2Count` |
| 按 s1 从某日期开始统计疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date` | `totalPaths`, `disCount`, `p2Count` |
| 按 s1 早于 end_date 统计疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `end_date` | `totalPaths`, `disCount`, `p2Count` |
| 按 s1 左闭右开日期区间统计疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `disCount`, `p2Count` |
| 按训练日期顺序统计疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY` | `pattern_statistics.py` | `patient_id` | `totalPaths`, `disCount`, `p2Count` |
| 按训练日期顺序，并按 s1 从某日期开始统计疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date` | `totalPaths`, `disCount`, `p2Count` |
| 按训练日期顺序，并按 s1 早于 end_date 统计疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `end_date` | `totalPaths`, `disCount`, `p2Count` |
| 按训练日期顺序，并按 s1 左闭右开日期区间统计疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `disCount`, `p2Count` |
| 按训练日期顺序，并要求 s1/s2 都在窗口内统计疾病固定模式 path | `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_DUAL_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `disCount`, `p2Count` |
| 仅要求两侧训练日期非空，统计症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY` | `pattern_statistics.py` | `patient_id` | `totalPaths`, `symCount`, `p2Count` |
| 按 s1 从某日期开始统计症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date` | `totalPaths`, `symCount`, `p2Count` |
| 按 s1 早于 end_date 统计症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `end_date` | `totalPaths`, `symCount`, `p2Count` |
| 按 s1 左闭右开日期区间统计症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `symCount`, `p2Count` |
| 按训练日期顺序统计症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY` | `pattern_statistics.py` | `patient_id` | `totalPaths`, `symCount`, `p2Count` |
| 按训练日期顺序，并按 s1 从某日期开始统计症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date` | `totalPaths`, `symCount`, `p2Count` |
| 按训练日期顺序，并按 s1 早于 end_date 统计症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `end_date` | `totalPaths`, `symCount`, `p2Count` |
| 按训练日期顺序，并按 s1 左闭右开日期区间统计症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `symCount`, `p2Count` |
| 按训练日期顺序，并要求 s1/s2 都在窗口内统计症状固定模式 path | `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_DUAL_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `symCount`, `p2Count` |
| 仅要求两侧训练日期非空，统计未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY` | `pattern_statistics.py` | `patient_id` | `totalPaths`, `unCount`, `p2Count` |
| 按 s1 从某日期开始统计未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date` | `totalPaths`, `unCount`, `p2Count` |
| 按 s1 早于 end_date 统计未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `end_date` | `totalPaths`, `unCount`, `p2Count` |
| 按 s1 左闭右开日期区间统计未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `unCount`, `p2Count` |
| 按训练日期顺序统计未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY` | `pattern_statistics.py` | `patient_id` | `totalPaths`, `unCount`, `p2Count` |
| 按训练日期顺序，并按 s1 从某日期开始统计未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date` | `totalPaths`, `unCount`, `p2Count` |
| 按训练日期顺序，并按 s1 早于 end_date 统计未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `end_date` | `totalPaths`, `unCount`, `p2Count` |
| 按训练日期顺序，并按 s1 左闭右开日期区间统计未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `unCount`, `p2Count` |
| 按训练日期顺序，并要求 s1/s2 都在窗口内统计未知固定模式 path | `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_DUAL_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `unCount`, `p2Count` |

## 按文件查

### `patients.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PATIENT_IDS_QUERY` | 查询全库患者 ID | 无 | `patient_id` |
| `PATIENT_EXISTS_QUERY` | 判断指定 Patient 节点是否存在 | `patient_id` | `exists` |
| `PATIENT_IDS_WITH_TRAINING_ON_DATE_QUERY` | 查询指定日期有训练记录的患者 ID | `base_date` | `patient_id` |
| `PATIENT_IDS_WITH_TRAINING_ON_DATE_LIMIT_QUERY` | 查询指定日期有训练记录的患者 ID，并在查询阶段限制数量 | `base_date`, `limit` | `patient_id` |
| `SOURCE_PATIENT_IDS_WITH_SECONDARY_ABILITY_SCORES_QUERY` | 查询可作为 source patient 的二级脑能力患者 ID | 无 | `patient_id` |

### `patient_training_history.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY` | 查询患者从某日期开始的训练日期与游戏集合 | `patient_id`, `start_date` | `trainingDate`, `games` |
| `PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY` | 查询患者训练日期的有序列表 | `patient_id` | `orderedDatesa` |
| `PATIENT_TOTAL_SCORE_TIMEPOINTS_QUERY` | 查询患者带总分的训练时间点 | `patient_id` | `instance_set_id`, `training_date`, `total_score` |
| `PATIENT_TOTAL_SCORE_BY_DATE_QUERY` | 查询患者指定训练日期的总分 | `patient_id`, `training_date` | `instance_set_id`, `training_date`, `total_score` |
| `PATIENT_TRAINING_TASK_HISTORY_QUERY` | 查询患者训练任务历史明细 | `patient_id` | `trainingDate`, `s`, `i`, `g` |
| `PATIENT_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY` | 查询患者左闭右开日期窗口内的游戏历史 | `patient_id`, `start_date`, `end_date` | `trainingDate`, `g` |
| `PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY` | 查询患者左闭右开日期窗口内的专属任务游戏历史 | `patient_id`, `start_date`, `end_date` | `trainingDate`, `g` |

### `patient_game_queries.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `DISTINCT_TRAINING_GAMES_QUERY` | 查询全库训练记录中出现过的去重游戏 | 无 | `g` |
| `PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY` | 查询患者早于 end_date 的去重游戏 | `patient_id`, `end_date` | `g` |
| `PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY` | 查询患者从某日期开始的去重游戏 | `patient_id`, `start_date` | `g` |
| `PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的去重游戏 | `patient_id`, `start_date`, `end_date` | `g` |
| `PATIENT_GAMES_BY_END_DATE_QUERY` | 查询患者早于 end_date 的游戏记录（不去重） | `patient_id`, `end_date` | `g` |
| `PATIENT_GAMES_BY_START_DATE_QUERY` | 查询患者从某日期开始的游戏记录（不去重） | `patient_id`, `start_date` | `g` |
| `PATIENT_GAMES_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的游戏记录（不去重） | `patient_id`, `start_date`, `end_date` | `g` |

### `fallback_task_queries.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PROFILE_MATCHED_EXCLUSIVE_TASKS_QUERY` | 按年龄、性别、学历和日期查询兜底专属训练任务 | `base_date`, `age`, `min_age`, `max_age`, `gender`, `education`, `limit` | `g`, `support_count`, `patient_count`, `latest_training_date` |
| `GLOBAL_POPULAR_EXCLUSIVE_TASKS_QUERY` | 按日期查询全局热门专属训练任务 | `base_date`, `limit` | `g`, `support_count`, `patient_count`, `latest_training_date` |

### `direct_entity_resolution.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `DIRECT_ENTITY_NAME_RESOLUTION_QUERY` | 按输入名称解析 Disease/Symptom/Unknown 实体 | `entity_name` | `entity_type`, `entity_id`, `entity_name` |
| `DIRECT_ENTITY_ALIAS_INDEX_QUERY` | 列出 Disease/Symptom/Unknown 的标准名和别名 | 无 | `entity_type`, `entity_id`, `entity_name`, `alias_label` |

### `patient_entity_queries.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PATIENT_PROFILE_ENTITIES_BY_EFFECTIVE_DATE_QUERY` | 查询患者在 base_date 当天或之前最近有效日期的画像实体 | `patient_id`, `base_date` | `effective_date`, `diseases`, `symptoms`, `unknowns` |
| `PATIENT_DIRECT_ENTITY_SCORING_PROFILE_QUERY` | 查询患者用于 direct entity path 评分的最近画像、校准年龄和实体 id 列表 | `patient_id`, `base_date` | `patient_id`, `effective_date`, `gender`, `education`, `profile_age`, `age_at_base_date`, `disease_ids`, `symptom_ids`, `unknown_ids` |
| `PATIENT_PROFILE_GENDER_EDUCATION_AGE_EXCLUSIVE_TASK_GAME_QUERY` | 按患者最近画像实体、性别、执行学历和基于 `base_date` 校准后的执行年龄范围查询专属任务相关游戏 | `patient_id`, `base_date`, `age_window` | `g`, `profile_age`, `age_at_base_date`, `profile_gender`, `profile_education`, `support_sources`, `support_count` |
| `PATIENT_PROFILE_GENDER_EDUCATION_AGE_WINDOWED_EXCLUSIVE_TASK_GAME_QUERY` | 按患者最近画像实体、性别、执行学历、基于 `base_date` 校准后的执行年龄范围和候选训练日期窗口查询专属任务相关游戏 | `patient_id`, `base_date`, `age_window`, `profile_candidate_training_window_days` | `g`, `profile_age`, `age_at_base_date`, `profile_gender`, `profile_education`, `support_sources`, `support_count` |
| `PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY` | 查询患者从某日期开始的去重任务实例 | `patient_id`, `start_date` | `i1` |
| `PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY` | 查询患者早于 end_date 的去重任务实例 | `patient_id`, `end_date` | `i1` |
| `PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的去重任务实例 | `patient_id`, `start_date`, `end_date` | `i1` |
| `PATIENT_DISTINCT_SYMPTOMS_BY_START_DATE_QUERY` | 查询患者从某日期开始的去重症状 | `patient_id`, `start_date` | `sym` |
| `PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY` | 查询患者早于 end_date 的去重症状 | `patient_id`, `end_date` | `sym` |
| `PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的去重症状 | `patient_id`, `start_date`, `end_date` | `sym` |
| `PATIENT_DISTINCT_DISEASES_BY_START_DATE_QUERY` | 查询患者从某日期开始的去重疾病 | `patient_id`, `start_date` | `dis` |
| `PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY` | 查询患者早于 end_date 的去重疾病 | `patient_id`, `end_date` | `dis` |
| `PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的去重疾病 | `patient_id`, `start_date`, `end_date` | `dis` |
| `PATIENT_DISTINCT_UNKNOWNS_BY_START_DATE_QUERY` | 查询患者从某日期开始的去重 unknown 节点 | `patient_id`, `start_date` | `un` |
| `PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY` | 查询患者早于 end_date 的去重 unknown 节点 | `patient_id`, `end_date` | `un` |
| `PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的去重 unknown 节点 | `patient_id`, `start_date`, `end_date` | `un` |

### `pattern_paths.py` direct source metadata

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `DISEASE_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY` | 查询所有疾病 direct path source 及最新训练日期 | 无 | `source_id`, `source_name`, `path_count`, `latest_training_date` |
| `SYMPTOM_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY` | 查询所有症状 direct path source 及最新训练日期 | 无 | `source_id`, `source_name`, `path_count`, `latest_training_date` |
| `UNKNOWN_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY` | 查询所有 unknown direct path source 及最新训练日期 | 无 | `source_id`, `source_name`, `path_count`, `latest_training_date` |
| `DISEASE_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY` | 查询单个疾病 direct path 最新训练日期 | `source_id` | `latest_training_date` |
| `SYMPTOM_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY` | 查询单个症状 direct path 最新训练日期 | `source_id` | `latest_training_date` |
| `UNKNOWN_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY` | 查询单个 unknown direct path 最新训练日期 | `source_id` | `latest_training_date` |

### `patient_comparison_queries.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY` | 从某日期开始比较两个患者的游戏集合 | `primary_patient_id`, `comparison_patient_id`, `start_date` | `games1`, `games2` |
| `PATIENT_GAME_SET_COMPARISON_BY_END_DATE_QUERY` | 早于 end_date 比较两个患者的游戏集合 | `primary_patient_id`, `comparison_patient_id`, `end_date` | `games1`, `games2` |
| `PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY` | 在左闭右开日期区间内比较两个患者的游戏集合 | `primary_patient_id`, `comparison_patient_id`, `start_date`, `end_date` | `games1`, `games2` |
| `PATIENT_SYMPTOM_SET_COMPARISON_BY_START_DATE_QUERY` | 从某日期开始比较两个患者的症状集合 | `primary_patient_id`, `comparison_patient_id`, `start_date` | `symptoms1`, `symptoms2` |
| `PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY` | 早于 end_date 比较两个患者的症状集合 | `primary_patient_id`, `comparison_patient_id`, `end_date` | `symptoms1`, `symptoms2` |
| `PATIENT_SYMPTOM_SET_COMPARISON_BY_DATE_RANGE_QUERY` | 在左闭右开日期区间内比较两个患者的症状集合 | `primary_patient_id`, `comparison_patient_id`, `start_date`, `end_date` | `symptoms1`, `symptoms2` |
| `PATIENT_DISEASE_SET_COMPARISON_BY_START_DATE_QUERY` | 从某日期开始比较两个患者的疾病集合 | `primary_patient_id`, `comparison_patient_id`, `start_date` | `diseases1`, `diseases2` |
| `PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY` | 早于 end_date 比较两个患者的疾病集合 | `primary_patient_id`, `comparison_patient_id`, `end_date` | `diseases1`, `diseases2` |
| `PATIENT_DISEASE_SET_COMPARISON_BY_DATE_RANGE_QUERY` | 在左闭右开日期区间内比较两个患者的疾病集合 | `primary_patient_id`, `comparison_patient_id`, `start_date`, `end_date` | `diseases1`, `diseases2` |
| `PATIENT_UNKNOWN_SET_COMPARISON_BY_START_DATE_QUERY` | 从某日期开始比较两个患者的 unknown 集合 | `primary_patient_id`, `comparison_patient_id`, `start_date` | `unknowns1`, `unknowns2` |
| `PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY` | 早于 end_date 比较两个患者的 unknown 集合 | `primary_patient_id`, `comparison_patient_id`, `end_date` | `unknowns1`, `unknowns2` |
| `PATIENT_UNKNOWN_SET_COMPARISON_BY_DATE_RANGE_QUERY` | 在左闭右开日期区间内比较两个患者的 unknown 集合 | `primary_patient_id`, `comparison_patient_id`, `start_date`, `end_date` | `unknowns1`, `unknowns2` |
| `PATIENT_SECONDARY_ABILITY_SCORES_BY_DISEASE_COURSE_WINDOW_QUERY` | 查询患者左闭右开病程窗口内有二级脑能力值的 TaskInstanceSet | `patient_id`, `base_date`, `disease_course_window_days` | `effective_ability_date`, `instance_set_id`, `training_date`, `secondary_ability_scores` |
| `PATIENT_TOTAL_SCORES_BY_DISEASE_COURSE_WINDOW_QUERY` | 查询患者左闭右开病程窗口内有总分的 TaskInstanceSet | `patient_id`, `base_date`, `disease_course_window_days` | `effective_total_score_date`, `instance_set_id`, `training_date`, `total_score` |

### `patient_score_queries.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY` | 查询两个患者共同游戏上的常模分序列 | `primary_patient_id`, `comparison_patient_id`, `end_date` | `game`, `scores_p1`, `scores_p2` |

### `entity_expansions.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY` | 从疾病扩展到相关游戏，每个游戏随机保留一条路径 | `disease_id` | `row` |
| `SYMPTOM_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY` | 从症状扩展到相关游戏，每个游戏随机保留一条路径 | `symptom_id` | `row` |
| `UNKNOWN_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY` | 从未知节点扩展到相关游戏，每个游戏随机保留一条路径 | `unknown_id` | `row` |

### `pattern_paths.py`

`TRAINING_ORDER_*_DUAL_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` 系列与上方 `training_order_source_window` 路径对应，额外要求 `s1`/`s2` 均在 `[start_date, end_date)` 内；完整按场景列表见“固定模式 path 查询”。

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY` | 仅要求两侧训练日期非空，随机抽取固定模式 path | `patient_id`, `per_g`, `limit` | `row` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 按 s1 从某日期开始随机抽取固定模式 path | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 按 s1 早于 end_date 随机抽取固定模式 path | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 按 s1 左闭右开日期区间随机抽取固定模式 path | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_QUERY` | 按训练日期顺序随机抽取固定模式 path | `patient_id`, `per_g`, `limit` | `row` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 从某日期开始随机抽取固定模式 path | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 早于 end_date 随机抽取固定模式 path | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 在左闭右开日期区间内随机抽取固定模式 path | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY` | 仅要求两侧训练日期非空，随机抽取疾病固定模式 path | `patient_id`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 按 s1 从某日期开始随机抽取疾病固定模式 path | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 按 s1 早于 end_date 随机抽取疾病固定模式 path | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 按 s1 左闭右开日期区间随机抽取疾病固定模式 path | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY` | 按训练日期顺序随机抽取疾病固定模式 path | `patient_id`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 按训练日期顺序，并按 s1 从某日期开始随机抽取疾病固定模式 path | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 按训练日期顺序，并按 s1 早于 end_date 随机抽取疾病固定模式 path | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 按训练日期顺序，并按 s1 左闭右开日期区间随机抽取疾病固定模式 path | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY` | 仅要求两侧训练日期非空，随机抽取症状固定模式 path | `patient_id`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 按 s1 从某日期开始随机抽取症状固定模式 path | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 按 s1 早于 end_date 随机抽取症状固定模式 path | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 按 s1 左闭右开日期区间随机抽取症状固定模式 path | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY` | 按训练日期顺序随机抽取症状固定模式 path | `patient_id`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 按训练日期顺序，并按 s1 从某日期开始随机抽取症状固定模式 path | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 按训练日期顺序，并按 s1 早于 end_date 随机抽取症状固定模式 path | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 按训练日期顺序，并按 s1 左闭右开日期区间随机抽取症状固定模式 path | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY` | 仅要求两侧训练日期非空，随机抽取未知固定模式 path | `patient_id`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 按 s1 从某日期开始随机抽取未知固定模式 path | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 按 s1 早于 end_date 随机抽取未知固定模式 path | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 按 s1 左闭右开日期区间随机抽取未知固定模式 path | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY` | 按训练日期顺序随机抽取未知固定模式 path | `patient_id`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 按训练日期顺序，并按 s1 从某日期开始随机抽取未知固定模式 path | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 按训练日期顺序，并按 s1 早于 end_date 随机抽取未知固定模式 path | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 按训练日期顺序，并按 s1 左闭右开日期区间随机抽取未知固定模式 path | `patient_id`, `start_date`, `end_date`, `per_g`, `limit` | `row` |
| `DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY` | 随机抽取疾病到患者路径，每个患者保留一条 | `disease_id` | `row` |
| `DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 按 s 从某日期开始随机抽取疾病到患者路径，每个患者保留一条 | `disease_id`, `start_date` | `row` |
| `DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 按 s 早于 end_date 随机抽取疾病到患者路径，每个患者保留一条 | `disease_id`, `end_date` | `row` |
| `DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 按 s 左闭右开日期区间随机抽取疾病到患者路径，每个患者保留一条 | `disease_id`, `start_date`, `end_date` | `row` |
| `SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY` | 随机抽取症状到患者路径，每个患者保留一条 | `symptom_id` | `row` |
| `SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 按 s 从某日期开始随机抽取症状到患者路径，每个患者保留一条 | `symptom_id`, `start_date` | `row` |
| `SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 按 s 早于 end_date 随机抽取症状到患者路径，每个患者保留一条 | `symptom_id`, `end_date` | `row` |
| `SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 按 s 左闭右开日期区间随机抽取症状到患者路径，每个患者保留一条 | `symptom_id`, `start_date`, `end_date` | `row` |
| `UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY` | 随机抽取未知到患者路径，每个患者保留一条 | `unknown_id` | `row` |
| `UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 按 s 从某日期开始随机抽取未知到患者路径，每个患者保留一条 | `unknown_id`, `start_date` | `row` |
| `UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 按 s 早于 end_date 随机抽取未知到患者路径，每个患者保留一条 | `unknown_id`, `end_date` | `row` |
| `UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY` | 按 s 左闭右开日期区间随机抽取未知到患者路径，每个患者保留一条 | `unknown_id`, `start_date`, `end_date` | `row` |

### `pattern_statistics.py`

`*_DUAL_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` 系列与上方 `training_order_source_window` 统计对应，额外要求 `s1`/`s2` 均在 `[start_date, end_date)` 内；完整按场景列表见“固定模式 path 统计”。

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY` | 仅要求两侧训练日期非空，统计固定模式 path | `patient_id` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY` | 按 s1 早于 end_date 统计固定模式 path | `patient_id`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY` | 按 s1 从某日期开始统计固定模式 path | `patient_id`, `start_date` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | 按 s1 左闭右开日期区间统计固定模式 path | `patient_id`, `start_date`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY` | 按训练日期顺序统计固定模式 path | `patient_id` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY` | 按训练日期顺序，并按 s1 早于 end_date 统计固定模式 path | `patient_id`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY` | 按训练日期顺序，并按 s1 从某日期开始统计固定模式 path | `patient_id`, `start_date` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | 按训练日期顺序，并按 s1 左闭右开日期区间统计固定模式 path | `patient_id`, `start_date`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY` | 仅要求两侧训练日期非空，统计疾病固定模式 path | `patient_id` | `totalPaths`, `disCount`, `p2Count` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY` | 按 s1 从某日期开始统计疾病固定模式 path | `patient_id`, `start_date` | `totalPaths`, `disCount`, `p2Count` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY` | 按 s1 早于 end_date 统计疾病固定模式 path | `patient_id`, `end_date` | `totalPaths`, `disCount`, `p2Count` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | 按 s1 左闭右开日期区间统计疾病固定模式 path | `patient_id`, `start_date`, `end_date` | `totalPaths`, `disCount`, `p2Count` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY` | 按训练日期顺序统计疾病固定模式 path | `patient_id` | `totalPaths`, `disCount`, `p2Count` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY` | 按训练日期顺序，并按 s1 从某日期开始统计疾病固定模式 path | `patient_id`, `start_date` | `totalPaths`, `disCount`, `p2Count` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY` | 按训练日期顺序，并按 s1 早于 end_date 统计疾病固定模式 path | `patient_id`, `end_date` | `totalPaths`, `disCount`, `p2Count` |
| `PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | 按训练日期顺序，并按 s1 左闭右开日期区间统计疾病固定模式 path | `patient_id`, `start_date`, `end_date` | `totalPaths`, `disCount`, `p2Count` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY` | 仅要求两侧训练日期非空，统计症状固定模式 path | `patient_id` | `totalPaths`, `symCount`, `p2Count` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY` | 按 s1 从某日期开始统计症状固定模式 path | `patient_id`, `start_date` | `totalPaths`, `symCount`, `p2Count` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY` | 按 s1 早于 end_date 统计症状固定模式 path | `patient_id`, `end_date` | `totalPaths`, `symCount`, `p2Count` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | 按 s1 左闭右开日期区间统计症状固定模式 path | `patient_id`, `start_date`, `end_date` | `totalPaths`, `symCount`, `p2Count` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY` | 按训练日期顺序统计症状固定模式 path | `patient_id` | `totalPaths`, `symCount`, `p2Count` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY` | 按训练日期顺序，并按 s1 从某日期开始统计症状固定模式 path | `patient_id`, `start_date` | `totalPaths`, `symCount`, `p2Count` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY` | 按训练日期顺序，并按 s1 早于 end_date 统计症状固定模式 path | `patient_id`, `end_date` | `totalPaths`, `symCount`, `p2Count` |
| `PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | 按训练日期顺序，并按 s1 左闭右开日期区间统计症状固定模式 path | `patient_id`, `start_date`, `end_date` | `totalPaths`, `symCount`, `p2Count` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY` | 仅要求两侧训练日期非空，统计未知固定模式 path | `patient_id` | `totalPaths`, `unCount`, `p2Count` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY` | 按 s1 从某日期开始统计未知固定模式 path | `patient_id`, `start_date` | `totalPaths`, `unCount`, `p2Count` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY` | 按 s1 早于 end_date 统计未知固定模式 path | `patient_id`, `end_date` | `totalPaths`, `unCount`, `p2Count` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | 按 s1 左闭右开日期区间统计未知固定模式 path | `patient_id`, `start_date`, `end_date` | `totalPaths`, `unCount`, `p2Count` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY` | 按训练日期顺序统计未知固定模式 path | `patient_id` | `totalPaths`, `unCount`, `p2Count` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY` | 按训练日期顺序，并按 s1 从某日期开始统计未知固定模式 path | `patient_id`, `start_date` | `totalPaths`, `unCount`, `p2Count` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY` | 按训练日期顺序，并按 s1 早于 end_date 统计未知固定模式 path | `patient_id`, `end_date` | `totalPaths`, `unCount`, `p2Count` |
| `PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | 按训练日期顺序，并按 s1 左闭右开日期区间统计未知固定模式 path | `patient_id`, `start_date`, `end_date` | `totalPaths`, `unCount`, `p2Count` |
