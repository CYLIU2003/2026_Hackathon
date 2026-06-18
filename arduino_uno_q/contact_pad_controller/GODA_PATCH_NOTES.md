# 郷田さんPCA9685サーボコード統合メモ

## 変更してよい点

郷田さんの元コードは、PCA9685 + サーボの単体テスト用です。統合のため、以下の変更を行ってください。

- 先頭の `C++` という行を削除する
- `loop()` 内でサーボを0〜180度往復させる処理を削除する
- `openReleaseGate()` / `closeReleaseGate()` の関数形式に変更する
- 既存の `contact_pad_controller` の `update_outputs()` から呼び出す
- `RELEASING` の間だけOPEN、それ以外は必ずCLOSEにする

## 統合先

推奨統合先:

```text
arduino_uno_q/contact_pad_controller/contact_pad_controller.ino
```

差し替え確認用（スタンドアロン参照版）:

```text
arduino_uno_q/actuator_standalone/actuator_standalone.ino
```

## 必要ライブラリ

Arduino IDEのライブラリマネージャで以下を入れてください。

```text
Adafruit PWM Servo Driver Library
```

依存で `Adafruit BusIO` が必要な場合は同時に入れてください。
