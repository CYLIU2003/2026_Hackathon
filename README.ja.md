# A1 Front Paw Contact Pad System

## 概要

このリポジトリは、A1 **Bear Honey Buffet** ハッカソンプロジェクトにおける **Front Paw Contact Pad System** のプロトタイプを扱う。

現在のプロトタイプは、疑似入力・接触パッド制御に加えて、Raspberry Pi のカメラAI認識モジュールを含む。熊または対象物の存在を検知し、前足接触または将来の電気抵抗/接触パッド入力を確認し、蜂蜜量と安全状態を確認したうえで、蜂蜜放出信号を安全に判断する。

カメラAIは追加の認識レイヤーであり、単独の安全制御器ではない。YOLO検出だけで蜂蜜を放出してはいけない。

制御ロジックの初期版は、引き続き **疑似センサー入力** だけでも動作する。従来のArduino/接触パッド系および電気抵抗による接触確認の経路は、リポジトリ内に残し、後で別途統合する。

---

## プロジェクトのビジョン

A1システム全体は、4つのレイヤーに分ける。

```text
[Bear]
  ↓
[Camera AI perception layer]
  ↓ ai_bear_detected
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
1. 熊または対象物を検知しているか        ai_bear_detected / bear_detected
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

### Arduino Uno

Arduino Uno は、現場側の接触確認・安全制御基板として残す。

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

Arduino Uno / 電気抵抗測定 / 接触パッドロジックは、今後も削除せず文書と実装に残す。camera AI は `ai_bear_detected` を追加できるが、`paw_contact`、`raw_contact_value`、接触しきい値、緊急停止、RELEASE_OFF フェイルセーフを置き換えない。

Arduino Uno は、低レイテンシなGPIO制御とUSBシリアル通信により、現場側のフェイルセーフ制御に使う。

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
- 軽量YOLOで熊を検出
- ai_bear_detected 状態を出力
- Arduino Uno から状態データを受信
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
- USB ID: 0411:02da
- /dev/video0: 実際の映像ストリーム
- /dev/video1: metadata device。画像取得には使わない
- 既定設定: device=auto。0411:02da の Video Capture ノードを優先し、metadata ノードは避ける
- OpenCV が /dev/video0 のパス名で開けない場合は、同じノードの index 0 に自動フォールバックする
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
  - bear detection judgement
  - JSON Lines / CSV logging
  ↓
Existing decision logic
  - ai_bear_detected
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
ai_bear_detected
simulated_paw_contact
raw_contact_value
simulated_honey_amount_percent
simulated_system_safe
emergency_stop
```

### ロジック

```text
release_allowed = (
    ai_bear_detected
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
    ai_bear_detected
    and paw_contact
    and honey_amount_percent >= honey_min_threshold_percent
    and system_safe
    and not emergency_stop
)
```

---

## データ形式

Arduino Uno から Raspberry Pi へは JSON Lines を送信する。

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
{"source":"camera_ai","ai_camera_ok":true,"ai_model_ok":true,"ai_bear_detected":true,"ai_bear_confidence":0.82,"ai_bear_box_area_ratio":0.18,"event":"AI_BEAR_DETECTED"}
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
遠隔ブラウザ画面は監視・デモ支援用であり、RELEASE_ON/OFF の安全判定を
Arduino/contact-pad 側から移動するものではない。

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
- 失敗時の挙動: ai_bear_detected=false
```

設定されたモデルがすべて無い場合、`AI_MODEL_LOAD_ERROR` を出力し、`ai_model_ok=false` としてフェイルセーフを維持する。

遠隔監視の動作:

```text
Camera AI process
  -> CSV保存: data/logs/camera_ai_log.csv
  -> 最新の認識済み画像保存: data/debug_frames/latest_camera_ai.jpg
Dashboard process
  -> ブラウザ画面: http://<pi-ip>:8080
  -> 最新画像: /camera/latest.jpg
```

Raspberry Pi の立ち上げ確認では、`.pt` の PyTorch フォールバックが
`YOLO.predict()` 実行時に `Illegal instruction` で落ちた。`ncnn` を入れて
`models/yolo_bear_ncnn_model` を使う経路では起動・推論が通ったため、Pi の
デモでは NCNN モデルを通常の実行経路として使う。

もし現在の Pi 環境の `ncnn` ランタイム（例: `ncnn==1.0.20260526` の aarch64
ビルド）が `extract("out0")` で SIGSEGV し、Camera AI が即死して画面が最後の
フレームで止まる場合は、Pi 側に PyTorch を入れずに Colab で `.pt` を ONNX に
書き出し、`models/yolo_bear.onnx` を置くだけで Camera AI は自動的に
ONNX Runtime の推論経路を優先する（NCNN 不要 / Pi 上の PyTorch・Ultralytics
インストール不要）。
そのため Raspberry Pi 実行用の `raspberry_pi/camera_ai/requirements.txt` は
`onnxruntime` を含めるが、PyTorch と Ultralytics は含めない。学習・書き出し作業だけ、Colab または開発PCで
`raspberry_pi/camera_ai/requirements.export.txt` を使う。

ONNX 書き出し手順（Colab で実行し、Pi は runtime requirements のみ）:

```text
1. notebooks/export_bear_yolo_onnx.ipynb を開く
2. リポジトリの best.pt をアップロード
3. すべてのセルを実行し models/yolo_bear.onnx を書き出す
   (imgsz=256, opset 18。opset 12 は変換成功時のみ)
4. yolo_bear.onnx をダウンロードし、Pi の models/yolo_bear.onnx に配置
5. Pi で ./scripts/run_demo.sh を再起動
6. ai_model_ok=true であり、画面が更新され続けることを確認
```

`models/yolo_bear.onnx` が存在するとき、`scripts/run_demo.sh` は既定で
推論を有効にする（`RUN_CAMERA_AI_INFERENCE` が自動的に 1）。ONNX がないときは
既定でカメラのみフェイルセーフモード（`ai_model_ok=false`・HOLD を維持・
画面は更新され続ける）になる。
`scripts/run_demo.sh` の既定は `CAMERA_DEVICE=auto` で、BUFFALO BSW500M の
Video Capture ノードを選ぶ。会場で固定したい場合は
`CAMERA_DEVICE=/dev/video0 ./scripts/run_demo.sh` を使う。

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
python3 raspberry_pi/camera_ai/camera_test.py --device auto
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
| `arduino_uno_q/contact_pad_controller/` | Arduino Uno のメイン制御。疑似入力、接触パッド状態遷移、蜂蜜量しきい値判定、RELEASE_ON/OFF出力、LED/GPIO、JSON Lines出力を担当する。 |
| `raspberry_pi/logger/` | Raspberry Pi 側のシリアルロガー。ArduinoとAIのJSON Linesを受信し、CSVログに保存する。 |
| `raspberry_pi/dashboard/` | デモ・監視用ダッシュボード。接触状態、AI状態、放出状態をまとめて表示する。 |
| `raspberry_pi/camera_ai/` | 任意のカメラAI知覚レイヤー。`/dev/video0` のカメラテスト、YOLO読み込み、熊検出、AI状態出力を担当する。ただし蜂蜜放出を直接命令してはいけない。 |
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
[ ] ai_bear_detected をフェイルセーフに出力
```

### Phase 4: AI状態ログとダッシュボード統合

```text
[ ] camera AI JSON Lines / CSV を記録
[ ] ai_camera_ok と ai_model_ok を表示
[ ] ai_camera_ok、ai_model_ok、ai_bear_detected を表示
[ ] 接触状態と放出状態を同じ画面に表示
```

### Phase 5: 抵抗/接触パッド統合

```text
[ ] Arduino Uno の接触パッドロジックを維持
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
[ ] Camera AI が熊を検出
[ ] 接触/抵抗レイヤーが paw_contact を確認
[ ] 蜂蜜量と安全状態の条件を満たす
[ ] 緊急停止で RELEASE_OFF に強制移行
[ ] YOLO検出だけでは蜂蜜を放出しない
```

---

## チームへの説明文

```text
I will develop the front paw contact pad system as a separate electronic/control module.
Raspberry Pi 4B with a BUFFALO BSW500M camera will be used for YOLO-based bear detection, logging, and dashboard support.
Arduino Uno and the contact/resistance layer remain responsible for contact confirmation and fail-safe release logic.
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
[ ] Uno が疑似入力を生成できる
[ ] Uno が RELEASE_ON/OFF を判断できる
[ ] Raspberry Pi が /dev/video0 から画像取得できる
[ ] Camera AI がフェイルセーフな ai_bear_detected を出力できる
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

### Arduino Uno

1. `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino` を開く。
2. Arduino IDEで **Arduino Uno** を選択し、ビルド・書き込みを行う。
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

Raspberry Pi 上で、リポジトリ直下から実行する。

```bash
cd ~/Desktop/2026_Hackathon
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/camera_ai/requirements.txt
python -m pip install -r raspberry_pi/dashboard/requirements.txt
```

Camera AI の実行用インストールは ONNX/NCNN 前提であり、Raspberry Pi 上では
PyTorch/Ultralytics を意図的に入れない。

通常のデモ起動。Camera AI と遠隔ダッシュボードをまとめて起動する。

```bash
./scripts/run_demo.sh
```

会場で、実カメラ推論から Arduino 機構動作まで一通り動かす場合:

```bash
RUN_CAMERA_AI_INFERENCE=1 RUN_ACTUATOR_BRIDGE=1 ./scripts/run_demo.sh
```

ブリッジは新しい安全CSV行が `RELEASE_ON` の時だけ Arduino に `RELEASE` を送る。
欠損・古いログ・エラー時は `STOP` 側を維持する。

同じネットワーク上のPC、タブレット、スマートフォン、または Tailscale 経由で開く。

```text
http://<pi-ip>:8080
```

ダッシュボードには、Camera AI の最新認識画像、AI状態、contact-pad状態が表示される。
Camera AI が保存する画像は以下。

```text
data/debug_frames/latest_camera_ai.jpg
```

ダッシュボード無しで Camera AI だけ起動する場合:

```bash
python -m raspberry_pi.camera_ai.run_camera_ai \
  --device auto \
  --terminal-status \
  --no-jsonl \
  --save-debug-frames
```

1回だけ動かすスモークテスト:

```bash
python -m raspberry_pi.camera_ai.run_camera_ai \
  --device auto \
  --terminal-status \
  --no-jsonl \
  --once \
  --save-debug-frames
```

カメラ単体確認:

```bash
python3 raspberry_pi/camera_ai/camera_test.py --device auto
```

### Raspberry Pi ダッシュボード

Camera AI が既に動いていて `data/debug_frames/latest_camera_ai.jpg` を書いている場合だけ、
ダッシュボード単体を起動する。

```bash
python raspberry_pi/dashboard/app.py \
  --log-dir data/logs \
  --camera-log-file data/logs/camera_ai_log.csv \
  --debug-frame-dir data/debug_frames \
  --host 0.0.0.0 \
  --port 8080
```

開くURL:

```text
http://<pi-ip>:8080
```

フルデモ時に Arduino Uno のシリアルロガーも同時に起動する場合:

```bash
RUN_SERIAL_LOGGER=1 ./scripts/run_demo.sh
```

8080番ポートが既に使われている場合:

```bash
DASHBOARD_PORT=18080 ./scripts/run_demo.sh
```

今回の立ち上げ確認で通した内容:

```text
- Camera AI が models/yolo_bear_ncnn_model を NCNN 経由で読み込む。
- data/debug_frames/latest_camera_ai.jpg が生成される。
- Dashboard / が HTTP 200 を返す。
- Dashboard /camera/latest.jpg が HTTP 200 image/jpeg を返す。
- デモ停止後、Camera AI と dashboard のプロセスが残らない。
```

---

## デモモード（遠隔アクチュエータ制御）

ダッシュボードには、プレゼンテーション時に安全に遠隔操作するための
**デモモード** パネルが組み込まれている。Raspberry Pi 経由で
Arduino 接続のサーボ/機構に手動コマンドを送信できる。

### アーキテクチャ

```text
Dashboard (ブラウザ)
  ↓ Tailscale / LAN
Raspberry Pi 4B (ダッシュボードバックエンド)
  ↓ USBシリアル (有線)
Arduino Uno Q
  ↓ GPIO / PCA9685
サーボ / 蜂蜜放出機構
```

- 無線/遠隔部分は Dashboard → Raspberry Pi 間 **のみ**（Tailscale または LAN 経由）。
- Raspberry Pi → Arduino 間は安定性のため **有線USBシリアル** のまま。
- ダッシュボードが直接 Arduino と通信することはない。

### クイックスタート

フルデモ（Camera AI + 安全制御 + ダッシュボード）を起動:

```bash
./scripts/run_demo.sh
```

ハードウェアテスト用にダッシュボード単体をデモモード付きで起動:

```bash
python raspberry_pi/dashboard/app.py \
  --log-dir data/logs \
  --log-file data/logs/feeding_decision_log.csv \
  --camera-log-file data/logs/camera_ai_log.csv \
  --debug-frame-dir data/debug_frames \
  --demo-serial-port /dev/ttyACM0 \
  --demo-baudrate 115200 \
  --demo-command-log-file data/logs/demo_commands.csv \
  --host 0.0.0.0 \
  --port 8080
```

同じ Tailscale ネットワーク上のブラウザから `http://<pi-ip>:8080` を開く。

### 使い方

1. ダッシュボードを開く。デモモードパネルはデフォルトで **DISABLED** と表示される。
2. **Enable Demo Mode** をクリックして手動操作を有効にする。
3. 操作ボタンを使う:
   - **Release / Open** — Arduino に `RELEASE` を送信（デモモード有効時のみ）
   - **Stop / Close** — Arduino に `STOP` を送信（常に使用可能）
   - **Test Motion** — Arduino に `TEST` を送信（デモモード有効時のみ）
   - **Emergency Stop** — 即座に `STOP` を送信し、デモモードを無効化、操作をロック
4. ステータステーブルに以下が表示される:
   - 最後に送信したコマンド
   - コマンド送信時刻
   - シリアル接続状態（`CONNECTED` / `SIMULATION_MODE` / `ERROR`）
   - 結果（`SENT` / `SIMULATED` / `BLOCKED` / `ERROR`）
   - メッセージ

### 安全動作

- デフォルト状態は **STOP / 閉**。
- `Release` または `Test` コマンドを送信するには、事前にデモモードを手動で有効にする必要がある。
- `Stop / Close` と `Emergency Stop` は **常に** 使用可能。
- Emergency Stop は即座に `STOP` を送信し、デモモードを無効化する。
- シリアル通信エラー時は、ハードウェアを制御せず **シミュレーションモード** に自動フォールバックする。

### シミュレーションモード（ハードウェア無しのリハーサル）

Arduino が接続されていない、またはシリアルポートが利用できない場合、
ダッシュボードは自動的にシミュレーションモードで動作する:

```bash
# 自動フォールバック — Arduino 非接続のまま実行
python raspberry_pi/dashboard/app.py --host 0.0.0.0 --port 8080

# 明示的にシミュレーションモードを強制
python raspberry_pi/dashboard/app.py --demo-force-simulation --host 0.0.0.0 --port 8080
```

シミュレーションモードでは:
- UI 上のすべてのボタンが通常通り動作する。
- コマンドは `data/logs/demo_commands.csv` に記録される。
- ハードウェアへのシリアルデータ送信は行わない。
- ステータスに `SIMULATION_MODE` と表示される。

### API エンドポイント

ダッシュボードバックエンドは、デモモード用に以下の REST エンドポイントを提供する:

| エンドポイント | メソッド | 説明 |
|---|---|---|
| `/api/demo-mode` | POST | デモモードの有効/無効 (`{"enabled": true/false}`) |
| `/api/demo-command` | POST | 汎用コマンド送信 (`{"command": "RELEASE"}`) |
| `/api/demo/release` | POST | RELEASE コマンド送信 |
| `/api/demo/stop` | POST | STOP コマンド送信 |
| `/api/demo/test` | POST | TEST コマンド送信 |
| `/api/demo/emergency-stop` | POST | EMERGENCY_STOP コマンド送信 |
| `/api/demo-status` | GET | 現在のデモステータス取得 |

すべてのエンドポイントは `Accept: application/json` または
`Content-Type: application/json` で呼び出された場合に JSON を返す。
ブラウザUIからは HTML form POST で送信し、ダッシュボードにリダイレクトする。

### シリアルコマンド

Raspberry Pi は USB シリアル経由で以下の単純な文字列コマンドを Arduino に送信する:

| コマンド | シリアル文字列 | 説明 |
|---|---|---|
| Release / Open | `RELEASE\n` | 蜂蜜放出機構を作動 |
| Stop / Close | `STOP\n` | 機構を停止（安全デフォルト） |
| Test Motion | `TEST\n` | 短いテスト動作を実行 |
| Emergency Stop | `STOP\n` | STOP と同じ、デモモードも無効化 |

### コマンドログ

すべてのデモコマンドは CSV に記録される:

```text
data/logs/demo_commands.csv
```

CSVカラム: `timestamp`, `command`, `serial_command`, `demo_enabled`,
`serial_status`, `result`, `message`, `emergency_stop`

### CLI オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--demo-serial-port` | `/dev/ttyACM0` | Arduino接続のシリアルポート |
| `--demo-baudrate` | `115200` | シリアル通信ボーレート |
| `--demo-command-log-file` | `data/logs/demo_commands.csv` | デモコマンドCSVログのパス |
| `--demo-serial-timeout` | `1.0` | シリアル書き込みタイムアウト（秒） |
| `--demo-serial-reset-delay` | `2.0` | シリアルポートオープン後の待機時間（秒） |
| `--demo-force-simulation` | (off) | シリアルポートが存在してもシミュレーションモードを強制 |

---

## データ形式メモ

- Arduino Uno は **JSON Lines** を送信する。
- Camera AI も **JSON Lines** を送信する。
- Raspberry Pi は **CSVログ** を保存する。
- `timestamp` はリアルタイムクロック追加前は **uptime** (`T+<ms>`) として扱う。
- 詳細スキーマは `docs/interface_spec.md` と `docs/camera_ai_interface_spec.md` を参照する。

---

## 一文要約

このプロジェクトでは、Raspberry Pi 4B と BUFFALO BSW500M USBカメラを用いてYOLOによる熊検出を行い、従来のArduino/接触パッド系の安全判定を残したまま、AI検知・接触確認・蜂蜜量・安全状態を満たした場合のみ蜂蜜放出を許可する。
