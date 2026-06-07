# 変数一覧 / VARIABLES.md

## Project

A1 Bear Honey Buffet  
Module: Front Paw Contact Pad System  
Target: Arduino Uno Q + Raspberry Pi 4B

---

## 0. この文書の目的

この文書は、Front Paw Contact Pad System の実装で使用する変数名、型、範囲、意味を統一するための一覧である。

AIエージェント、Codex、GitHub Copilot、人間の開発者は、原則としてこの文書に定義された変数名を使用すること。

---

## 1. 命名ルール

### 1.1 基本ルール

```text
- snake_case を使用する
- boolean は true/false が分かる名前にする
- 単位がある値は変数名に単位を入れる
- percent, ms, raw, count などを明記する
```

良い例:

```text
honey_amount_percent
max_release_duration_ms
raw_contact_value
bear_detected
```

悪い例:

```text
value
data
flag
mode
x
```

---

## 2. 状態変数

| Variable | Type | Range / Values | Default | Owner | Description |
|---|---|---|---|---|---|
| `state` | string / enum | see State Enum | `IDLE` | Uno Q | 現在の状態機械の状態 |
| `previous_state` | string / enum | see State Enum | `IDLE` | Uno Q | 1つ前の状態 |
| `event` | string / enum | see Event Enum | `BOOT` | Uno Q | 最新イベント |
| `release_state` | string / enum | `RELEASE_ON`, `RELEASE_OFF` | `RELEASE_OFF` | Uno Q | 蜂蜜放出信号 |
| `system_safe` | bool | `true`, `false` | `true` | Uno Q | システムが安全状態か |
| `emergency_stop` | bool | `true`, `false` | `false` | Uno Q | 緊急停止が有効か |
| `error_code` | string / null | see Error Code Enum | `null` | Uno Q / Pi | エラー識別子 |
| `error_message` | string / null | any | `null` | Uno Q / Pi | エラー説明 |

---

## 3. 疑似センサー入力変数

実センサーがない初期段階では、以下の疑似入力を使う。

| Variable | Type | Range / Values | Default | Owner | Description |
|---|---|---|---|---|---|
| `simulated_bear_detected` | bool | `true`, `false` | `false` | Uno Q | 熊が来た想定の疑似入力 |
| `simulated_paw_contact` | bool | `true`, `false` | `false` | Uno Q | 前足が接触した想定の疑似入力 |
| `simulated_honey_amount_percent` | int | `0` to `100` | `80` | Uno Q | 蜂蜜残量の疑似入力 |
| `simulated_system_safe` | bool | `true`, `false` | `true` | Uno Q | システム安全状態の疑似入力 |
| `simulation_step` | int | `0` or greater | `0` | Uno Q | シミュレーションシナリオのステップ番号 |
| `simulation_scenario_name` | string | any | `default_demo` | Uno Q / Pi | 使用中の疑似入力シナリオ名 |

---

## 4. 判定済み入力変数

疑似入力または実センサー入力を、制御ロジックで使いやすい形に変換した変数。

| Variable | Type | Range / Values | Default | Owner | Description |
|---|---|---|---|---|---|
| `bear_detected` | bool | `true`, `false` | `false` | Uno Q | 熊を検出したか |
| `paw_contact` | bool | `true`, `false` | `false` | Uno Q | 前足接触を検出したか |
| `honey_amount_percent` | int | `0` to `100` | `80` | Uno Q | 蜂蜜残量 |
| `honey_enough` | bool | `true`, `false` | `true` | Uno Q | 蜂蜜残量がしきい値以上か |
| `contact_confirmed` | bool | `true`, `false` | `false` | Uno Q | 接触が一定時間継続し確定したか |
| `release_allowed` | bool | `true`, `false` | `false` | Uno Q | 放出してよい条件を満たしたか |

---

## 5. Raw sensor variables / 将来の実センサー用変数

現時点では未使用でも、将来的な置換を想定して予約する。

| Variable | Type | Range / Values | Default | Owner | Description |
|---|---|---|---|---|---|
| `raw_contact_value` | int / null | `0` to `1023` or null | `null` | Uno Q | 接触パッドの生値 |
| `raw_pressure_value` | int / null | `0` to `1023` or null | `null` | Uno Q | 圧力センサーの生値 |
| `raw_honey_sensor_value` | int / null | `0` to `1023` or null | `null` | Uno Q | 蜂蜜量センサーの生値 |
| `raw_distance_mm` | int / null | `0` or greater | `null` | Uno Q | 距離センサー値 |
| `raw_camera_detected` | bool / null | `true`, `false`, null | `null` | Uno Q / Pi | カメラ検出結果 |
| `contact_resistance_ohm` | float / null | `0` or greater | `null` | Uno Q | 接触抵抗の推定値 |
| `contact_impedance_ohm` | float / null | `0` or greater | `null` | Uno Q | 接触インピーダンスの推定値 |

注意:

```text
contact_resistance_ohm や contact_impedance_ohm は、実測系が安全に設計されるまで使用しない。
熊に電流を流す実験は行わない。
```

---

## 6. Timing variables / 時間変数

単位はすべて `ms`。

| Variable | Type | Unit | Default | Owner | Description |
|---|---|---:|---:|---|---|
| `current_time_ms` | unsigned long / int | ms | runtime | Uno Q | 現在時刻 |
| `state_entered_at_ms` | unsigned long / int | ms | `0` | Uno Q | 現状態に入った時刻 |
| `last_contact_time_ms` | unsigned long / int | ms | `0` | Uno Q | 最後に接触を検出した時刻 |
| `release_started_at_ms` | unsigned long / int | ms | `0` | Uno Q | RELEASE_ON開始時刻 |
| `cooldown_started_at_ms` | unsigned long / int | ms | `0` | Uno Q | COOLDOWN開始時刻 |
| `last_message_sent_at_ms` | unsigned long / int | ms | `0` | Uno Q | 最後にJSONを送信した時刻 |
| `last_log_written_at_ms` | unsigned long / int | ms | `0` | Pi | 最後にログを書いた時刻 |

---

## 7. Config variables / 設定値

設定値は `config.h` または `config.json` にまとめる。

| Variable | Type | Unit | Recommended Default | Description |
|---|---|---:|---:|---|
| `honey_min_threshold_percent` | int | % | `20` | 放出可能な最低蜂蜜残量 |
| `contact_confirm_duration_ms` | int | ms | `500` | 接触確定に必要な継続時間 |
| `max_release_duration_ms` | int | ms | `3000` | 1回の最大放出時間 |
| `cooldown_after_release_ms` | int | ms | `5000` | 放出後の待機時間 |
| `message_interval_ms` | int | ms | `1000` | JSON Lines送信間隔 |
| `sensor_update_interval_ms` | int | ms | `100` | センサー更新間隔 |
| `serial_baudrate` | int | baud | `115200` | シリアル通信速度 |
| `dashboard_refresh_interval_ms` | int | ms | `1000` | ダッシュボード更新間隔 |
| `default_honey_amount_percent` | int | % | `80` | 初期蜂蜜量 |
| `default_release_state` | string | enum | `RELEASE_OFF` | 初期放出状態 |

---

## 8. Hardware pin variables / Arduino Uno Q GPIO

ピン番号は仮定。実機配線に合わせて変更すること。

| Variable | Type | Example | Description |
|---|---|---:|---|
| `PIN_RELEASE_LED` | int | `13` | RELEASE_ON/OFFを表示するLED |
| `PIN_RELEASE_SIGNAL` | int | `8` | 蜂蜜機構側へ送るデジタル出力 |
| `PIN_EMERGENCY_STOP` | int | `7` | 緊急停止入力 |
| `PIN_SIM_BEAR_INPUT` | int | `2` | 熊検出疑似入力 |
| `PIN_SIM_CONTACT_INPUT` | int | `3` | 接触疑似入力 |
| `PIN_CONTACT_ANALOG` | int | `A0` | 接触パッドのアナログ入力 |
| `PIN_HONEY_ANALOG` | int | `A1` | 蜂蜜量センサーのアナログ入力 |
| `PIN_STATUS_LED` | int | `12` | システム状態LED |

---

## 9. State Enum

`state` は以下の値だけを使う。

| Value | Description |
|---|---|
| `IDLE` | 待機状態 |
| `BEAR_DETECTED` | 熊検出状態 |
| `CONTACT_CONFIRMED` | 前足接触確定状態 |
| `READY_TO_RELEASE` | 放出準備完了 |
| `RELEASING` | 蜂蜜放出中 |
| `COOLDOWN` | 放出後の待機中 |
| `ERROR_SAFE` | 異常時安全停止状態 |

---

## 10. Release State Enum

| Value | Description |
|---|---|
| `RELEASE_OFF` | 放出しない |
| `RELEASE_ON` | 放出する |

初期値と異常時は必ず `RELEASE_OFF`。

---

## 11. Event Enum

| Value | Description |
|---|---|
| `BOOT` | 起動 |
| `IDLE` | 待機 |
| `BEAR_DETECTED` | 熊検出 |
| `CONTACT_STARTED` | 接触開始 |
| `CONTACT_CONFIRMED` | 接触確定 |
| `HONEY_LOW` | 蜂蜜残量不足 |
| `READY_TO_RELEASE` | 放出準備完了 |
| `RELEASE_START` | 放出開始 |
| `RELEASE_TIMEOUT` | 放出時間上限に到達 |
| `RELEASE_END` | 放出終了 |
| `COOLDOWN_START` | クールダウン開始 |
| `COOLDOWN_END` | クールダウン終了 |
| `EMERGENCY_STOP` | 緊急停止 |
| `INVALID_INPUT` | 入力値異常 |
| `ERROR` | 一般エラー |
| `RESET` | リセット |

---

## 12. Error Code Enum

| Value | Description |
|---|---|
| `ERR_NONE` | エラーなし |
| `ERR_INVALID_HONEY_AMOUNT` | 蜂蜜量が0-100範囲外 |
| `ERR_INVALID_STATE` | 未定義状態 |
| `ERR_SERIAL_PARSE_FAILED` | JSONパース失敗 |
| `ERR_COMMUNICATION_TIMEOUT` | 通信タイムアウト |
| `ERR_EMERGENCY_STOP` | 緊急停止 |
| `ERR_UNKNOWN` | 不明なエラー |

---

## 13. JSON Lines schema

Arduino Uno QからRaspberry Piへ送信する1行JSONの変数。

| Field | Type | Required | Example |
|---|---|---:|---|
| `timestamp` | string | yes | `2026-05-23T18:30:00+09:00` |
| `state` | string | yes | `IDLE` |
| `previous_state` | string | no | `COOLDOWN` |
| `event` | string | yes | `RELEASE_START` |
| `bear_detected` | bool | yes | `true` |
| `paw_contact` | bool | yes | `true` |
| `contact_confirmed` | bool | no | `true` |
| `raw_contact_value` | int/null | no | `512` |
| `honey_amount_percent` | int | yes | `80` |
| `honey_enough` | bool | no | `true` |
| `system_safe` | bool | yes | `true` |
| `emergency_stop` | bool | yes | `false` |
| `release_allowed` | bool | no | `true` |
| `release_state` | string | yes | `RELEASE_ON` |
| `error_code` | string/null | no | `ERR_NONE` |
| `error_message` | string/null | no | `null` |

Example:

```json
{"timestamp":"2026-05-23T18:30:05+09:00","state":"RELEASING","previous_state":"READY_TO_RELEASE","event":"RELEASE_START","bear_detected":true,"paw_contact":true,"contact_confirmed":true,"raw_contact_value":null,"honey_amount_percent":80,"honey_enough":true,"system_safe":true,"emergency_stop":false,"release_allowed":true,"release_state":"RELEASE_ON","error_code":"ERR_NONE","error_message":null}
```

---

## 14. CSV log columns

Raspberry Pi側で保存するCSV列。

```csv
timestamp,state,previous_state,event,bear_detected,paw_contact,contact_confirmed,raw_contact_value,honey_amount_percent,honey_enough,system_safe,emergency_stop,release_allowed,release_state,error_code,error_message
```

---

## 15. Python側変数

Raspberry Pi側 Python 実装で使う変数。

| Variable | Type | Default | Description |
|---|---|---|---|
| `serial_port` | str | `/dev/ttyACM0` | Uno Qのシリアルポート |
| `baudrate` | int | `115200` | 通信速度 |
| `log_dir` | Path/str | `data/logs` | ログ保存先 |
| `log_file_path` | Path/str | runtime | CSVファイルパス |
| `latest_state` | dict | `{}` | 最新の受信状態 |
| `received_line` | str | runtime | シリアルから受け取った1行 |
| `parsed_message` | dict | runtime | JSONパース後のデータ |
| `required_fields` | list[str] | see schema | 必須フィールド一覧 |
| `csv_fieldnames` | list[str] | see CSV columns | CSV列名 |
| `invalid_message_count` | int | `0` | 不正メッセージ数 |
| `received_message_count` | int | `0` | 受信メッセージ数 |

---

## 16. Dashboard variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `dashboard_host` | str | `0.0.0.0` | ダッシュボードのホスト |
| `dashboard_port` | int | `8080` | ダッシュボードのポート |
| `latest_log_path` | Path/str | runtime | 表示対象ログ |
| `refresh_interval_sec` | int | `1` | 表示更新間隔 |
| `display_release_state` | str | `RELEASE_OFF` | UI表示用release状態 |
| `display_event` | str | `IDLE` | UI表示用イベント |

---

## 17. Decision logic variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `can_release` | bool | `false` | 放出可能かどうか |
| `is_honey_enough` | bool | `true` | 蜂蜜量がしきい値以上か |
| `is_contact_stable` | bool | `false` | 接触が安定しているか |
| `release_elapsed_ms` | int | `0` | 放出開始からの経過時間 |
| `cooldown_elapsed_ms` | int | `0` | cooldown開始からの経過時間 |
| `should_enter_error_safe` | bool | `false` | ERROR_SAFEに入るべきか |

---

## 18. Recommended constants in Arduino config.h

```cpp
#pragma once

const int PIN_RELEASE_LED = 13;
const int PIN_RELEASE_SIGNAL = 8;
const int PIN_EMERGENCY_STOP = 7;
const int PIN_SIM_BEAR_INPUT = 2;
const int PIN_SIM_CONTACT_INPUT = 3;
const int PIN_CONTACT_ANALOG = A0;
const int PIN_HONEY_ANALOG = A1;
const int PIN_STATUS_LED = 12;

const int HONEY_MIN_THRESHOLD_PERCENT = 20;
const unsigned long CONTACT_CONFIRM_DURATION_MS = 500;
const unsigned long MAX_RELEASE_DURATION_MS = 3000;
const unsigned long COOLDOWN_AFTER_RELEASE_MS = 5000;
const unsigned long MESSAGE_INTERVAL_MS = 1000;
const unsigned long SENSOR_UPDATE_INTERVAL_MS = 100;
const int SERIAL_BAUDRATE = 115200;
```

---

## 19. Reserved variables / 予約変数

将来的な拡張用。MVPでは未使用でよい。

| Variable | Type | Description |
|---|---|---|
| `bear_distance_mm` | int/null | 熊までの距離 |
| `bear_confidence_score` | float/null | カメラ/AI検出の信頼度 |
| `honey_release_level_percent` | int | 放出量制御 |
| `release_duration_request_ms` | int | 蜂の巣機構側へ要求する放出時間 |
| `battery_voltage_v` | float/null | 電源電圧 |
| `temperature_c` | float/null | 温度 |
| `humidity_percent` | float/null | 湿度 |
| `device_id` | string | デバイス識別子 |
| `firmware_version` | string | Uno Q側ファームウェア版 |
| `software_version` | string | Raspberry Pi側ソフトウェア版 |

---

## 20. Minimal required variables for MVP

MVPで最低限必要な変数は以下。

```text
state
event
bear_detected
paw_contact
honey_amount_percent
system_safe
emergency_stop
release_state
current_time_ms
release_started_at_ms
cooldown_started_at_ms
honey_min_threshold_percent
max_release_duration_ms
cooldown_after_release_ms
```

---

## 21. 一文要約

このプロジェクトでは、変数名を明確に統一し、疑似入力から実センサー入力へ安全に置き換えられるようにする。特に、`release_state` は常に安全側の `RELEASE_OFF` を初期値・異常時の値として扱う。
