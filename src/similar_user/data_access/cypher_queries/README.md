# Cypher Query Directory

本目录维护业务查询使用的 Cypher 语句。需要查某条语句时，优先看“按场景查”；需要确认完整归属时，再看“按文件查”。

## 按场景查

### 训练日期与游戏

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 查询患者从某日期开始的训练日期与游戏集合 | `PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY` | `patient_dates.py` | `patient_id`, `start_date` | `trainingDate`, `games` |
| 查询患者训练任务历史明细 | `PATIENT_TRAINING_TASK_HISTORY_QUERY` | `patient_dates.py` | `patient_id` | `trainingDate`, `s`, `i`, `g` |
| 查询患者左闭右开日期窗口内的游戏历史 | `PATIENT_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY` | `patient_dates.py` | `patient_id`, `start_date`, `end_date` | `trainingDate`, `g` |
| 查询患者早于 end_date 的去重游戏 | `PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY` | `patient_dates.py` | `patient_id`, `end_date` | `g` |
| 查询患者从某日期开始的去重游戏 | `PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY` | `patient_dates.py` | `patient_id`, `start_date` | `g` |
| 查询患者左闭右开日期区间内的去重游戏 | `PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY` | `patient_dates.py` | `patient_id`, `start_date`, `end_date` | `g` |
| 查询患者早于 end_date 的游戏记录（不去重） | `PATIENT_GAMES_BY_END_DATE_QUERY` | `patient_dates.py` | `patient_id`, `end_date` | `g` |
| 查询患者从某日期开始的游戏记录（不去重） | `PATIENT_GAMES_BY_START_DATE_QUERY` | `patient_dates.py` | `patient_id`, `start_date` | `g` |
| 查询患者左闭右开日期区间内的游戏记录（不去重） | `PATIENT_GAMES_BY_DATE_RANGE_QUERY` | `patient_dates.py` | `patient_id`, `start_date`, `end_date` | `g` |

### 两个患者的集合比较

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 早于 end_date 比较游戏集合 | `PATIENT_GAME_SET_COMPARISON_BY_END_DATE_QUERY` | `patient_dates.py` | `primary_patient_id`, `comparison_patient_id`, `end_date` | `games1`, `games2` |
| 从某日期开始比较游戏集合 | `PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY` | `patient_dates.py` | `primary_patient_id`, `comparison_patient_id`, `start_date` | `games1`, `games2` |
| 在左闭右开日期区间内比较游戏集合 | `PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY` | `patient_dates.py` | `primary_patient_id`, `comparison_patient_id`, `start_date`, `end_date` | `games1`, `games2` |
| 早于 end_date 比较症状集合 | `PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY` | `patient_dates.py` | `primary_patient_id`, `comparison_patient_id`, `end_date` | `symptoms1`, `symptoms2` |
| 早于 end_date 比较疾病集合 | `PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY` | `patient_dates.py` | `primary_patient_id`, `comparison_patient_id`, `end_date` | `diseases1`, `diseases2` |
| 早于 end_date 比较 unknown 集合 | `PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY` | `patient_dates.py` | `primary_patient_id`, `comparison_patient_id`, `end_date` | `unknowns1`, `unknowns2` |

### 候选用户评分

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 查询两个患者共同游戏上的常模分序列 | `PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY` | `patient_dates.py` | `primary_patient_id`, `comparison_patient_id`, `end_date` | `game`, `scores_p1`, `scores_p2` |

### 固定模式 path 检索

固定模式为：

```text
Patient -- TaskInstanceSet -- TaskInstance -- Game -- TaskInstance -- TaskInstanceSet -- Patient
```

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 不限日期随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `patient_id`, `per_g`, `limit` | `row` |
| 从某日期开始随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| 早于 end_date 随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY` | `pattern_paths.py` | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| 仅按早于 end_date 约束随机抽取固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_END_DATE_RANDOMIZED_PATH_QUERY` | `pattern_paths.py` | `patient_id`, `end_date`, `per_g`, `limit` | `row` |

### 固定模式 path 统计

| 场景 | Query | 文件 | 主要参数 | 返回 |
|---|---|---|---|---|
| 不限日期统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY` | `pattern_statistics.py` | `patient_id` | `totalPaths`, `gCount`, `p2Count` |
| 按训练日期约束统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY` | `pattern_statistics.py` | `patient_id` | `totalPaths`, `gCount`, `p2Count` |
| 早于 end_date 统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| 从某日期开始统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date` | `totalPaths`, `gCount`, `p2Count` |
| 在左闭右开日期区间内统计固定模式 path | `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | `pattern_statistics.py` | `patient_id`, `start_date`, `end_date` | `totalPaths`, `gCount`, `p2Count` |

## 按文件查

### `patient_dates.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY` | 查询患者从某日期开始的训练日期与游戏集合 | `patient_id`, `start_date` | `trainingDate`, `games` |
| `PATIENT_TRAINING_TASK_HISTORY_QUERY` | 查询患者训练任务历史明细 | `patient_id` | `trainingDate`, `s`, `i`, `g` |
| `PATIENT_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY` | 查询患者左闭右开日期窗口内的游戏历史 | `patient_id`, `start_date`, `end_date` | `trainingDate`, `g` |
| `PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY` | 查询患者早于 end_date 的去重游戏 | `patient_id`, `end_date` | `g` |
| `PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY` | 查询患者从某日期开始的去重游戏 | `patient_id`, `start_date` | `g` |
| `PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的去重游戏 | `patient_id`, `start_date`, `end_date` | `g` |
| `PATIENT_GAMES_BY_END_DATE_QUERY` | 查询患者早于 end_date 的游戏记录（不去重） | `patient_id`, `end_date` | `g` |
| `PATIENT_GAMES_BY_START_DATE_QUERY` | 查询患者从某日期开始的游戏记录（不去重） | `patient_id`, `start_date` | `g` |
| `PATIENT_GAMES_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的游戏记录（不去重） | `patient_id`, `start_date`, `end_date` | `g` |
| `PATIENT_GAME_SET_COMPARISON_BY_END_DATE_QUERY` | 早于 end_date 比较两个患者的游戏集合 | `primary_patient_id`, `comparison_patient_id`, `end_date` | `games1`, `games2` |
| `PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY` | 从某日期开始比较两个患者的游戏集合 | `primary_patient_id`, `comparison_patient_id`, `start_date` | `games1`, `games2` |
| `PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY` | 在左闭右开日期区间内比较两个患者的游戏集合 | `primary_patient_id`, `comparison_patient_id`, `start_date`, `end_date` | `games1`, `games2` |
| `PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY` | 查询两个患者共同游戏上的常模分序列 | `primary_patient_id`, `comparison_patient_id`, `end_date` | `game`, `scores_p1`, `scores_p2` |
| `PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY` | 查询患者从某日期开始的去重任务实例 | `patient_id`, `start_date` | `i1` |
| `PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY` | 查询患者早于 end_date 的去重任务实例 | `patient_id`, `end_date` | `i1` |
| `PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的去重任务实例 | `patient_id`, `start_date`, `end_date` | `i1` |
| `PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY` | 查询患者早于 end_date 的去重症状 | `patient_id`, `end_date` | `sym` |
| `PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY` | 早于 end_date 比较两个患者的症状集合 | `primary_patient_id`, `comparison_patient_id`, `end_date` | `symptoms1`, `symptoms2` |
| `PATIENT_DISTINCT_SYMPTOMS_BY_START_DATE_QUERY` | 查询患者从某日期开始的去重症状 | `patient_id`, `start_date` | `sym` |
| `PATIENT_SYMPTOM_SET_COMPARISON_BY_START_DATE_QUERY` | 从某日期开始比较两个患者的症状集合 | `primary_patient_id`, `comparison_patient_id`, `start_date` | `symptoms1`, `symptoms2` |
| `PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的去重症状 | `patient_id`, `start_date`, `end_date` | `sym` |
| `PATIENT_SYMPTOM_SET_COMPARISON_BY_DATE_RANGE_QUERY` | 在左闭右开日期区间内比较两个患者的症状集合 | `primary_patient_id`, `comparison_patient_id`, `start_date`, `end_date` | `symptoms1`, `symptoms2` |
| `PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY` | 查询患者早于 end_date 的去重疾病 | `patient_id`, `end_date` | `d` |
| `PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY` | 早于 end_date 比较两个患者的疾病集合 | `primary_patient_id`, `comparison_patient_id`, `end_date` | `diseases1`, `diseases2` |
| `PATIENT_DISEASE_SET_COMPARISON_BY_START_DATE_QUERY` | 从某日期开始比较两个患者的疾病集合 | `primary_patient_id`, `comparison_patient_id`, `start_date` | `diseases1`, `diseases2` |
| `PATIENT_DISEASE_SET_COMPARISON_BY_DATE_RANGE_QUERY` | 在左闭右开日期区间内比较两个患者的疾病集合 | `primary_patient_id`, `comparison_patient_id`, `start_date`, `end_date` | `diseases1`, `diseases2` |
| `PATIENT_DISTINCT_DISEASES_BY_START_DATE_QUERY` | 查询患者从某日期开始的去重疾病 | `patient_id`, `start_date` | `d` |
| `PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的去重疾病 | `patient_id`, `start_date`, `end_date` | `d` |
| `PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY` | 查询患者早于 end_date 的去重 unknown 节点 | `patient_id`, `end_date` | `u` |
| `PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY` | 早于 end_date 比较两个患者的 unknown 集合 | `primary_patient_id`, `comparison_patient_id`, `end_date` | `unknowns1`, `unknowns2` |
| `PATIENT_DISTINCT_UNKNOWNS_BY_START_DATE_QUERY` | 查询患者从某日期开始的去重 unknown 节点 | `patient_id`, `start_date` | `u` |
| `PATIENT_UNKNOWN_SET_COMPARISON_BY_START_DATE_QUERY` | 从某日期开始比较两个患者的 unknown 集合 | `primary_patient_id`, `comparison_patient_id`, `start_date` | `unknowns1`, `unknowns2` |
| `PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY` | 查询患者左闭右开日期区间内的去重 unknown 节点 | `patient_id`, `start_date`, `end_date` | `u` |
| `PATIENT_UNKNOWN_SET_COMPARISON_BY_DATE_RANGE_QUERY` | 在左闭右开日期区间内比较两个患者的 unknown 集合 | `primary_patient_id`, `comparison_patient_id`, `start_date`, `end_date` | `unknowns1`, `unknowns2` |
| `PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY` | 查询患者训练日期的有序列表 | `patient_id` | `orderedDatesa` |

### `pattern_paths.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_RANDOMIZED_PATH_QUERY` | 不限日期随机抽取固定模式 path | `patient_id`, `per_g`, `limit` | `row` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY` | 从某日期开始随机抽取固定模式 path | `patient_id`, `start_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY` | 早于 end_date 随机抽取固定模式 path | `patient_id`, `end_date`, `per_g`, `limit` | `row` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_END_DATE_RANDOMIZED_PATH_QUERY` | 仅按早于 end_date 约束随机抽取固定模式 path | `patient_id`, `end_date`, `per_g`, `limit` | `row` |

### `pattern_statistics.py`

| Query | 用途 | 主要参数 | 返回 |
|---|---|---|---|
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY` | 不限日期统计固定模式 path | `patient_id` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY` | 按训练日期约束统计固定模式 path | `patient_id` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY` | 早于 end_date 统计固定模式 path | `patient_id`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY` | 从某日期开始统计固定模式 path | `patient_id`, `start_date` | `totalPaths`, `gCount`, `p2Count` |
| `PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY` | 在左闭右开日期区间内统计固定模式 path | `patient_id`, `start_date`, `end_date` | `totalPaths`, `gCount`, `p2Count` |
