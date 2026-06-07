# AI実装指示書 / AI_DEVELOPMENT_INSTRUCTIONS.md

## Project

A1 Bear Honey Buffet  
Module: Front Paw Contact Pad System  
Owner: LIU Chengyang / 刘承洋_C.Y.LIU  
Target hardware: Arduino Uno Q + Raspberry Pi 4B

---

## 0. この指示書の目的

この文書は、AIエージェント、Codex、GitHub Copilot、または開発補助AIに対して、A1プロジェクトの **Front Paw Contact Pad System** を実装させるための指示書である。

このシステムは、熊が前足で接触パッドに触れたことを検知・模擬し、蜂蜜放出機構へ安全な `RELEASE_ON` / `RELEASE_OFF` 信号を送る電子制御プロトタイプである。

現時点では実センサーが手元にないため、最初の実装では **疑似センサー入力** を使うこと。

---

## 1. 最優先ゴール

AIエージェントは、まず以下のMVPを完成させること。

```text
Arduino Uno Q:
  simulated sensor inputs
      ↓
  release decision logic
      ↓
  RELEASE_ON / RELEASE_OFF output
      ↓
  JSON Lines output

Raspberry Pi 4B:
  receive JSON Lines
      ↓
  save CSV logs
      ↓
  display latest state
```

### MVP v0.1 の達成条件

```text
[ ] Arduino Uno Q側で疑似入力を生成できる
[ ] bear_detected / paw_contact / honey_amount_percent / system_safe / emergency_stop を扱える
[ ] 安全条件を満たしたときだけ RELEASE_ON になる
[ ] 条件を満たさないとき、異常時、緊急停止時は必ず RELEASE_OFF になる
[ ] Uno QからJSON Lines形式で状態を出力できる
[ ] Raspberry Pi 4BでJSON Linesを受け取りCSVログに保存できる
[ ] 最新状態をターミナルまたは簡易Web画面で確認できる
[ ] READMEに実行方法が書かれている
```

---

## 2. システム境界

### 2.1 AIが実装する範囲

AIは以下を実装する。

```text
- Front Paw Contact Pad System の制御ロジック
- 疑似センサー入力
- release decision logic
- 状態遷移
- JSON Lines出力
- Raspberry Pi側のCSVロガー
- 必要に応じた簡易ダッシュボード
- 実行手順書
- テストケース
```

### 2.2 AIが実装してはいけない範囲

AIは以下を実装しない。

```text
- 蜂の巣内部の機械構造
- Flow Hive風の可動セル構造
- Queen Excluderの物理設計
- 本物の蜂・熊を使う実験手順
- 高電圧・大電流を使う抵抗測定
- 電撃・刺激を与える装置
- 本物のポンプ・電磁弁を無制限に動かす制御
```

---

## 3. ハードウェア役割分担

### 3.1 Arduino Uno Q

Arduino Uno Qは **現場側のメイン制御基板** とする。

担当:

```text
- 疑似センサー入力
- 将来的な実センサー入力
- 接触判定
- しきい値判定
- safety check
- RELEASE_ON / RELEASE_OFF の決定
- LED / GPIO / serial output
```

設計方針:

```text
- リアルタイム性が必要な判断はArduino Uno Q側に置く
- 異常時はArduino Uno Q単体でもRELEASE_OFFへ戻れるようにする
- Raspberry Piが落ちても安全側に倒れるようにする
```

### 3.2 Raspberry Pi 4B

Raspberry Pi 4Bは **ログ・可視化・デモ用上位機** とする。

担当:

```text
- Uno Qから状態データを受信
- CSVログ保存
- 最新状態の表示
- 簡易ダッシュボード
- 発表用デモ画面
```

設計方針:

```text
- Raspberry Piを唯一の安全制御器にしない
- Raspberry Piは制御の主役ではなく、記録・表示・共有の役割にする
```

---

## 4. 安全ルール

AIは以下を必ず守ること。

### 4.1 Fail-safe

初期状態、異常状態、通信異常、未定義状態では必ず以下にする。

```text
release_state = RELEASE_OFF
```

### 4.2 RELEASE_ON 条件

`RELEASE_ON` にしてよいのは、以下をすべて満たすときだけ。

```text
bear_detected == true
paw_contact == true
honey_amount_percent >= honey_min_threshold_percent
system_safe == true
emergency_stop == false
```

それ以外は必ず `RELEASE_OFF`。

### 4.3 RELEASE_ON の時間制限

`RELEASE_ON` は無制限に継続してはならない。

```text
if elapsed_release_time_ms >= max_release_duration_ms:
    release_state = RELEASE_OFF
```

### 4.4 Cooldown

放出後は一定時間 `COOLDOWN` に入り、連続放出を防ぐ。

```text
cooldown_after_release_ms
```

### 4.5 禁止事項

```text
- 高電圧を使う接触測定
- 熊に電流を流す設計
- 電撃的な防御・刺激システム
- 実動物への未許可テスト
- 安全停止なしのrelease制御
```

---

## 5. 実装すべき状態遷移

AIは、制御ロジックを状態機械として実装すること。

```text
IDLE
  ↓ bear_detected
BEAR_DETECTED
  ↓ paw_contact confirmed
CONTACT_CONFIRMED
  ↓ honey enough and system safe
READY_TO_RELEASE
  ↓ start release
RELEASING
  ↓ max_release_duration_ms elapsed
COOLDOWN
  ↓ cooldown_after_release_ms elapsed
IDLE
```

異常時:

```text
ANY_STATE
  ↓ emergency_stop / invalid input / internal error
ERROR_SAFE
  ↓ RESET command
IDLE
```

`ERROR_SAFE` では必ず `RELEASE_OFF`。

---

## 6. 実装フェーズ

### Phase 1: ドキュメントと骨格作成

AIはまず以下を作成する。

```text
docs/block_diagram.md
docs/state_machine.md
docs/interface_spec.md
```

内容:

```text
- システムブロック図
- 状態遷移図
- JSON Lines仕様
- CSVログ仕様
- Uno QとRaspberry Piの役割分担
```

---

### Phase 2: Arduino Uno Q 側 MVP

作成するディレクトリ:

```text
arduino_uno_q/contact_pad_controller/
```

作成するファイル:

```text
contact_pad_controller.ino
config.h
README.md
```

実装内容:

```text
- simulated_bear_detected
- simulated_paw_contact
- simulated_honey_amount_percent
- simulated_system_safe
- emergency_stop
- state machine
- release decision logic
- release LED output
- JSON Lines serial output
```

最初は実センサー入力を使わず、疑似入力でよい。

---

### Phase 3: Raspberry Pi 4B ロガー

作成するディレクトリ:

```text
raspberry_pi/logger/
```

作成するファイル:

```text
serial_logger.py
requirements.txt
README.md
```

実装内容:

```text
- serial portからJSON Linesを受信
- JSONをvalidate
- CSVへ追記保存
- 最新状態をターミナル表示
- 不正JSONを破棄してログに警告表示
```

---

### Phase 4: Raspberry Pi 4B 簡易ダッシュボード

作成するディレクトリ:

```text
raspberry_pi/dashboard/
```

作成するファイル:

```text
app.py
requirements.txt
README.md
```

実装内容:

```text
- 最新CSVまたは最新JSONを読み込む
- bear_detected / paw_contact / honey_amount_percent / release_state を表示
- 直近イベントを表示
```

Web化する場合は、FlaskまたはFastAPIのどちらかを使ってよい。  
MVPではターミナル表示でも可。

---

### Phase 5: テスト

作成するディレクトリ:

```text
tests/
```

最低限、以下のテストケースを通すこと。

| Case | bear_detected | paw_contact | honey_amount_percent | system_safe | emergency_stop | Expected |
|---|---:|---:|---:|---:|---:|---|
| no_bear | false | false | 80 | true | false | RELEASE_OFF |
| bear_no_contact | true | false | 80 | true | false | RELEASE_OFF |
| contact_honey_low | true | true | 10 | true | false | RELEASE_OFF |
| ready_to_release | true | true | 80 | true | false | RELEASE_ON |
| unsafe_system | true | true | 80 | false | false | RELEASE_OFF |
| emergency_stop | true | true | 80 | true | true | RELEASE_OFF |
| timeout | true | true | 80 | true | false | RELEASE_OFF after timeout |

---

## 7. 推奨リポジトリ構成

```text
a1-front-paw-contact-pad/
├─ README.md
├─ AI_DEVELOPMENT_INSTRUCTIONS.md
├─ PROJECT_GUARDRAILS.md
├─ VARIABLES.md
├─ docs/
│  ├─ block_diagram.md
│  ├─ state_machine.md
│  └─ interface_spec.md
├─ arduino_uno_q/
│  ├─ contact_pad_controller/
│  │  ├─ contact_pad_controller.ino
│  │  ├─ config.h
│  │  └─ README.md
├─ raspberry_pi/
│  ├─ logger/
│  │  ├─ serial_logger.py
│  │  ├─ requirements.txt
│  │  └─ README.md
│  ├─ dashboard/
│  │  ├─ app.py
│  │  ├─ requirements.txt
│  │  └─ README.md
├─ data/
│  └─ logs/
├─ examples/
│  ├─ sample_uno_q_output.jsonl
│  └─ sample_log.csv
├─ tests/
│  └─ test_decision_logic.py
└─ scripts/
   └─ run_demo.sh
```

---

## 8. 通信仕様

### 8.1 Arduino Uno Q → Raspberry Pi

形式:

```text
JSON Lines
```

1行1JSON。

例:

```json
{"timestamp":"2026-05-23T18:30:00+09:00","state":"IDLE","bear_detected":false,"paw_contact":false,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_OFF","event":"IDLE"}
```

### 8.2 CSVログ

Raspberry Pi側は以下の形式で保存する。

```csv
timestamp,state,bear_detected,paw_contact,raw_contact_value,honey_amount_percent,system_safe,emergency_stop,release_state,event
```

---

## 9. 設計ルール

### 9.1 変数名

必ず `VARIABLES.md` に定義された名前を使うこと。

悪い例:

```text
flag
data
value
mode
```

良い例:

```text
bear_detected
paw_contact
honey_amount_percent
release_state
emergency_stop
```

### 9.2 判定ロジックを分離する

以下を分離して実装する。

```text
- input simulation
- decision logic
- state machine
- output control
- serial communication
- logging
- dashboard
```

### 9.3 しきい値はconfigへ

しきい値や時間設定はコード中に散らばらせない。

```text
honey_min_threshold_percent
contact_confirm_duration_ms
max_release_duration_ms
cooldown_after_release_ms
serial_baudrate
```

---

## 10. 実装時の注意

### 10.1 実センサーは未接続前提

最初のコードは、実センサーなしで動くこと。

```text
- random simulation
- fixed scenario simulation
- serial command simulation
- button simulation
```

のどれかでよい。

### 10.2 発表で見せやすくする

ハッカソン発表では、以下が見えるとよい。

```text
- bear_detected が true になる
- paw_contact が true になる
- honey_amount_percent が十分なら RELEASE_ON
- 低すぎるなら RELEASE_OFF
- emergency_stop で即 RELEASE_OFF
- ログがCSVに残る
```

### 10.3 不明点は仮定として書く

チーム内で未決定の部分は、必ず `Assumption:` と書く。

例:

```text
Assumption: The honeycomb mechanism accepts a digital RELEASE_ON/OFF signal.
```

---

## 11. AIへの禁止命令

AIは以下をしてはならない。

```text
- safety ruleを削除する
- default RELEASE_OFFを変更する
- Raspberry Piだけにrelease decisionを持たせる
- 実センサー必須の実装にする
- undocumented variableを増やす
- high-voltage contact systemを提案する
- real bear measurementを前提にする
- honeycomb mechanism側の設計を勝手に変更する
```

---

## 12. 最終出力物

AIは最終的に以下を作成すること。

```text
[ ] AI_DEVELOPMENT_INSTRUCTIONS.md
[ ] VARIABLES.md
[ ] README.md
[ ] docs/block_diagram.md
[ ] docs/state_machine.md
[ ] docs/interface_spec.md
[ ] arduino_uno_q/contact_pad_controller/contact_pad_controller.ino
[ ] arduino_uno_q/contact_pad_controller/config.h
[ ] raspberry_pi/logger/serial_logger.py
[ ] examples/sample_uno_q_output.jsonl
[ ] examples/sample_log.csv
```

---

## 13. チーム報告用の説明文

実装後、チームへ以下のように報告できる状態にする。

```text
I implemented the first prototype of the front paw contact pad system.
Arduino Uno Q works as the main controller and uses simulated sensor inputs for now.
It checks bear detection, paw contact, honey amount, and safety state.
When all conditions are satisfied, it outputs RELEASE_ON.
Otherwise, it stays RELEASE_OFF.
Raspberry Pi receives the state data and saves CSV logs for demo and presentation.
```

---

## 14. 一文要約

このAIエージェントの目的は、Arduino Uno Qを現場制御、Raspberry Pi 4Bをログ・可視化として使い、実センサーなしでも動作する安全なFront Paw Contact Pad SystemのMVPを実装することである。
