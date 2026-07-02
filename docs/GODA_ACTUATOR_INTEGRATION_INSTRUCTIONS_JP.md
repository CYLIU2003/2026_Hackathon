# 郷田さん担当コードのシステム統合指示書

対象リポジトリ: `CYLIU2003/2026_Hackathon`  
対象範囲: A1 Front Paw Contact Pad System + Honey Release Actuator  
作成日: 2026-06-18

---

## 1. この指示書の目的

郷田さんから共有されたPCA9685 + サーボモーター制御コードを、現在のA1システムに安全に組み込むための作業指示をまとめる。

現在のシステムは、以下のように役割が分かれている。

```text
[熊・対象物]
  ↓
[Raspberry Pi / Camera AI]
  - YOLOまたは仮想AIで熊接近を判定
  - ai_bear_approaching を出力
  ↓
[Arduino Uno Q / Contact Pad Controller]
  - 前足接触・抵抗確認
  - 蜂蜜残量
  - 安全状態
  - emergency_stop
  - RELEASE_ON / RELEASE_OFF 判定
  ↓
[PCA9685 + Servo Motor]
  - 郷田さん担当のハチミツ放出機構
```

郷田さんの元コードは、**PCA9685経由でサーボを0〜180度まで往復させる単体テストコード**である。  
統合後は、サーボを常時往復させるのではなく、既存システムの安全判定で `RELEASE_ON` になったときだけ動かす。

---

## 2. 結論：郷田さんのコードは変更してよい

統合のため、郷田さんのコードは変更してよい。

ただし、変更の目的は次の3点に限定する。

1. **単体テスト用の無限往復動作を停止する**
2. **既存の状態機械から呼び出せる関数形式に分解する**
3. **起動時・異常時・待機時は必ず閉状態に戻す**

変更前の考え方:

```cpp
void loop() {
  0度から180度へ動かす;
  180度から0度へ戻す;
  これを永久に繰り返す;
}
```

変更後の考え方:

```cpp
void update_outputs() {
  if (state == RELEASING) {
    openReleaseGate();
  } else {
    closeReleaseGate();
  }
}
```

---

## 3. 追加・変更するファイル

以下の構成で追加する。

```text
2026_Hackathon/
├─ docs/
│  └─ GODA_ACTUATOR_INTEGRATION_INSTRUCTIONS_JP.md
│
├─ arduino_uno_q/
│  ├─ actuator_standalone/
│  │  └─ actuator_standalone.ino                       # スタンドアロン参照版（config.h無しで単体動作）
│  └─ contact_pad_controller/
│     ├─ contact_pad_controller.ino                    # 統合版（メイン）
│     ├─ config.h                                      # 既存。必要ならサーボ設定を追記
│     └─ GODA_PATCH_NOTES.md                           # Arduino側変更メモ
│
├─ raspberry_pi/
│  ├─ integration/
│  │  └─ fake_bear_to_actuator.py                      # 仮想ラズパイAI + Arduino制御テスト
│  └─ test_tools/
│     └─ fake_camera_ai_jsonl.py                       # JSON Linesのみ出す仮想Camera AI
│
└─ scripts/
   └─ run_fake_bear_actuator_demo.sh
```

---

## 4. 既存システムとの接続方針

### 4.1 現在の安全判定を壊さない

現在のリポジトリでは、Arduino側の `contact_pad_controller` がMVP状態機械を持ち、`RELEASE_ON / RELEASE_OFF` を出力する設計になっている。  
そのため、郷田さんのPCA9685コードは **RELEASE_ON/OFFの後段** に入れる。

禁止する実装:

```text
Camera AIが熊を検出したら、直接サーボを開く
```

採用する実装:

```text
Camera AIが熊を検出
  AND 前足接触確認
  AND 蜂蜜量OK
  AND system_safe=true
  AND emergency_stop=false
↓
Arduino状態機械が RELEASING へ遷移
↓
PCA9685経由でサーボをOPEN角へ移動
```

---

## 5. Arduino側の改修指示

### 5.1 郷田さんコードから残す部分

残すもの:

```cpp
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVOMIN 150
#define SERVOMAX 500
uint8_t servoNum = 0;

int angleToPulse(int angle) {
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}
```

ただし、`C++` という行はArduino IDEではコンパイルエラーになるため削除する。

### 5.2 変更する部分

元コードの `loop()` 内にある往復処理は削除する。

削除対象:

```cpp
for (int angle = 0; angle <= 180; angle += 10) {
  pwm.setPWM(servoNum, 0, angleToPulse(angle));
  delay(30);
}
...
for (int angle = 180; angle >= 0; angle -= 10) {
  pwm.setPWM(servoNum, 0, angleToPulse(angle));
  delay(30);
}
```

代わりに、以下の関数に分ける。

```cpp
void initReleaseActuator();
void openReleaseGate();
void closeReleaseGate();
void moveServoSmooth(int fromAngle, int toAngle);
```

---

## 6. サーボ角度の初期値

最初は安全側で以下とする。

```cpp
const int SERVO_CLOSED_ANGLE = 0;
const int SERVO_OPEN_ANGLE = 90;
```

理由:

- 180度まで動かすと機構に干渉する可能性がある
- まず90度程度で機構の可動範囲を見る
- 実機に合わせて `SERVO_OPEN_ANGLE` を少しずつ調整する

実機調整後に、例えば以下のように変更してよい。

```cpp
const int SERVO_CLOSED_ANGLE = 20;
const int SERVO_OPEN_ANGLE = 110;
```

---

## 7. ラズパイが無い場合のテストモード

郷田さんの手元にRaspberry Piが無い可能性があるため、以下の2種類のテストモードを用意する。

### 7.1 Arduino単体テストモード

Arduinoに統合版スケッチを書き込むだけで、内部の仮想入力が次のように変化する。

```text
IDLE
↓
仮想熊検知
↓
仮想前足接触
↓
蜂蜜量OK・安全OK
↓
RELEASING
↓
サーボOPEN
↓
一定時間後にCLOSE
```

このモードではRaspberry Piは不要。

### 7.2 PCを仮想Raspberry Piとして使うテストモード

`raspberry_pi/integration/fake_bear_to_actuator.py` をWindows / macOS / Linux上で実行する。  
このPythonスクリプトは、仮のCamera AIが熊を検知しているように振る舞い、Arduinoへシリアル命令を送る。

実行例:

```bash
python raspberry_pi/integration/fake_bear_to_actuator.py --port COM3 --loop
```

Raspberry Pi上で実行する場合:

```bash
python3 raspberry_pi/integration/fake_bear_to_actuator.py --port /dev/ttyACM0 --loop
```

シリアル接続なしでJSON Linesだけ確認する場合:

```bash
python3 raspberry_pi/integration/fake_bear_to_actuator.py --no-serial --loop
```

---

## 8. Arduinoが受け付けるシリアルコマンド

統合版では、Arduinoに以下のコマンドを追加する。

| コマンド | 意味 |
|---|---|
| `RELEASE` | Raspberry Pi ダッシュボード Demo Mode からの開動作要求 |
| `STOP` | Raspberry Pi ダッシュボード Demo Mode からの閉動作要求 |
| `TEST` | Raspberry Pi ダッシュボード Demo Mode からのテスト動作要求 |
| `RESET` | ERROR_SAFEから復帰 |
| `TEST_AUTO_ON` | Arduino内部の自動シミュレーションをON |
| `TEST_AUTO_OFF` | Arduino内部の自動シミュレーションをOFF |
| `SET AI_BEAR 1` | 仮想Camera AIが熊検知中 |
| `SET AI_BEAR 0` | 熊検知なし |
| `SET PAW 1` | 前足接触あり |
| `SET PAW 0` | 前足接触なし |
| `SET HONEY 80` | 蜂蜜量80% |
| `SET SAFE 1` | 安全状態OK |
| `SET SAFE 0` | 安全状態NG |
| `SET ESTOP 1` | 非常停止ON |
| `SET ESTOP 0` | 非常停止OFF |
| `STATUS` | 現在状態をJSONで出力 |

重要: `SET AI_BEAR 1` だけではサーボは動かない。  
`SET PAW 1`, `SET HONEY 80`, `SET SAFE 1`, `SET ESTOP 0` も満たしたときだけ `RELEASING` に入る。
`RELEASE` と `TEST` はデモ用の模擬入力ショートカットであり、`ERROR_SAFE`
を解除しない。エラー復帰は `RESET` だけで行う。

---

## 9. 動作確認手順

### Step 1: 郷田さんの元コード単体確認

目的: PCA9685とMG996Rの配線・ライブラリ・電源を確認する。

- Arduino IDEでAdafruit PWM Servo Driver Libraryをインストール
- PCA9685のI2C接続確認
- MG996RをPCA9685のCH0へ接続
- 外部5〜6V電源をPCA9685のV+へ接続
- Arduino GND / PCA9685 GND / 外部電源GNDを共通化

この段階では、サーボが動くかだけ確認する。

### Step 2: 統合版Arduinoスケッチに置換

`arduino_uno_q/contact_pad_controller/contact_pad_controller.ino` をArduino IDEで開き、書き込む。

確認すること:

- 起動直後にサーボが閉状態へ移動する
- Serial MonitorにJSON Linesが出る
- RELEASE_OFFの間はサーボが閉状態を維持する
- RELEASE_ON / RELEASINGになった時だけ開く

### Step 3: Arduino単体の自動テスト

Serial Monitorで以下を送る。

```text
TEST_AUTO_ON
```

期待動作:

- 数秒後に仮想熊検知
- その後に仮想前足接触
- `state` が `RELEASING` に入る
- サーボがOPEN角へ移動
- 最大放出時間後にCLOSE角へ戻る

### Step 4: PCを仮想Raspberry Piとして使う

ArduinoをUSBでPCへ接続し、次を実行する。

```bash
python raspberry_pi/integration/fake_bear_to_actuator.py --port COM3 --loop
```

Linux / Raspberry Piの場合:

```bash
python3 raspberry_pi/integration/fake_bear_to_actuator.py --port /dev/ttyACM0 --loop
```

期待動作:

- PC側が仮想Camera AIとして `ai_bear_detected=true` を出す
- Arduinoへ `SET AI_BEAR 1` などを送る
- Arduino側が安全条件を満たす
- サーボが開閉する

### Step 5: 実Raspberry Pi + YOLOへ置換

最後に、仮想AIスクリプトを実際の `raspberry_pi/camera_ai/run_camera_ai.py` へ置き換える。  
このとき、YOLO単独では放出させず、必ずArduino側の安全判定を通す。

---

## 10. 配線指示

### 10.1 PCA9685とArduino

| PCA9685 | Arduino Uno / Uno Q |
|---|---|
| VCC | 5V または 3.3V（基板仕様に合わせる） |
| GND | GND |
| SDA | SDA |
| SCL | SCL |

### 10.2 PCA9685とMG996R

| MG996R | PCA9685 |
|---|---|
| Signal | CH0 PWM |
| V+ | CH0 V+ |
| GND | CH0 GND |

### 10.3 外部電源

MG996RはArduinoの5Vピンから直接給電しない。

```text
外部5〜6V電源 +  → PCA9685 V+
外部5〜6V電源 -  → PCA9685 GND
Arduino GND       → PCA9685 GND
```

GNDを共通化しないと、PWM信号の基準電位が揃わず、サーボが暴れる可能性がある。

---

## 11. 安全上の禁止事項

- 熊検知だけでハチミツを放出しない
- サーボを無限往復させるコードを統合版に残さない
- MG996RをArduinoの5Vから直接駆動しない
- 起動直後にOPENへ動く実装にしない
- ERROR_SAFE中にOPENへ動かさない
- 非常停止中にサーボを動かさない
- 実動物でのテストを行わない

---

## 12. 担当分担の整理

| 担当 | 内容 |
|---|---|
| 劉 | Raspberry Pi側Camera AI、仮想AI、統合ロジック、ログ確認 |
| 郷田さん | PCA9685 + サーボ + ハチミツ放出機構の動作確認 |
| Arduino統合部 | 状態機械、安全判定、RELEASE_ON/OFF、サーボ呼び出し |
| 構造担当 | サーボ角度、リンク機構、干渉、戻り位置の調整 |

---

## 13. 最終的な完成条件

統合完了の条件は以下とする。

1. Arduino起動直後にサーボが閉状態になる
2. `RELEASE_OFF` ではサーボが閉状態を維持する
3. `RELEASING` の間だけサーボが開状態になる
4. 最大放出時間後に自動で閉状態へ戻る
5. `emergency_stop=true` のときは必ず閉状態になる
6. 仮想AIスクリプトで、ラズパイ無しでもデモ動作を再現できる
7. 実YOLOに差し替えても、YOLO単独では放出しない

---

## 14. 統合時の最小実装方針

最小構成では、次だけできればよい。

```text
Arduino単体:
  TEST_AUTO_ON
  ↓
  仮想熊検知
  ↓
  仮想接触
  ↓
  サーボOPEN
  ↓
  自動CLOSE

PC/Raspberry Pi接続:
  fake_bear_to_actuator.py
  ↓
  SET AI_BEAR 1 / SET PAW 1 / SET HONEY 80 / SET SAFE 1
  ↓
  Arduino状態機械
  ↓
  PCA9685 + Servo
```

この段階まで確認できれば、郷田さん担当の機構コードは現在のシステムへ統合可能と判断する。
