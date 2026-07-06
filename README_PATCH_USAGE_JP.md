# 郷田さんコード統合パッケージの使い方

このフォルダは、`CYLIU2003/2026_Hackathon` に追加するための統合用ファイル一式です。

## 1. 追加先

リポジトリ直下で、このフォルダ内のファイルを同じ階層にコピーしてください。

```text
2026_Hackathon/
├─ docs/GODA_ACTUATOR_INTEGRATION_INSTRUCTIONS_JP.md
├─ arduino_uno_q/actuator_standalone/actuator_standalone.ino
├─ arduino_uno_q/contact_pad_controller/GODA_PATCH_NOTES.md
├─ raspberry_pi/integration/fake_bear_to_actuator.py
├─ raspberry_pi/test_tools/fake_camera_ai_jsonl.py
└─ scripts/run_fake_bear_actuator_demo.sh
```

## 2. まず読むファイル

```text
docs/GODA_ACTUATOR_INTEGRATION_INSTRUCTIONS_JP.md
```

このファイルに、郷田さんのコードをどう変更して、現在の状態機械へどう接続するかをまとめています。

## 3. Arduinoで確認するファイル

**メインスケッチ（通常はこちらを使ってください）**:

```text
arduino_uno_q/contact_pad_controller/contact_pad_controller.ino
```

Arduino IDEで `contact_pad_controller` フォルダを開いてください。

**スタンドアロン版（config.h 無しで単体動作、参照用）**:

```text
arduino_uno_q/actuator_standalone/actuator_standalone.ino
```

Arduino IDEで `actuator_standalone` フォルダを開いてください。

必要ライブラリ:

```text
Adafruit PWM Servo Driver Library
```

## 4. ラズパイ無しでテストする方法

### Arduino単体テスト

統合版スケッチは、初期状態で `auto_test_mode = true` です。  
Arduinoに書き込むだけで、仮想熊検知→仮想接触→RELEASING→サーボOPEN→CLOSE の流れを確認できます。

### PCを仮想Raspberry Piにする

```bash
python raspberry_pi/integration/fake_bear_to_actuator.py --port COM3 --loop
```

Linux / Raspberry Pi:

```bash
python3 raspberry_pi/integration/fake_bear_to_actuator.py --port /dev/ttyACM0 --loop
```

シリアル無しでJSONだけ見る場合:

```bash
python3 raspberry_pi/integration/fake_bear_to_actuator.py --no-serial --loop
```

## 5. 実YOLOへ差し替えるとき

最終的には `fake_bear_to_actuator.py` の仮想 `ai_bear_detected` を、既存の `raspberry_pi/camera_ai/run_camera_ai.py` の出力へ置き換えます。

ただし、YOLO単独でサーボを開いてはいけません。  
Arduino側の接触確認、安全確認、蜂蜜量確認、非常停止確認を必ず通してください。
