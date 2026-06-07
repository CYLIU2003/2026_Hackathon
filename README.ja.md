# A1 Front Paw Contact Pad System

## 概要

このリポジトリは、A1 **Bear Honey Buffet** ハッカソンプロジェクトにおける **Front Paw Contact Pad System** のプロトタイプを扱う。

本システムの目的は、熊が接近し、前足で接触パッドに触れた状態を検知または模擬し、その結果に基づいて蜂の巣機構へ安全な蜂蜜放出信号を送ることである。

初期バージョンでは、実センサーは必須ではない。  
センサーが未準備の段階でも開発を進められるように、疑似入力を用いて制御ロジックを先に検証する。

---

## プロジェクトのビジョン

A1システム全体は、大きく2つの部分に分ける。

```text
[Bear]
  ↓
[Front Paw Contact Pad System]  ← 本リポジトリ / LIU担当
  ↓ release signal
[Honeycomb / Bee Hive Mechanism] ← Godaさん側
  ↓
[Honey is released]
```

このリポジトリは、電子制御・検知・ログ記録側のみを対象とする。

---

## このシステムが行うこと

Front Paw Contact Pad System は、以下を確認する。

```text
1. 熊が来たか
2. 前足が接触パッドに触れているか
3. 蜂蜜量は十分か
4. システムは安全状態か
5. 蜂蜜放出機構を動作させてよいか
```

すべての条件を満たした場合、以下を出力する。

```text
RELEASE_ON
```

条件を満たさない場合は、以下を出力する。

```text
RELEASE_OFF
```

---

## ハードウェア構成

### Arduino Uno Q

Arduino Uno Q は、現場側のメイン制御基板として使用する。

主な役割:

```text
- 接触パッド入力
- 疑似センサー入力
- しきい値判定
- 放出判定ロジック
- LED / GPIO / release signal 出力
- serial または network 通信
```

Arduino Uno Q は、Linuxが動作するMPU側とリアルタイム制御用MCU側を持つため、現場制御に適している。

参考:

```text
https://docs.arduino.cc/hardware/uno-q
https://docs.arduino.cc/tutorials/uno-q/user-manual/
```

### Raspberry Pi 4B

Raspberry Pi 4B は、上位側のログ記録・可視化・デモ表示用デバイスとして使用する。

主な役割:

```text
- Arduino Uno Q から状態データを受信
- CSVログ保存
- ダッシュボード表示
- 最新状態の可視化
- 発表用デモ支援
- SSH / Tailscale などによる遠隔確認
```

Raspberry Pi を唯一の安全制御器にしないこと。  
放出判定の基本は Arduino Uno Q 側に置く。

---

## システム構成

```text
┌────────────────────────────┐
│ Bear / Simulated Bear       │
└─────────────┬──────────────┘
              ↓
┌────────────────────────────┐
│ Front Paw Contact Pad       │
│ - contact input             │
│ - future pressure/R sensor  │
│ - currently simulated input │
└─────────────┬──────────────┘
              ↓
┌────────────────────────────┐
│ Arduino Uno Q               │
│ - sensor simulation         │
│ - decision logic            │
│ - RELEASE_ON/OFF output     │
│ - serial JSON output        │
└─────────────┬──────────────┘
              ↓
┌────────────────────────────┐
│ Raspberry Pi 4B             │
│ - receive state             │
│ - CSV logging               │
│ - dashboard                 │
│ - visualization             │
└─────────────┬──────────────┘
              ↓
┌────────────────────────────┐
│ Presentation / Team Demo    │
└────────────────────────────┘
```

---

## MVP v0.1

最初のMVPでは、以下を実現する。

### 入力

```text
simulated_bear_detected
simulated_paw_contact
simulated_honey_amount_percent
simulated_system_safe
emergency_stop
```

### ロジック

```text
if bear_detected
and paw_contact
and honey_amount_percent >= threshold
and system_safe
and not emergency_stop:
    release_state = RELEASE_ON
else:
    release_state = RELEASE_OFF
```

### 出力

```text
- RELEASE_ON / RELEASE_OFF
- LED ON/OFF
- JSON Lines over serial
- CSV log on Raspberry Pi
```

---

## 状態遷移

```text
IDLE
  ↓ bear detected
BEAR_DETECTED
  ↓ paw contact confirmed
CONTACT_CONFIRMED
  ↓ honey enough and system safe
READY_TO_RELEASE
  ↓ release command
RELEASING
  ↓ timeout
COOLDOWN
  ↓ cooldown finished
IDLE
```

異常時:

```text
ANY_STATE
  ↓ invalid data / emergency stop / communication error
ERROR_SAFE
  ↓ reset
IDLE
```

`ERROR_SAFE` では、必ず `RELEASE_OFF` にする。

---

## 安全方針

このプロジェクトはハッカソン用プロトタイプであり、人や動物を傷つけてはならない。

禁止事項:

```text
- 接触パッドに高電圧・大電流を使う
- 電撃装置を設計する
- 専門家の監督なしに本物の熊で試験する
- 妥当な測定なしに本物の熊の抵抗値として主張する
- 安全停止なしで蜂蜜放出を行う
```

必ず守ること:

```text
- 初期状態と異常時は RELEASE_OFF
- 実センサーがない段階では疑似入力を使用する
- RELEASE_ON には時間制限を設ける
- 重要な状態変化をログに残す
- 接触パッド制御と蜂の巣機構を分離する
```

---

## データ形式

Arduino Uno Q から Raspberry Pi へは JSON Lines を送信する。

例:

```json
{"timestamp":"2026-05-23T18:30:00+09:00","bear_detected":false,"paw_contact":false,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_OFF","state":"IDLE","event":"IDLE"}
{"timestamp":"2026-05-23T18:30:05+09:00","bear_detected":true,"paw_contact":true,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_ON","state":"RELEASING","event":"RELEASE_START"}
```

Raspberry Pi 側では CSV ログとして保存する。

例:

```csv
timestamp,bear_detected,paw_contact,honey_amount_percent,system_safe,emergency_stop,release_state,state,event
2026-05-23T18:30:00+09:00,false,false,80,true,false,RELEASE_OFF,IDLE,IDLE
2026-05-23T18:30:05+09:00,true,true,80,true,false,RELEASE_ON,RELEASING,RELEASE_START
```

---

## 推奨リポジトリ構成

```text
a1-front-paw-contact-pad/
├─ README.md
├─ README.ja.md
├─ README.zh-CN.md
├─ README.ko.md
├─ AI_DEVELOPMENT_INSTRUCTIONS.md
├─ VARIABLES.md
├─ PROJECT_GUARDRAILS.md
├─ docs/
│  ├─ block_diagram.md
│  ├─ state_machine.md
│  └─ interface_spec.md
├─ arduino_uno_q/
│  ├─ contact_pad_controller/
│  │  ├─ contact_pad_controller.ino
│  │  └─ config.h
│  └─ README.md
├─ raspberry_pi/
│  ├─ logger/
│  │  ├─ serial_logger.py
│  │  └─ requirements.txt
│  ├─ dashboard/
│  │  ├─ app.py
│  │  └─ requirements.txt
│  └─ README.md
├─ data/
│  └─ logs/
├─ examples/
│  └─ sample_log.csv
└─ scripts/
   └─ run_demo.sh
```

---

## 開発ロードマップ

### Phase 1: 設計

```text
[ ] ブロック図を作成する
[ ] 状態遷移図を作成する
[ ] JSON/CSVインターフェースを定義する
[ ] 蜂の巣機構側へ渡す release signal を定義する
```

### Phase 2: Uno Q 単体プロトタイプ

```text
[ ] simulated bear_detected input
[ ] simulated paw_contact input
[ ] simulated honey_amount input
[ ] release decision logic
[ ] LEDまたはserialによる RELEASE_ON/OFF 出力
```

### Phase 3: Raspberry Pi ロガー

```text
[ ] Uno Q から JSON Lines を受信する
[ ] メッセージ形式を検証する
[ ] CSVログに保存する
[ ] ターミナルで最新状態を表示する
```

### Phase 4: デモ用ダッシュボード

```text
[ ] 最新の bear_detected を表示する
[ ] 最新の paw_contact を表示する
[ ] honey_amount を表示する
[ ] release_state を表示する
[ ] 直近イベントログを表示する
```

### Phase 5: 実センサーへの置換

```text
[ ] simulated bear_detected を実センサー候補へ置換する
[ ] simulated paw_contact を実センサー候補へ置換する
[ ] simulated honey_amount を実センサー候補へ置換する
[ ] ダミー物体でのみ試験する
```

---

## チームへの説明文

```text
I will develop the front paw contact pad system as a separate electronic/control module.
Arduino Uno Q will be used as the main controller for simulated sensor inputs and release decision logic.
Raspberry Pi 4B will be used for logging, dashboard, and presentation demo.
Since I do not have real sensors now, I will first build the logic using simulated inputs.
Later, the simulated inputs can be replaced with actual sensors.
```

---

## 現在の仮定

```text
- 蜂の巣機構側は単純な RELEASE_ON/OFF 信号を受け取れる
- 初期段階では物理センサーは使用しない
- 最初のデモではポンプやバルブの代わりにLED/serial出力を使う
- 実動物による試験は行わない
- このプロジェクトはハッカソン用の概念検証である
```

---

## MVP v0.1 完了条件

```text
[ ] Uno Q が疑似入力を生成できる
[ ] Uno Q が RELEASE_ON/OFF を判断できる
[ ] LEDまたはserialで RELEASE_ON/OFF が見える
[ ] Raspberry Pi が状態データを受信できる
[ ] Raspberry Pi がCSVログを保存できる
[ ] 異常時に RELEASE_OFF へ戻る
[ ] READMEにシステムの説明がある
[ ] 接触パッドと蜂の巣機構の境界をチームが理解できる
```

---

## 一文要約

このプロジェクトでは、Arduino Uno Q を前足接触パッドのメイン制御基板として使い、Raspberry Pi 4B をログ記録・ダッシュボード用デバイスとして使う。最初は疑似入力で安全な蜂蜜放出判定ロジックを検証し、後から実センサーへ置き換える。
