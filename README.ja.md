# A1 Front Paw Contact Pad System

## 概要

このリポジトリは、A1 **Bear Honey Buffet** ハッカソンプロジェクトにおける **Front Paw Contact Pad System** のプロトタイプを扱う。

現在のプロトタイプは、疑似入力・接触パッド制御に加えて、Raspberry Pi のカメラAI認識モジュールを含む。熊または対象物の接近を検知し、前足接触または将来の電気抵抗/接触パッド入力を確認し、蜂蜜量と安全状態を確認したうえで、蜂蜜放出信号を安全に判断する。

カメラAIは追加の認識レイヤーであり、単独の安全制御器ではない。YOLO検出だけで蜂蜜を放出してはいけない。

制御ロジックの初期版は、引き続き **疑似センサー入力** だけでも動作する。従来のArduino/接触パッド系および電気抵抗による接触確認の経路は、リポジトリ内に残し、後で別途統合する。

---

## プロジェクトのビジョン

A1システム全体は、4つのレイヤーに分ける。

```text
[Bear]
  ↓
[Camera AI perception layer]
  ↓ ai_bear_approaching
[Contact / resistance confirmation layer]
  ↓ paw_contact / raw_contact_value
[Safety decision layer]
  ↓ RELEASE_ON / RELEASE_OFF
[Honey release actuator layer]
  ↓
[Honey release mechanism]
```

このリポジトリは、認識、接触確認、安全判定ロジック、ログ記録、デモ支援を対象とする。蜂蜜放出側は、単純な RELEASE_ON/OFF インターフェースと、後続の PCA9685 + サーボ統合として扱う。

---

## このシステムが行うこと

本システムは、以下を確認する。

```text
1. 熊または対象物が接近しているか        ai_bear_approaching / bear_detected
2. 前足が接触パッドに触れているか          paw_contact / raw_contact_value
3. 蜂蜜量は十分か                          honey_amount_percent
4. システムは安全状態か                    system_safe
5. 緊急停止が押されていないか              emergency_stop == false
6. 蜂蜜放出機構を動作させてよいか          RELEASE_ON / RELEASE_OFF
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

Arduino Uno Q は、現場側の接触確認・安全制御基板として残す。

主な役割:

```text
- 接触パッド入力
- 将来の電気抵抗/接触測定
- 疑似センサー入力
- しきい値判定
- 放出判定ロジック
- LED / GPIO / release signal 出力
- serial または network 通信
```

Arduino Uno Q / 電気抵抗測定 / 接触パッドロジックは、今後も削除せず文書と実装に残す。camera AI は `ai_bear_approaching` を追加できるが、`paw_contact`、`raw_contact_value`、接触しきい値、緊急停止、RELEASE_OFF フェイルセーフを置き換えない。

Arduino Uno Q は、Linuxが動作するMPU側とリアルタイム制御用MCU側を持つため、現場制御に適している。

参考:

```text
https://docs.arduino.cc/hardware/uno-q
https://docs.arduino.cc/tutorials/uno-q/user-manual/
```

### Raspberry Pi 4B

Raspberry Pi 4B 4GB は、AIカメラ認識、ログ記録、上位側の状態管理に使用する。

主な役割:

```text
- BUFFALO BSW500M USBカメラから画像を取得
- OpenCV / V4L2 でカメラキャプチャ
- 軽量YOLOで熊接近を検出
- ai_bear_approaching 状態を出力
- Arduino Uno Q から状態データを受信
- CSVログ保存
- ダッシュボード表示
- 最新状態の可視化
- 発表用デモ支援
- SSH / Tailscale などによる遠隔確認
```

Raspberry Pi を唯一の安全制御器にしないこと。カメラAIは追加の認識レイヤーであり、単独の安全制御器ではない。

### BUFFALO BSW500M USBカメラ

BUFFALO BSW500M USB Webカメラを Raspberry Pi 4B に接続する。

```text
- /dev/video0: 実際の映像ストリーム
- /dev/video1: metadata device。画像取得には使わない
- 推奨FourCC: まずMJPG、失敗時にYUYV
- 推奨解像度: まず640x480、失敗時に320x240
```

### PCA9685 + サーボモーター

PCA9685 + サーボモーター + 外部電源は、蜂蜜放出機構側の駆動に使用する。

```text
- 入力: RELEASE_ON / RELEASE_OFF
- 役割: デモ用蜂蜜放出機構のアクチュエータ駆動
- 安全: 無制御の放出は禁止。初期状態は必ず RELEASE_OFF
```

---

## システム構成

```text
Bear / target object
  ↓
BUFFALO BSW500M USB Camera
  ↓
Raspberry Pi 4B 4GB
  - OpenCV / V4L2 camera capture
  - YOLO bear detection
  - bear approach judgement
  - JSON Lines / CSV logging
  ↓
Existing decision logic
  - ai_bear_approaching
  - paw_contact / resistance measurement
  - honey_amount_percent
  - system_safe
  - emergency_stop
  ↓
RELEASE_ON / RELEASE_OFF
  ↓
PCA9685 + Servo Motor
  ↓
Honey release mechanism
```

---

## MVP v0.1

最初のMVPでは、以下を実現する。

### 入力

```text
simulated_bear_detected
ai_bear_approaching
simulated_paw_contact
raw_contact_value
simulated_honey_amount_percent
simulated_system_safe
emergency_stop
```

### ロジック

```text
release_allowed = (
    ai_bear_approaching
    and paw_contact
    and honey_amount_percent >= honey_min_threshold_percent
    and system_safe
    and not emergency_stop
)
```

### 出力

```text
- RELEASE_ON / RELEASE_OFF
- LED ON/OFF
- JSON Lines over serial
- CSV log on Raspberry Pi
- Camera AI JSON Lines / CSV state
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
- カメラAIは追加の認識レイヤーであり、単独の安全制御器ではない
- YOLO検出だけで蜂蜜放出を許可しない
- RELEASE_ON には時間制限を設ける
- 重要な状態変化をログに残す
- 接触パッド制御と蜂の巣機構を分離する
```

蜂蜜放出は、必要条件がすべて満たされた場合にのみ許可する。

```python
release_allowed = (
    ai_bear_approaching
    and paw_contact
    and honey_amount_percent >= honey_min_threshold_percent
    and system_safe
    and not emergency_stop
)
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

Camera AI も Raspberry Pi から JSON Lines を出力する。

```json
{"source":"camera_ai","ai_camera_ok":true,"ai_model_ok":true,"ai_bear_detected":true,"ai_bear_confidence":0.82,"ai_bear_box_area_ratio":0.18,"ai_bear_approaching":true,"event":"AI_BEAR_APPROACHING"}
```

これらの camera AI フィールドは、安全判定レイヤーへの入力であり、直接 `RELEASE_ON` を命令するものではない。

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
│  ├─ interface_spec.md
│  ├─ camera_ai_design.md
│  └─ camera_ai_interface_spec.md
├─ arduino_uno_q/
│  ├─ contact_pad_controller/
│  │  ├─ contact_pad_controller.ino
│  │  └─ config.h
│  └─ README.md
├─ raspberry_pi/
│  ├─ camera_ai/
│  │  ├─ run_camera_ai.py
│  │  ├─ camera_test.py
│  │  ├─ camera_capture.py
│  │  ├─ bear_detector.py
│  │  ├─ approach_logic.py
│  │  └─ config.camera_ai.yaml
│  ├─ logger/
│  │  ├─ serial_logger.py
│  │  └─ requirements.txt
│  ├─ dashboard/
│  │  ├─ app.py
│  │  └─ requirements.txt
│  └─ README.md
├─ data/
│  └─ logs/
├─ models/
│  ├─ yolo_bear_ncnn_model/
│  └─ yolo_bear.pt
├─ outputs/
│  └─ camera_test.jpg
├─ examples/
│  └─ sample_log.csv
└─ scripts/
   └─ run_demo.sh
```

---

`models/` と `outputs/` は実行時・デモ時に使うフォルダである。
モデル重みやカメラ画像は、チームで小さなサンプルを残すと決めた場合を除き、通常はGitに入れない。

---

## Camera AI モジュール

Camera AI モジュールは、Raspberry Pi 4B 4GB と BUFFALO BSW500M USB Webカメラで動作する。

カメラAIは追加の認識レイヤーであり、単独の安全制御器ではない。

ハードウェアと実行時の前提:

```text
- 対象デバイス: Raspberry Pi 4B 4GB
- カメラ: BUFFALO BSW500M USB Webカメラ
- 映像デバイス: /dev/video0
- metadata device: /dev/video1。画像取得には使わない
- 優先モデルパス: models/yolo_bear_ncnn_model
- フォールバックモデルパス: models/yolo_bear.pt
- Raspberry Pi 4B 推奨解像度: 320x240
- 推奨FourCC: まずMJPG、失敗時にYUYV
- 失敗時の挙動: ai_bear_approaching=false
```

設定されたモデルがすべて無い場合、`AI_MODEL_LOAD_ERROR` を出力し、`ai_model_ok=false` としてフェイルセーフを維持する。

Raspberry Pi 4B向けにnano `.pt` モデルを軽量形式へ書き出す:

```bash
python3 raspberry_pi/camera_ai/export_lightweight_yolo.py \
  --source models/yolo_bear.pt \
  --format ncnn \
  --imgsz 256 \
  --overwrite
```

Camera AI 実行コマンド:

```bash
python3 -m compileall -q raspberry_pi/camera_ai
python3 raspberry_pi/camera_ai/camera_test.py --device /dev/video0
python3 -m raspberry_pi.camera_ai.run_camera_ai --terminal-status --no-jsonl --once
```

カメラデバッグコマンド:

```bash
lsusb
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext
fuser -v /dev/video0
```

---

## 各フォルダの担当

| パス | 担当内容 |
|---|---|
| `arduino_uno_q/contact_pad_controller/` | Arduino Uno Q のメイン制御。疑似入力、接触パッド状態遷移、蜂蜜量しきい値判定、RELEASE_ON/OFF出力、LED/GPIO、JSON Lines出力を担当する。 |
| `raspberry_pi/logger/` | Raspberry Pi 側のシリアルロガー。ArduinoとAIのJSON Linesを受信し、CSVログに保存する。 |
| `raspberry_pi/dashboard/` | デモ・監視用ダッシュボード。接触状態、AI状態、放出状態をまとめて表示する。 |
| `raspberry_pi/camera_ai/` | 任意のカメラAI知覚レイヤー。`/dev/video0` のカメラテスト、YOLO読み込み、熊接近推定、AI状態出力を担当する。ただし蜂蜜放出を直接命令してはいけない。 |
| `docs/` | ブロック図、状態遷移図、インターフェース仕様、camera AI設計メモなどの設計資料。 |
| `data/logs/` | 実行時のCSV/JSONLログ置き場。小さなサンプル以外の生成ログは通常Gitに入れない。 |
| `examples/` | デモや説明用の小さなサンプル入出力。 |
| `models/` | ローカルのYOLOモデル重みと書き出し先。優先パスは `models/yolo_bear_ncnn_model`、`.pt` はフォールバック。通常Gitには入れない。 |
| `outputs/` | カメラテスト画像や一時的なデモ出力。通常Gitには入れない。 |
| `scripts/` | デモ実行用の補助スクリプト。 |
| `tests/` | 判定ロジックやcamera AI補助処理のPythonテスト。 |
| ルート直下のファイル | プロジェクト全体の指示、ガードレール、変数一覧、多言語READMEを置く。 |

---

## 開発ロードマップ

### Phase 1: 疑似入力による制御ロジック

```text
[ ] 熊/接触/蜂蜜量/安全状態の疑似入力
[ ] RELEASE_ON/OFF 判定ロジック
[ ] 緊急停止と RELEASE_OFF フェイルセーフ
[ ] JSON Lines 出力
```

### Phase 2: Raspberry Pi カメラ単体テスト

```text
[ ] BUFFALO BSW500M を Raspberry Pi 4B に接続
[ ] /dev/video0 が映像ストリームであることを確認
[ ] /dev/video1 は画像取得に使わない
[ ] camera_test.py で1フレーム取得
```

### Phase 3: YOLOモデル配置とAI推論

```text
[ ] models/yolo_bear_ncnn_model を配置または書き出し
[ ] AI_MODEL_LOAD_ERROR が消えることを確認
[ ] カメラ画像に対してYOLO推論を実行
[ ] ai_bear_approaching をフェイルセーフに出力
```

### Phase 4: AI状態ログとダッシュボード統合

```text
[ ] camera AI JSON Lines / CSV を記録
[ ] ai_camera_ok と ai_model_ok を表示
[ ] ai_bear_detected と ai_bear_approaching を表示
[ ] 接触状態と放出状態を同じ画面に表示
```

### Phase 5: 抵抗/接触パッド統合

```text
[ ] Arduino Uno Q の接触パッドロジックを維持
[ ] raw_contact_value を追加または検証
[ ] 接触しきい値ロジックを追加
[ ] 安全なダミー物体でのみ試験
```

### Phase 6: PCA9685 / サーボ蜂蜜放出統合

```text
[ ] PCA9685 と外部サーボ電源を接続
[ ] RELEASE_ON/OFF を安全なサーボ動作に対応
[ ] 放出タイムアウトとクールダウンを追加
[ ] リセット時・異常時に RELEASE_OFF になることを確認
```

### Phase 7: フェイルセーフ付き全体デモ

```text
[ ] Camera AI が接近を検出
[ ] 接触/抵抗レイヤーが paw_contact を確認
[ ] 蜂蜜量と安全状態の条件を満たす
[ ] 緊急停止で RELEASE_OFF に強制移行
[ ] YOLO検出だけでは蜂蜜を放出しない
```

---

## チームへの説明文

```text
I will develop the front paw contact pad system as a separate electronic/control module.
Raspberry Pi 4B with a BUFFALO BSW500M camera will be used for YOLO-based bear approach detection, logging, and dashboard support.
Arduino Uno Q and the contact/resistance layer remain responsible for contact confirmation and fail-safe release logic.
PCA9685 and a servo motor will be used on the honey release mechanism side.
Camera AI is an additional perception layer, not the only safety controller.
```

---

## 現在の仮定

```text
- 蜂の巣機構側は単純な RELEASE_ON/OFF 信号を受け取れる
- Raspberry Pi 4B は BUFFALO BSW500M の /dev/video0 を画像取得に使う
- /dev/video1 はmetadataであり、画像取得には使わない
- 物理的な接触/抵抗統合は camera AI とは別に残す
- PCA9685 + サーボモーター + 外部電源をアクチュエータ側で使う
- 実動物による試験は行わない
- このプロジェクトはハッカソン用の概念検証である
```

---

## MVP v0.1 完了条件

```text
[ ] Uno Q が疑似入力を生成できる
[ ] Uno Q が RELEASE_ON/OFF を判断できる
[ ] Raspberry Pi が /dev/video0 から画像取得できる
[ ] Camera AI がフェイルセーフな ai_bear_approaching を出力できる
[ ] LEDまたはserialで RELEASE_ON/OFF が見える
[ ] Raspberry Pi が状態データを受信できる
[ ] Raspberry Pi がCSVログを保存できる
[ ] 異常時に RELEASE_OFF へ戻る
[ ] YOLO検出だけでは蜂蜜を放出できない
[ ] READMEにシステムの説明がある
[ ] 接触パッドと蜂の巣機構の境界をチームが理解できる
```

---

## はじめ方（MVPシミュレーション）

このプロトタイプは **疑似センサー入力** だけでも動作する。実センサーがなくても制御ロジックを確認できる。

### Arduino Uno Q

1. `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino` を開く。
2. Arduino Uno Q にビルド・書き込みを行う。
3. シリアルモニタを **115200 baud** で開く。
4. JSON Lines 出力を確認する。

### Raspberry Pi ロガー

1. 依存関係をインストールする。
   ```bash
   pip install -r raspberry_pi/logger/requirements.txt
   ```
2. ロガーを実行する。
   ```bash
   python raspberry_pi/logger/serial_logger.py --serial-port /dev/ttyACM0 --baudrate 115200
   ```
3. CSVログは `data/logs/` に保存される。

### Raspberry Pi Camera AI

1. 軽量YOLOモデルを `models/yolo_bear_ncnn_model` に配置または書き出す。
2. カメラを確認する。
   ```bash
   python3 raspberry_pi/camera_ai/camera_test.py --device /dev/video0
   ```
3. AIを1回だけ実行する。
   ```bash
   python3 -m raspberry_pi.camera_ai.run_camera_ai --terminal-status --no-jsonl --once
   ```

### Raspberry Pi ダッシュボード

1. 依存関係をインストールする。
   ```bash
   pip install -r raspberry_pi/dashboard/requirements.txt
   ```
2. ダッシュボードを起動する。
   ```bash
   python raspberry_pi/dashboard/app.py --log-dir data/logs --host 0.0.0.0 --port 8080
   ```
3. `http://<pi-ip>:8080` を開き、最新状態を確認する。

---

## データ形式メモ

- Arduino Uno Q は **JSON Lines** を送信する。
- Camera AI も **JSON Lines** を送信する。
- Raspberry Pi は **CSVログ** を保存する。
- `timestamp` はリアルタイムクロック追加前は **uptime** (`T+<ms>`) として扱う。
- 詳細スキーマは `docs/interface_spec.md` と `docs/camera_ai_interface_spec.md` を参照する。

---

## 一文要約

このプロジェクトでは、Raspberry Pi 4B と BUFFALO BSW500M USBカメラを用いてYOLOによる熊接近検出を行い、従来のArduino/接触パッド系の安全判定を残したまま、AI検知・接触確認・蜂蜜量・安全状態を満たした場合のみ蜂蜜放出を許可する。
