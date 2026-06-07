# 守るべきこと / Project Guardrails

## Project

A1: Bear Honey Buffet  
担当範囲: Front Paw Contact Pad System / Electronic & Control Prototype  
作成者: LIU Chengyang / 刘承洋_C.Y.LIU

---

## 0. このドキュメントの目的

このドキュメントは、A1プロジェクトで Front Paw Contact Pad System を作るときに守るべきルールをまとめたものです。

本システムは、熊が前足で接触パッドに触れたことを検知し、蜂蜜放出機構へ安全な release signal を送るための電子制御プロトタイプです。

---

## 1. 最重要方針

### 1.1 役割分担を混ぜない

A1プロジェクトは、以下のように分離して進めます。

```text
Beehive / Honeycomb Mechanism
  - honeycomb structure
  - movable plate
  - honey release physical mechanism
  - queen excluder / hive zoning
  - mainly Goda-san side

Front Paw Contact Pad System
  - bear/contact detection logic
  - simulated sensor input
  - electronic control
  - release signal output
  - data logging / dashboard
  - LIU side
```

この境界を曖昧にしないこと。

### 1.2 センサーがなくても止めない

現時点で実センサーが手元にないため、最初はすべて simulated input で開発する。

```text
Real sensor input
  ↓ replaced by
Simulated input / serial command / button / fixed test data
```

後から本物のセンサーへ差し替えられるように、入力インターフェースを抽象化する。

### 1.3 Arduino Uno Qを現場制御の中心にする

Arduino Uno Qを Front Paw Contact Pad System のメイン制御基板として扱う。

- MCU側: センサー入力、しきい値判定、低遅延I/O、release signal
- Linux/MPU側: 上位処理、ローカルログ、軽量UI、必要に応じたAI処理
- Raspberry Pi 4B: 外部ログ、ダッシュボード、可視化、発表用デモ

Raspberry Pi 4Bにリアルタイム制御を寄せすぎない。

### 1.4 本物の熊・蜂に危害を与えない

このプロジェクトはハッカソン用プロトタイプであり、実動物に対する刺激・電撃・危険な接触実験をしてはならない。

禁止事項:

- 熊に電流を流す設計
- 高電圧・大電流を使う接触パッド
- 実動物への未許可テスト
- 蜂の幼虫や蜂群を傷つける機構の提案
- 安全管理者・専門家なしの動物実験

許可される範囲:

- 低電圧・微小電流を想定した安全な測定概念の整理
- 人間の手や導電性スポンジなどによる模擬試験
- ダミー入力による制御ロジック検証
- 動物園・専門家・教員の監督下での将来的な検討

---

## 2. システムの基本思想

### 2.1 このシステムが判断すること

Front Paw Contact Pad System は以下を判断する。

```text
1. 熊が近づいたか
2. 前足がパッドに触れたか
3. 蜂蜜量は十分か
4. システムは安全状態か
5. 蜂蜜を放出してよいか
```

### 2.2 このシステムが直接やらないこと

以下は担当外、または後工程。

```text
- 蜂の巣内部の機械構造設計
- honeycomb cell の可動機構設計
- queen excluder の実装
- 本物の蜂蜜流路の詳細構造
- 実際の熊を使った検証
```

---

## 3. 制御ロジックの原則

### 3.1 Fail-safeを基本にする

異常時は必ず RELEASE_OFF にする。

RELEASE_ON にしてよい条件:

```text
bear_detected == true
paw_contact == true
honey_amount >= HONEY_MIN_THRESHOLD
system_safe == true
emergency_stop == false
```

どれか1つでも満たさない場合は RELEASE_OFF。

### 3.2 いきなり放出しない

ノイズや一瞬の接触で放出しない。最低限、以下を入れる。

```text
- contact_confirm_duration_ms
- release_timeout_ms
- cooldown_after_release_ms
```

### 3.3 放出は時間制限する

RELEASE_ON は無制限に継続しない。

例:

```text
max_release_duration_ms = 3000
```

時間を超えたら RELEASE_OFF に戻す。

### 3.4 デモではLEDをrelease actuatorの代替にする

本物のポンプ・サーボ・電磁弁がない場合は、LEDで release signal を表現する。

```text
LED ON  = RELEASE_ON
LED OFF = RELEASE_OFF
```

---

## 4. データ・ログの原則

### 4.1 すべての状態変化を記録する

最低限、次の項目をCSVに保存する。

```csv
timestamp,bear_detected,paw_contact,honey_amount,system_safe,release_state,event
```

### 4.2 ログは発表で使える形式にする

発表で示しやすいように、状態遷移が追えるログにする。

例:

```csv
2026-05-23T18:30:00+09:00,0,0,80,1,OFF,IDLE
2026-05-23T18:30:03+09:00,1,0,80,1,OFF,BEAR_DETECTED
2026-05-23T18:30:05+09:00,1,1,80,1,ON,RELEASE_START
2026-05-23T18:30:08+09:00,1,1,78,1,OFF,RELEASE_TIMEOUT
```

### 4.3 生データと判定結果を分ける

センサー値と判定値を混ぜない。

```text
raw_contact_value: 0-1023
paw_contact: true/false
```

---

## 5. コード設計ルール

### 5.1 名前を明確にする

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
system_safe
```

### 5.2 ハード依存部分とロジックを分ける

以下を分離する。

```text
hardware_io
decision_logic
communication
logging
dashboard
```

### 5.3 しきい値はコードに直書きしない

しきい値はconfigとしてまとめる。

例:

```json
{
  "honey_min_threshold_percent": 20,
  "contact_confirm_duration_ms": 500,
  "max_release_duration_ms": 3000,
  "cooldown_after_release_ms": 5000
}
```

### 5.4 MVPでは複雑にしすぎない

最初は以下だけでよい。

```text
Input:
- simulated_bear_detected
- simulated_paw_contact
- simulated_honey_amount
- simulated_system_safe

Logic:
- release decision

Output:
- RELEASE_ON / RELEASE_OFF
- serial message
- LED
```

---

## 6. AI / Codex / GitHub Copilot を使うときのルール

### 6.1 AIに丸投げしない

AIには実装補助をさせるが、最終判断は人間が行う。

### 6.2 AIに守らせる条件

AI agentには必ず以下を指示する。

```text
- Do not design harmful animal experiments.
- Do not use high voltage/current for animal contact.
- Keep Arduino Uno Q as the main field controller.
- Keep Raspberry Pi 4B for logging/dashboard/demo.
- Use simulated inputs before real sensors are available.
- Keep honeycomb mechanism and contact pad system separated.
- Always default to RELEASE_OFF on error.
```

### 6.3 AIが勝手に変更してはいけないもの

```text
- system boundary
- safety rule
- release condition
- log schema
- hardware role assignment
```

---

## 7. チーム内コミュニケーションルール

### 7.1 Godaさん側との接続点を明確にする

Godaさん側に渡す信号仕様はシンプルにする。

```text
RELEASE_ON
RELEASE_OFF
```

必要であれば後から拡張する。

```text
release_level: 0-100
release_duration_ms
```

### 7.2 未確定部分は未確定として書く

まだ決まっていないものは、仮定として明示する。

例:

```text
Assumption: The honey release mechanism can accept a digital ON/OFF signal.
```

### 7.3 図で共有する

言語が混ざるチームなので、ブロック図・状態遷移図・簡単なスケッチを優先する。

---

## 8. Definition of Done

MVP v0.1 の完了条件:

```text
[ ] Arduino Uno Q上で疑似入力を生成できる
[ ] bear_detected / paw_contact / honey_amount / system_safe を扱える
[ ] release decision logic が動く
[ ] RELEASE_ON / RELEASE_OFF を出せる
[ ] LEDまたはserial outputで状態が見える
[ ] Raspberry Pi 4BでCSVログを保存できる
[ ] ブロック図がある
[ ] 状態遷移図がある
[ ] READMEに実行方法が書いてある
[ ] 危険な動物実験を含まない
```

---

## 9. 一文での原則

このプロジェクトでは、Arduino Uno Qを現場制御の中心に置き、Raspberry Pi 4Bを記録・可視化・発表用に使い、センサーがない段階では疑似入力で安全な制御ロジックを先に完成させる。
