# 開発ノート / Development Notes

最終更新: 2026-07-06T11:22:08+09:00
対象: A1 Bear Honey Buffet / Front Paw Contact Pad Safety Control System  
タイムゾーン: Asia/Tokyo (UTC+09:00)

## 1. このノートの目的

このファイルは、以下を継続的に記録する正式な開発台帳である。

- いつ、どのファイルを、何の目的で変更したか
- 安全仕様・インターフェース・状態遷移への影響
- 実施したテストと結果
- 未解決事項、既知の制約、次の作業
- システム最適化の優先順位と完了条件

## 2. 記録ルール

今後、実装・設定・文書・テスト・スクリプトを変更するたびに、この
ファイル末尾の「変更履歴」へ同じ作業単位の記録を追加する。

記録時刻は `YYYY-MM-DDTHH:MM:SS+09:00` の ISO 8601 形式を使用する。

各記録には最低限、次を含める。

```text
日時:
担当:
目的:
変更ファイル:
変更内容:
安全・インターフェースへの影響:
検証:
結果:
残課題:
```

履歴の根拠は次の優先順位とする。

1. Git コミット日時・コミット差分
2. 未コミット差分とファイル更新日時
3. README・設計資料などに残る説明

ファイル更新日時はコピーや展開でも変化するため、Git履歴より信頼度が
低い。未コミット変更の日時として使用する場合は、その旨を明記する。
`.venv/`、`__pycache__/`、`.pytest_cache/`、実行時ログ、デバッグ画像は
開発履歴の対象外とする。

## 3. 現在のシステム要約

```text
USB Camera
  -> YOLO bear detection
  -> confidence / bounding-box area / consecutive detections
  -> mock or future real contact-pad input
  -> honey / safety / emergency-stop checks
  -> Arduino Uno Q authoritative RELEASE_ON/OFF decision
  -> Raspberry Pi CSV logging and dashboard
```

原則:

- 物理リリースの最終権限は Arduino Uno Q に置く。
- Raspberry Pi の safety controller は発表・ログ・統合確認用ミラーとする。
- 欠損、タイムアウト、不正値、例外時は `RELEASE_OFF` / `HOLD` とする。
- `RELEASE_ON` には最大時間を設け、その後は cooldown へ移行する。
- 現在の接触値・インピーダンス値は模擬入力であり、実測値ではない。

## 4. 過去の編集履歴

### 2026-06-07T15:52:04+09:00 — 初期MVP

根拠: Git commit `2480228` (`first commit`)

主な変更:

- プロジェクト指示、安全ガードレール、ハードウェア役割を追加。
- Arduino Uno Q の模擬入力、状態機械、`RELEASE_ON/OFF` を実装。
- Raspberry Pi のシリアルCSVロガーと簡易ダッシュボードを追加。
- ブロック図、状態遷移、インターフェース仕様、多言語READMEを追加。
- サンプルJSON Lines/CSVと基本判断テストを追加。

安全上の意味:

- 初期状態・異常状態を `RELEASE_OFF` とする基礎を確立。
- リリース時間制限、cooldown、`ERROR_SAFE` の設計を導入。

### 2026-06-07T16:15:21+09:00 — Camera AI 基盤

根拠: Git commit `6878a02`

主な変更:

- `camera_ai/` にカメラ取得、YOLO検出、接近判定、状態発行を追加。
- 信頼度、検出面積比、連続検出による接近判定を追加。
- Camera AI JSON/CSV仕様、設計資料、テストを追加。
- Camera AIを追加認識層とし、接触・安全判断を置換しない構成にした。

### 2026-06-07T16:22:14+09:00 — Camera AI 手順改善

根拠: Git commit `0395438`

主な変更:

- Camera AI READMEへ詳細な導入、実行、トラブルシューティングを追加。

### 2026-06-07T18:03:09+09:00 — カメラ運用安定化

根拠: Git commit `9e44233`

主な変更:

- カメラ設定とCamera AI実行処理を更新。
- カメラ試験へリトライ処理とターミナル状態表示を追加。
- Raspberry Pi上での確認手順を改善。

### 2026-06-07T18:35:58+09:00 — 設定・例外処理の整理

根拠: Git commit `3cedae5`

主な変更:

- カメラ取得処理を `camera_capture.py` へ分離。
- 設定解決、カメラfallback、エラー処理を整理。
- カメラ設定テストを追加。
- 多言語READMEを現在のCamera AI構成へ更新。

### 2026-06-12T18:45:12+09:00 — 軽量モデル対応

根拠: Git commit `7590be1`

主な変更:

- NCNN、TFLite、ONNX、PyTorchモデル候補を扱う構成へ更新。
- 軽量モデルexportツールを追加。
- モデル選択テストとCamera AI仕様を更新。

狙い:

- Raspberry Pi 4B上の推論負荷を下げ、モデル形式を交換可能にする。

### 2026-06-13T17:22:25+09:00 — 学習・配布ワークフロー

根拠: Git commit `81a2d37`

主な変更:

- 学習済みモデル、NCNN成果物、Colabノートを追加。
- データ準備、学習、成果物import、Pi向けpackage作成ツールを追加。
- データセット処理テストと専用requirementsを追加。

### 2026-06-17T10:36:40+09:00 — モデルfallback強化

根拠: Git commit `291e5cb`

主な変更:

- 設定順に複数モデルをロードするfallback処理を追加。
- モデルロード失敗時のエラー情報とfail-safe動作を改善。
- モデル選択テストと仕様を更新。

### 2026-06-17T18:30:14+09:00 — Camera AI・ダッシュボード統合

根拠: Git commit `ca3a2b5`

主な変更:

- Camera AIの最新注釈画像保存とダッシュボード表示を追加。
- カメラ状態、モデル状態、検出、信頼度、面積比をブラウザ表示。
- デモ起動スクリプトとダッシュボードテストを追加・更新。

### 2026-06-17T18:45:06+09:00 — 推論間隔・画像配信改善

根拠: Git commit `9fb5e64`

主な変更:

- Raspberry Pi向け推論間隔を調整。
- 最新カメラ画像のキャッシュ抑止を強化。
- 設計・運用資料を更新。

### 2026-06-17T23:51:33+09:00 — Web Camera Viewer

根拠: Git commit `6a03476`

主な変更:

- Camera AI単体のWeb viewerを追加。
- SSHポートフォワーディングを使う遠隔確認手順を追加。
- Web viewerテストと配布package対象を更新。

### 2026-06-18T00:02:56+09:00 — リポジトリ案内整備

根拠: Git commit `e90bd1e`

主な変更:

- `feature_overview.md` と `repository_map.md` を追加。
- READMEのクイックナビゲーションとモジュール索引を改善。

### 2026-06-18T16:04:34+09:00 — アクチュエータ統合準備

根拠: Git commit `bbaa00a`

主な変更:

- PCA9685・サーボ統合コードと単体Arduinoスケッチを追加。
- 模擬Camera AIからArduinoへシリアルコマンドを送るツールを追加。
- 実Raspberry Pi/YOLOなしで統合確認できるデモを追加。
- Arduino、ロガー、インターフェース、統合手順を更新。

安全上の意味:

- アクチュエータを開く条件と `ERROR_SAFE` 時の閉鎖動作を明文化。
- 実AIの完成を待たず、模擬入力で安全経路を試験可能にした。

### 2026-06-24T19:14:39+09:00〜19:18:38+09:00 — 給餌判断システム化

根拠: 未コミット差分と各ファイル更新日時。Gitコミット日時ではない。

目的:

- 単なるYOLOデモから、Camera AI・接触確認・安全判断・給餌指令を一つの
  説明可能なシステムとして表示する。

追加:

- `raspberry_pi/safety_control/safety_controller.py`
  - Camera AI CSVまたは全模擬シナリオを入力する状態機械。
  - 接触確認時間、蜂蜜下限、release timeout、cooldownを実装。
  - 欠損・古いCamera AIデータ・不正値・緊急停止を `ERROR_SAFE` 化。
- `raspberry_pi/safety_control/config.safety_control.json`
  - safety mirrorの閾値と時間設定を一元化。
- `raspberry_pi/safety_control/README.md`
  - Camera AIモードとカメラ不要シナリオモードの手順を追加。
- `tests/test_safety_controller.py`
  - 正常リリース、接触確認、timeout、低蜂蜜、緊急停止、データ回復を試験。
- `examples/sample_feeding_decision_log.csv`
  - 発表・仕様確認用の統合CSV例を追加。

更新:

- `raspberry_pi/dashboard/app.py` (19:14:39)
  - Current State、Camera Status、Bear Detection、Confidence、
    Contact Pad、Safety Decision、Servo Command、CSV Logを強調表示。
- `docs/block_diagram.md` / `docs/state_machine.md` (19:15:38)
  - Camera AIから安全判断までの流れと発表用状態名を反映。
- `raspberry_pi/README.md` (19:17:16)
  - safety controlモジュールと統合デモを追加。
- `README.zh-CN.md`、`docs/repository_map.md`、
  `raspberry_pi/dashboard/README.md`、`scripts/run_demo.sh` (19:17:51)
  - 統合起動、模擬接触、カメラ不要モード、ログ位置を追加。
- `docs/interface_spec.md` (19:18:33)
  - 統合給餌判断CSV契約を追加。
- `docs/feature_overview.md`、`tests/test_dashboard.py` (19:18:38)
  - 実装状況、サンプルログ、ダッシュボード表示試験を追加。

状態名の扱い:

- 制御上の `READY_TO_RELEASE` を発表上 `SAFE_TO_FEED` と表示。
- 制御上の `RELEASING` を発表上 `FEEDING` と表示。
- `LOGGED` は安全制御状態に入れず、`log_status=SAVED` として記録。

検証:

- 2026-06-24T19:18:41+09:00: Camera AIログ欠損時に
  `ERROR_SAFE / RELEASE_OFF / HOLD` を確認。
- 2026-06-24T19:18:42+09:00: pytest `42 passed`。
- `bash -n scripts/run_demo.sh`、Python compile、Flask test clientを確認。

## 5. 今後のシステム最適化計画

### P0 — 安全判断の一貫性

#### P0-1. ArduinoとRaspberry Piの共通テストベクトル化

課題:

- Arduinoの正式状態機械とPiの発表用ミラーに、将来ロジック差分が生じる
  可能性がある。

計画:

- JSONまたはCSVで共通の入力シナリオと期待結果を定義する。
- PythonテストとArduino試験の両方で同じケースを使用する。
- 状態、event、release、timeout、cooldown、error latchを比較する。

完了条件:

- AGENTS.md記載の最低7ケースに、通信切断、境界値20%、接触チャタリング、
  recoveryを加えた共通テストが全件一致する。

#### P0-2. 実シリアル入力アダプタ

課題:

- safety mirrorはCamera AI CSVと模擬接触を結合するが、Arduinoの実JSON
  Linesを直接統合していない。

計画:

- `SensorSnapshot` へ変換するArduino JSON Lines入力アダプタを追加する。
- `raw_contact_value`、`paw_contact`、`honey_amount_percent`、
  `system_safe`、`emergency_stop` を使用する。
- 破損JSON、欠損フィールド、stale dataをfail-safeに処理する。

完了条件:

- Arduino切断後、設定timeout以内に表示が
  `ERROR_SAFE / RELEASE_OFF / HOLD` になる。
- 再接続だけでは物理Arduinoのerror latchを勝手に解除しない。

#### P0-3. Piから物理サーボを直接駆動しない境界の固定

計画:

- `servo_command` を表示・通信上の要求値として明記する。
- 物理出力はArduinoの `release_state` のみに結びつける。
- 将来の統合コードにもauthority/sourceフィールドを追加する。

完了条件:

- Piプロセス停止、Camera AI停止、CSV書込み失敗のどの場合もArduinoが
  `RELEASE_OFF` を維持できる統合試験がある。

### P1 — 耐障害性と観測性

#### P1-1. CSVログのローテーションと書込み耐障害化

計画:

- 日付または最大容量でログをローテーションする。
- flush/fsync方針を決め、途中書込み行を無視できるreaderにする。
- ディスク空き容量不足をダッシュボードへ表示する。

完了条件:

- 24時間相当の模擬運転でメモリ使用量が増え続けない。
- 破損最終行があっても直前の正常状態を表示できる。

#### P1-2. データ鮮度の可視化

計画:

- Camera AI、Arduino、feeding decisionの各最終更新時刻とageを表示する。
- stale閾値を超えたカードを赤表示し、release表示をHOLDへ固定する。

完了条件:

- デモ中に「Runningだが古いデータ」を誤って正常表示しない。

#### P1-3. 構造化エラーコード

計画:

- Arduino、Camera AI、safety mirrorでエラーコード命名を統一する。
- `error_code`、`error_message`、`source`、`recoverable` を記録する。

完了条件:

- 発生源と復旧方法をログ1行から判別できる。

### P1 — 性能最適化

#### P1-4. Raspberry Pi 4B実機ベンチマーク

計画:

- NCNN、ONNX、PyTorch fallbackごとに推論時間、FPS、CPU、RAM、温度を測る。
- 320x240/640x480、input size、推論間隔を比較する。
- 精度を落としすぎない最小負荷設定を選ぶ。

完了条件:

- 10分以上の連続動作でCamera AI、dashboard、loggerが安定する。
- 選定設定と測定値を開発ノートへ記録する。

#### P1-5. CSVポーリング負荷削減

課題:

- 現在は最新状態取得のためCSV全体を読み返す箇所があり、長時間ログで
  遅くなる可能性がある。

計画:

- 最新状態を小さなatomic JSONファイルへ別途保存する、または末尾読取りに
  変更する。
- 履歴CSVは追記専用として維持する。

完了条件:

- ログ件数が増えてもダッシュボード応答時間がほぼ一定である。

### P2 — センサー統合品質

#### P2-1. 接触センサー抽象化

計画:

- `mock`、Arduino digital contact、低電圧抵抗測定を同じinterfaceへ揃える。
- 生値、単位、閾値、校正状態、validityを記録する。
- 実測前は92.4 kΩなどの模擬値を実熊データとして扱わない。

完了条件:

- 入力sourceを設定だけで交換でき、状態機械を変更しない。

#### P2-2. チャタリング・ノイズ対策

計画:

- contact confirmに加えてrelease中の瞬断許容時間を安全側に検討する。
- median/連続サンプル方式を模擬波形で比較する。

完了条件:

- ノイズ試験ケースで意図しない `RELEASE_ON` が一度も発生しない。

### P2 — デモと保守性

#### P2-3. 設定契約の一本化

計画:

- Arduino `config.h` とPi JSONに重複する閾値を一覧化する。
- 生成または検証スクリプトで値の不一致を検出する。

完了条件:

- CI/テストで閾値不一致が失敗として検出される。

#### P2-4. デモ事前診断

計画:

- `scripts/preflight_check.sh` を追加し、Python環境、モデル、カメラ、
  serial port、書込み権限、ポート8080、ディスク容量を確認する。

完了条件:

- 発表前に1コマンドで問題箇所と修正案を表示できる。

#### P2-5. ダッシュボードの状態履歴

計画:

- 最新状態だけでなく、直近の状態遷移とrelease回数を表示する。
- `ERROR_SAFE`、timeout、low honeyを色分けする。

完了条件:

- 発表者が「なぜHOLDなのか」を画面だけで説明できる。

## 6. 推奨実装順序

1. 共通テストベクトル
2. Arduino JSON Lines入力アダプタ
3. データ鮮度表示
4. 最新状態ファイルとログローテーション
5. Raspberry Pi 4B性能計測
6. 実接触センサーアダプタ
7. 設定整合性チェック
8. デモpreflightと状態履歴表示

## 7. 変更履歴

### 2026-06-25T12:22:28+09:00 — 開発ノート作成

担当: Codex

目的:

- 過去の編集履歴をGit履歴から復元する。
- 今後の全変更を日時付きで継続記録する。
- 次期システム最適化の順序と完了条件を定義する。

変更ファイル:

- `DEVELOPMENT_NOTES.md`
- `AGENTS.md`

変更内容:

- 2026-06-07から2026-06-24までの13コミットと未コミット統合変更を整理。
- P0〜P2の最適化計画を追加。
- 今後の変更時に本ノートを必ず更新するルールを追加。

安全・インターフェースへの影響:

- 実行コード、状態機械、GPIO、シリアル契約への変更なし。

検証:

- Git log、commit差分、未コミット差分、対象ファイル更新日時を照合。
- Markdown構造と記載パスを確認。
- 2026-06-25T12:24:44+09:00: pytest `42 passed`。

結果:

- 開発履歴と次期計画を単一ファイルで参照可能にした。

残課題:

- 2026-06-24の給餌判断システム化は未コミットのため、正式コミット後に
  commit hashを追記する。

### 2026-07-02T15:26:27+09:00 — Dashboard Demo Mode追加

根拠: 未コミット差分と編集時刻。Gitコミット日時ではない。

担当: Codex

目的:

- Tailscale経由で開いたRaspberry Piダッシュボードから、USBシリアル接続の
  Arduinoへ安全なデモ用コマンドを送れるようにする。
- ArduinoをWi-Fi化せず、Dashboard → Raspberry Pi → USB serial → Arduino
  の境界を保つ。

変更ファイル:

- `raspberry_pi/dashboard/app.py`
- `raspberry_pi/dashboard/requirements.txt`
- `raspberry_pi/dashboard/README.md`
- `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino`
- `arduino_uno_q/actuator_standalone/actuator_standalone.ino`
- `arduino_uno_q/contact_pad_controller/README.md`
- `docs/interface_spec.md`
- `docs/GODA_ACTUATOR_INTEGRATION_INSTRUCTIONS_JP.md`
- `tests/test_dashboard.py`
- `scripts/run_demo.sh`
- `DEVELOPMENT_NOTES.md`

変更内容:

- ダッシュボードへ Demo Mode パネル、Enable/Disable、Release/Open、
  Stop/Close、Test Motion、Emergency Stop、最新コマンド状態表示を追加。
- Flask APIに `/api/demo-status`、`/api/demo-enable`、`/api/demo-mode`、
  `/api/demo-command`、個別demo endpointを追加。
- Raspberry Pi側でUSBシリアル送信を一元化し、`RELEASE`、`STOP`、`TEST`
  をArduinoへ送るようにした。
- Arduino未接続、serial port不可、pyserial未導入時は `SIMULATED` として
  CSVへ記録し、UIは動作継続する。
- Demo command CSVログを追加し、dashboard requirementsへ `pyserial` を追加。
- `scripts/run_demo.sh` からDashboard起動時にdemo serial port、baudrate、
  demo command log fileを渡すようにした。
- Arduino側にDemo Mode用 `RELEASE`、`STOP`、`TEST` 受信処理を追加。
  `RELEASE`/`TEST` は `ERROR_SAFE` を解除せず、既存の状態機械とtimeoutを
  通る。
- ダッシュボードテストにDemo Mode API、fake serial、simulation fallback、
  invalid command、demo log除外確認を追加。

安全・インターフェースへの影響:

- デフォルトは `STOP` / closed、Demo Modeは無効。
- `RELEASE` と `TEST` は手動Enable後のみ送信可能。
- `STOP` / CloseとEmergency StopはDemo Mode無効時でも `STOP` を送信でき、
  Emergency StopはDemo Modeを無効化。
- Raspberry Piはコマンド送信ゲートウェイであり、ArduinoのWi-Fi化や完全無線
  制御への変更なし。
- Demo command logはcontact/safety CSVとして誤選択されないよう除外。

検証:

- 2026-07-02T15:33:33+09:00: `python -m py_compile
  raspberry_pi/dashboard/app.py raspberry_pi/logger/serial_logger.py
  raspberry_pi/safety_control/safety_controller.py` 成功。
- 2026-07-02T15:33:33+09:00: `bash -n scripts/run_demo.sh` 成功。
- 2026-07-02T15:32:07+09:00: `.venv/bin/python -m pytest
  tests/test_dashboard.py -q` は `12 passed`。
- 2026-07-02T15:33:33+09:00: `.venv/bin/python -m pytest -q` は
  `51 passed`。

結果:

- ハードウェア未接続でもDemo ModeのUI、API、CSVログ、simulation fallbackを
  確認できた。
- 実Arduino接続時はRaspberry Pi backendだけがUSBシリアルを扱う構成になった。

残課題:

- Raspberry Pi実機で `/dev/ttyACM0` 接続、Tailscale経由アクセス、Arduino実機の
  `RELEASE` / `STOP` / `TEST` 受信を確認する。

### 2026-07-04T21:56:00+09:00 — NCNNネイティブ推論への移行（ultralytics非依存化）

担当: LIU Chengyang / 刘承洋_C.Y.LIU

目的:

Raspberry Pi 4B で `ultralytics`（PyTorch依存）が `Illegal instruction` を
引き起こしていた問題を解決し、`models/yolo_bear_ncnn_model` を用いた
NCNNネイティブ推論を `YoloBearDetector` のプライマリバックエンドとする。

変更ファイル:

- `raspberry_pi/camera_ai/bear_detector.py`

変更内容:

- `YoloBearDetector.__init__` でモデルパスが NCNN ディレクトリ（`*.ncnn.param`
  を含む）か `.pt` ファイルかを自動判定するよう変更。
- NCNN バックエンド (`_init_ncnn`, `_detect_ncnn`) を新規追加。
  - `ncnn.Mat.from_pixels_resize` + `substract_mean_normalize` で前処理。
  - `ncnn.Net` + `create_extractor` で推論実行。
  - 出力 `(5, 1344)` = `[cx, cy, w, h, class_score]` を xyxy 形式に変換し、
    元フレーム寸法にスケーリング。
- Ultralytics バックエンド (`_init_ultralytics`, `_detect_ultralytics`) を
  fallback として保持（`.pt` ファイル用）。
- `metadata.yaml` からクラス名を読み込む `_load_metadata_class_names` を追加。
- `_check_runtime_dependency`, `_ensure_backend_ready` を削除（バックエンド
  分離により不要になったため）。

安全・インターフェースへの影響:

- 外部インターフェース (`detect()` の入出力形式) に変更なし。
- NCNN モデル使用時は `ultralytics` / PyTorch のインストール不要。
- detection dict の `bbox_xyxy` はクランプ処理追加によりフレーム範囲外に
  ならないことを保証。

検証:

- `python -c "from raspberry_pi.camera_ai.bear_detector import YoloBearDetector;
  d = YoloBearDetector('models/yolo_bear_ncnn_model'); print(d._backend)"`
  → `ncnn`
- ダミーフレーム (480x640 黒背景 + 赤矩形) で 10 件の検出を確認。
- 実カメラ (`/dev/video0`, 1920x1080) で 9 件の検出を確認。
- `python -m raspberry_pi.camera_ai.run_camera_ai --device /dev/video0
  --terminal-status --no-jsonl --once --save-debug-frames`
  → `event=AI_NO_BEAR camera=ok model=ok infer_ms=117.9`
- `./scripts/run_demo.sh` で Camera AI + Safety Controller + Dashboard が
  すべて起動し、CSVログ・debug frame が正常生成されることを確認。

結果:

- Camera AI が NCNN で正常動作 (推論 ~87-117ms)。
- Safety Controller が ERROR_SAFE → IDLE に復帰 (event=RESET)。
- Dashboard が HTTP 200 で応答、`/camera/latest.jpg` が生成。
- `data/logs/feeding_decision_log.csv` に safety decision が記録。

残課題:

- 実機で熊（または熊の画像）をカメラに映し、`AI_BEAR_DETECTED` →
  `AI_BEAR_APPROACHING` の状態遷移を確認する。
- アノテーション付き debug frame に検出枠が描画されているか目視確認する。

### 2026-07-05T13:53:05+09:00 — ESP32 BIA入力とUno安全状態機械の統合

担当: Codex

目的:

未コミット作業のファイル更新時刻に基づく記録。ESP32上のBIA測定スケッチを
Arduino Unoの前足接触入力として接続できるようにし、既存のサーボ付き
`contact_pad_controller` の安全状態機械へBIA接触判定を合流させる。

変更ファイル:

- `sensor/BIA.ino`
- `sensor/README.md`
- `arduino_uno_q/contact_pad_controller/config.h`
- `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino`
- `arduino_uno_q/README.md`
- `arduino_uno_q/contact_pad_controller/README.md`
- `raspberry_pi/logger/serial_logger.py`
- `docs/interface_spec.md`
- `docs/block_diagram.md`
- `docs/state_machine.md`
- `HARDWARE_TARGETS.md`
- `examples/sample_uno_q_output.jsonl`
- `examples/sample_log.csv`
- `DEVELOPMENT_NOTES.md`

変更内容:

- ESP32 BIAスケッチに `contact_detected` 判定、USB debug JSON Lines、
  Arduino向けUART最小JSON Lines、`CALIBRATE` / `SET_THRESHOLD` / `STATUS`
  コマンドを追加。
- GPIO17は既存の `DDS2_CS` と衝突するため、ESP32 UART TXをGPIO16に設定。
- Arduino Uno側に任意のBIA UART入力を追加。既定は
  `#define BIA_INPUT_ENABLED 0` のままなので、従来のシミュレーションMVPは
  変更なしで動作する。
- BIA入力有効時は `contact_detected` を `paw_contact` 入力源として使い、
  `amplitude1` を `raw_contact_value` としてRaspberry Piへ中継する。
- BIAデータ欠損、タイムアウト、長すぎるメッセージ、不正JSONを
  `ERROR_SAFE` / `RELEASE_OFF` に落とす処理を追加。
- Raspberry Pi CSV loggerにBIA関連の任意列を追加。
- インターフェース仕様、ブロック図、状態機械、ハードウェアターゲット、
  Arduino/BIA手順、サンプルJSON/CSVを更新。

安全・インターフェースへの影響:

- Arduino Unoが引き続き最終リリース安全判断を持つ。
- ESP32 BIAは接触入力サブモジュールであり、`RELEASE_ON/OFF` を直接決めない。
- 既定状態はBIA無効・シミュレーション入力のまま。
- BIA有効時に通信異常がある場合、`ERR_BIA_TIMEOUT` または
  `ERR_BIA_BAD_MESSAGE` 系で `ERROR_SAFE` に入り、`RESET` まで復帰しない。
- Uno -> Raspberry Pi JSON Linesに
  `contact_input_source`, `bia_input_enabled`, `bia_data_valid`,
  `bia_data_age_ms`, `bia_contact_detected`, `bia_phase1`,
  `bia_amplitude2`, `bia_phase2` を任意フィールドとして追加。

検証:

- `python -m py_compile raspberry_pi/logger/serial_logger.py
  raspberry_pi/dashboard/app.py` 成功。
- `bash -n scripts/run_demo.sh` 成功。
- `examples/sample_uno_q_output.jsonl` のJSON parse成功。
- `examples/sample_log.csv` の列数整合確認成功 (`27` columns)。
- `python -m pytest tests/test_dashboard.py tests/test_decision_logic.py -q` は
  `No module named pytest` のため未実施。
- `arduino-cli` / `arduino-lint` は環境になく、Arduino/ESP32実コンパイルは
  未実施。

結果:

- BIAを使わない既定MVPでは、既存の自動シミュレーション、サーボ制御、
  JSON Lines出力を維持する構成になった。
- BIAを有効化した場合の接触入力経路、ログ列、安全フォールバック仕様を
  コードと文書に反映した。

残課題:

- Arduino IDEまたは `arduino-cli` がある環境でUnoスケッチとESP32 BIAスケッチを
  実コンパイルする。
- 実配線で ESP32 GPIO16 TX -> Arduino D4 RX、GND共通、9600 baud の受信を確認する。
- BIA閾値は模擬物または人の手による安全な低電圧・微小電流テストで調整し、
  実動物では試験しない。

### 2026-07-06T02:30:00+09:00 — ONNXエクスポートノートブック修正（torch 2.5.1 ダウングレード）

担当: Codex

目的:

Colab のデフォルト Python 3.12 + torch 2.11 環境で `onnxscript` が
`torch_2_11` サブモジュールを欠いており、ONNX エクスポートが
`No module named 'onnxscript._framework_apis.torch_2_11'` で失敗する問題を修正。

1回目の修正（torch 最新 + opset 18）では onnxscript のバージョン不一致が
解消されなかったため、torch を 2.5.1 にダウングレードする方針に切り替えた。

変更ファイル:

- `notebooks/export_bear_yolo_onnx.ipynb`
- `DEVELOPMENT_NOTES.md`

変更内容:

- インストールセル: `torch==2.5.1 --index-url .../cpu` に固定。
  torch 2.5.1 は cp312 wheel があり、onnxscript 互換性が確認されている。
- エクスポートセル: opset=18 でエクスポート（dynamo exporter 要件）。
- 新規セル: opset 18 → 12 変換（`onnx.version_converter`）。
- 検証セル: opset <= 15 アサート。
- 全 Markdown 説明を 2026-07 + torch 2.5.1 の状況に更新。

安全・インターフェースへの影響:

- モデルファイル (`yolo_bear.onnx`) の opset バージョンが変わる可能性が
  あるが、推論インターフェース（入力 256x256、出力 (1,5,1344)）は不変。
- opset 12 変換成功時は Raspberry Pi cv2.dnn 互換を維持。
- opset 18 のままの場合は Pi 側で onnxruntime が必要。

検証:

- ノートブックのセル構造・コード構文を目視確認（13セル、全セル整合）。
- Colab 実実行は未実施（ユーザー側で実行予定）。

結果:

- torch 2.5.1 により onnxscript 互換性の問題が解決する見込み。
- Raspberry Pi cv2.dnn 互換の opset 12 出力を変換経由で維持。

残課題:

- Colab 実環境で全セルを順次実行し、エクスポートと opset 変換の成否を確認する。
- opset 変換失敗時に備え、Pi 側 Camera AI に onnxruntime バックエンドを
  追加するか検討する。

## 8. 今後追記用テンプレート

```markdown
### YYYY-MM-DDTHH:MM:SS+09:00 — 変更タイトル

担当:

目的:

変更ファイル:

- `path/to/file`

変更内容:

- 

安全・インターフェースへの影響:

- 

検証:

- 

結果:

- 

残課題:

- 
```

### 2026-07-06T00:00:00+09:00 — ダッシュボードの全画面リロード廃止と部分更新化

担当: AI assistant

目的:

- `./scripts/run_demo.sh` 起動時、ダッシュボードが約1秒ごとにページ全体を
  リロードし、スタイル再適用・画像再取得・フォーム状態リセット・
  スクロールリセットのチラつきで実用にならない問題を解消する。

変更ファイル:

- `raspberry_pi/dashboard/app.py`

変更内容:

- HTML ヘッダの `<meta http-equiv="refresh">` を廃止。ページ全体の
  再読み込みを止めた。
- `<main>` に `id="dashboard-main"`、`data-refresh-interval`、
  `data-demo-enabled`、`data-emergency-stop` の各 data 属性を付与。
- 末尾に JavaScript を追加し、`setInterval` で `/` を `fetch` し、
  `DOMParser` で `<main>` の中身だけ差し替える部分更新を実装。
  CSS/JS を再評価せず、ScrollTop やフォーム入力もリセットしない。
- Demo Mode の各送信フォームに `data-demo-control` を付与し、submit を
  インターセプトして fetch で送信後に部分更新するよう変更。
  これにより 303 リダイレクトによる再描画のチラつきも防止。
- `--refresh` の既定値を 1 秒から 2 秒に延長し、部分更新負荷と画像再取得
  頻度を抑えた。

安全・インターフェースへの影響:

- 安全 Release 判定そのものは Arduino Uno Q 側のまま変更なし。
- Raspberry Pi 側ダッシュボードはあくまで監視・演示層であり、
  RELEASE_ON/OFF の主安全判定を Pi に移動させる変更ではない。
- Demo Mode のAPI・シリアルコマンド・コマンドログ仕様は不変。
  HTML form は引き続き同じ action/parameter で POST する。

検証:

- `.venv/bin/python -m py_compile raspberry_pi/dashboard/app.py` → OK
- `.venv/bin/python -m pytest tests/test_dashboard.py -q` → 12/12 passed

結果:

- 12 個のダッシュボードテストが全て成功。既存の表示前提文字列や
  フレーム取得・Demo API 挙動は保たれた。
- 未コミット変更として記録。ファイルシステム更新日時ベース。

残課題:

- 実機ブラウザでのチラつき解消を操作者目線で最終確認すること。
- 画像は依然として部分更新のたびに `?t=<ns>` のみ置換され、
  Camera AI 書き出し頻度に応じて再取得される。許容範囲だが、
  カメラFPSが上がった場合は画像専用の低頻度更新切り分けを検討する。

### 2026-07-06T09:37:47+09:00 — GODAアクチュエータのULN2003ステッパーモード追加

担当: Codex

目的:

- `Haruka GODA/beehivemotorC++/beehivemotorC++.ino` で、既存の
  PCA9685サーボ駆動に加えて、ULN2003経由のステッピングモータ駆動を
  選択できるようにする。

変更ファイル:

- `Haruka GODA/beehivemotorC++/beehivemotorC++.ino`
- `DEVELOPMENT_NOTES.md`

変更内容:

- `ACTIVE_MOTOR_MODE` を追加し、
  `MOTOR_MODE_ULN2003_STEPPER` と `MOTOR_MODE_PCA9685_SERVO` を
  コンパイル時に切り替えられる構成にした。
- 既定モードを `MOTOR_MODE_ULN2003_STEPPER` に設定した。
- ULN2003ステッパーモードに、D8-D11をIN1-IN4として使う半ステップ駆動、
  開位置 `1024` half-steps、閉位置 `0` へのボタン切替動作を追加した。
- ステッパー移動後は既定でコイルをOFFにし、待機時の発熱を抑える設定にした。
- PCA9685サーボ側の初期化・0/90度切替動作を同じボタン操作APIに整理し、
  既存モードとして残した。

安全・インターフェースへの影響:

- このスケッチは単体アクチュエータ確認用であり、メインの
  Front Paw Contact Pad安全状態機械やUno QのRELEASE_ON/OFF判断は変更なし。
- ULN2003モードでは起動時の現在位置を閉/originとして扱うため、実機では
  電源投入前に機構位置を合わせる必要がある。
- 待機時はステッパーコイルをOFFにするため発熱は抑えられるが、保持トルクは
  失われる。必要な場合のみ `releaseStepperCoilsAfterMove` を調整する。

検証:

- `arduino-cli compile --fqbn arduino:avr:uno --build-path
  /tmp/codex-beehivemotor-uln2003-build 'Haruka GODA/beehivemotorC++'`
  → 成功。3712 bytes flash、584 bytes RAM。
- `arduino-cli compile --fqbn arduino:avr:uno --build-path
  /tmp/codex-beehivemotor-servo-build --build-property
  compiler.cpp.extra_flags=-DACTIVE_MOTOR_MODE=1
  'Haruka GODA/beehivemotorC++'`
  → 成功。8592 bytes flash、742 bytes RAM。

結果:

- ULN2003ステッパーモードを既定としてUno向けにコンパイル可能になった。
- PCA9685サーボモードもコマンドライン切替でコンパイル可能なまま維持した。
- 未コミット変更として記録。ファイルシステム編集時刻ベース。

残課題:

- 実機でULN2003 IN1-D8 / IN2-D9 / IN3-D10 / IN4-D11、5V、GND共通の
  配線を確認し、回転方向と開閉量を調整する。
- 実機機構に合わせて `stepperOpenSteps` と `stepperStepDelayUs` を調整する。

### 2026-07-06T09:45:00+09:00 — Camera AIのNCNN segfault回避とカメラのみフェイルセーフモード追加

担当: AI assistant

目的:

- `./scripts/run_demo.sh` 起動後、カメラ画面が数秒で固まる問題を解消。
  原因は Camera AI が `ex.extract("out0")` で SIGSEGV(終了コード139) し、
  `run_camera_ai` プロセスが即死して最新フレーム更新が止まっていたため。
  gdb/faqulthandler で `ncnn.cpython-313-aarch64-linux-gnu.so` 内の
  再帰的スタックで segfault することを確認（入力256x256/3ch正常）。

変更ファイル:

- `raspberry_pi/camera_ai/run_camera_ai.py`
- `scripts/run_demo.sh`

変更内容:

- `run_camera_ai.py` に `--no-inference` オプションを追加。
  推論をスキップし、カメラ撮像・debug frame書き出し・CSV/JSONL/
  terminal status 出力だけを継続するフェイルセーフループ
  (`run_camera_only_failsafe_loop`) を実装。状態は `ai_model_ok=false
  / ai_bear_approaching=false / event=AI_INFERENCE_DISABLED` で常に HOLD。
- `--once`/`--max-iterations` の停止条件をフェイルセーフループにも適用。
- `scripts/run_demo.sh` に環境変数 `RUN_CAMERA_AI_INFERENCE` を追加。
  既定は `0`（推論無効＝カメラのみフェイルセーフ）。NCNNが正常動作する
  環境では `RUN_CAMERA_AI_INFERENCE=1` で元の推論パスに戻る。

安全・インターフェースへの影響:

- Release 主安全判定は Arduino Uno Q 側のまま変更なし。
- Raspberry Pi 側 Camera AI は監視・演示層であり、これ単独で
  RELEASE_ON を出さない設計は不変。
- フェイルセーフモードでは `ai_bear_approaching=false` 固定のため、
  safety_controller は熊なしと判定し HOLD を維持。安全側に倒れている。
- Camera AI の JSON Lines / CSV フィールド形式は同一。
  `ai_model_ok=false` と `event=AI_INFERENCE_DISABLED` が新たに出る。

検証:

- `python -m py_compile raspberry_pi/camera_ai/run_camera_ai.py` → OK
- `python -m raspberry_pi.camera_ai.run_camera_ai ... --once --no-inference`
  → EXIT=0、フレーム更新確認（09:41:24）。
- `RUN_SAFETY_CONTROL=0 RUN_DASHBOARD=0 RUN_CAMERA_AI_INFERENCE=0
  timeout 12 ./scripts/run_demo.sh` → Camera AI が12秒間連続稼働、
  状態行が1秒間隔で継続出力、フレーム更新継続。
- `python -m pytest tests/test_camera_ai_approach_logic.py
  tests/test_decision_logic.py` → 12/12 passed。

結果:

- Demo 起動時のカメラ画面固まりを解消。ダッシュボードは最新フレームを
  更新し続けるようになった。熊検知は NCNN 復旧までオフ（HOLD継続）。
- 未コミット変更として記録。ファイルシステム編集時刻ベース。

残課題:

- NCNN `1.0.20260526` の aarch64 ビルドと当該モデルの組合せで
  `extract` が segfault する根本原因は未解明。別バージョンのncnn、
  ultralytics `.pt` fallback、または ONNX/TFLite 経由で熊検知を
  復旧させること。復旧後は `RUN_CAMERA_AI_INFERENCE=1` に戻す。

### 2026-07-06T09:43:45+09:00 — GODAアクチュエータのL293Dステッパーモード切替

担当: Codex

目的:

- 直前に追加したULN2003ステッパーモードをやめ、L293D経由の
  ステッピングモータ駆動へ切り替える。

変更ファイル:

- `Haruka GODA/beehivemotorC++/beehivemotorC++.ino`
- `DEVELOPMENT_NOTES.md`

変更内容:

- `MOTOR_MODE_ULN2003_STEPPER` を `MOTOR_MODE_L293D_STEPPER` に置換し、
  既定モードをL293Dステッパーにした。
- L293D配線想定を、Enable A=D5、IN1=D8、IN2=D9、Enable B=D6、
  IN3=D10、IN4=D11としてコードとシリアル表示に反映した。
- 4-wire bipolar stepper向けに2相励磁の4ステップシーケンスへ変更した。
- 移動時はEnable A/BをHIGH、移動後は既定でEnable A/Bと入力をLOWにし、
  待機時の発熱と通電を抑える構成にした。
- PCA9685サーボモードは `ACTIVE_MOTOR_MODE=1` でコンパイル可能なまま維持した。

安全・インターフェースへの影響:

- この変更は単体アクチュエータ確認用スケッチのみで、メインの
  Front Paw Contact Pad安全状態機械やUno QのRELEASE_ON/OFF判断は変更なし。
- L293DのVCC2はモータ用電源を使い、ArduinoとはGND共通にする必要がある。
- 起動時の現在位置を閉/originとして扱うため、実機では電源投入前に
  機構位置を合わせる必要がある。
- `stepperOpenSteps` は一般的な1.8度ステッパーの約90度として50 stepsにしたが、
  実機のギア比・機構に合わせて調整が必要。

検証:

- `arduino-cli compile --fqbn arduino:avr:uno --build-path
  /tmp/codex-beehivemotor-l293d-build 'Haruka GODA/beehivemotorC++'`
  → 成功。3762 bytes flash、576 bytes RAM。
- `arduino-cli compile --fqbn arduino:avr:uno --build-path
  /tmp/codex-beehivemotor-servo-build --build-property
  compiler.cpp.extra_flags=-DACTIVE_MOTOR_MODE=1
  'Haruka GODA/beehivemotorC++'`
  → 成功。8592 bytes flash、742 bytes RAM。

結果:

- L293Dステッパーモードを既定としてUno向けにコンパイル可能になった。
- コード中のULN2003前提のモード名・配線表示・半ステップシーケンスを
  L293D前提に置き換えた。
- 未コミット変更として記録。ファイルシステム編集時刻ベース。

残課題:

- 実機でL293D Enable/Input配線、VCC2モータ電源、GND共通を確認する。
- モータの回転方向が逆の場合はコイル配線またはシーケンス順を調整する。
- 実機機構に合わせて `stepperOpenSteps` と `stepperStepDelayMs` を調整する。

### 2026-07-06T10:30:00+09:00 — ONNX/cv2.dnn推論経路追加とNCNN segfault恒久復旧準備

担当: AI assistant

目的:

- 前回の一時対応(--no-inference)では `ai_model_ok=false` のままになり、
  熊検知が完全に無効化されていた。NCNN 1.0.20260526 の aarch64 ビルドが
  `extract("out0")` で SIGSEGV する問題を、Pi 上の PyTorch インストール無しで
  恒久復旧するため、ONNX + OpenCV `cv2.dnn` 推論経路を追加し、Colab で
  `.pt` -> ONNX を書き出す運用に切り替える。

変更ファイル:

- `raspberry_pi/camera_ai/bear_detector.py`
- `raspberry_pi/camera_ai/run_camera_ai.py`
- `scripts/run_demo.sh`
- `notebooks/export_bear_yolo_onnx.ipynb` (新規)
- `tests/test_camera_ai_model_selection.py`
- `README.md`, `README.ja.md`, `README.zh-CN.md`, `README.ko.md`
- `raspberry_pi/dashboard/app.py` (motor_driver import のみ別件修正)
- `DEVELOPMENT_NOTES.md`

変更内容:

- `bear_detector.py` に ONNX/cv2.dnn バックエンド(`_init_onnx` /
  `_detect_onnx`)を追加。`.onnx` ファイルを検出すると自動的にこの経路を使う。
  YOLOv8 ONNX 出力レイアウト `[1, 4+nc, anchors]` に合わせ、objectness なしの
  class_scores最大値を conf とする解析に修正。
- `run_camera_ai.py` の `resolve_model_candidates` を変更し、
  既存候補の中で ONNX ファイルを NCNN ディレクトリより優先するようソート。
  単一の `models/yolo_bear.onnx` を置くだけで cv2.dnn 経路に自動切替。
- `scripts/run_demo.sh` の `RUN_CAMERA_AI_INFERENCE` 既定値を
  「`models/yolo_bear.onnx` があれば 1、なければ 0」の自動判定に変更。
  ONNX 未配置時は従来通りカメラのみフェイルセーフで画面更新を維持。
- `notebooks/export_bear_yolo_onnx.ipynb` を新規追加。Colab 上で
  `best.pt` を読み込み、`imgsz=256, opset=12, simplify=True, dynamic=False`
  で ONNX を書き出し、`yolo_bear.onnx` としてダウンロードする手順をまとめた。
- 各言語 README に「NCNN が segfault する環境では Colab で ONNX を書き出し
  `models/yolo_bear.onnx` を配置すると自動で cv2.dnn 推論に切り替わる」手順を追記。
- `tests/test_camera_ai_model_selection.py` に
  `test_resolve_model_candidates_prefers_onnx_over_ncnn` を追加。
- `raspberry_pi/dashboard/app.py` の `from motor_driver import ...` を
  パッケージ相対 import に修正し、テスト収集時の ModuleNotFoundError を解消。

安全・インターフェースへの影響:

- Release 主安全判定は Arduino Uno Q 側のまま変更なし。
- Camera AI は監視・演示層であり、これ単独で RELEASE_ON を出さない設計は不変。
- ONNX 推理が有効な場合のみ `ai_model_ok=true` になる。モデル未配置時は
  引き続き `ai_model_ok=false` で HOLD を維持(安全側)。
- Camera AI の JSON Lines / CSV フィールド形式は同一。

検証:

- `python -m py_compile bear_detector.py run_camera_ai.py` → OK
- `bash -n scripts/run_demo.sh` → OK
- `pytest tests/test_camera_ai_model_selection.py
  tests/test_camera_ai_approach_logic.py tests/test_decision_logic.py
  tests/test_dashboard.py` → 32 passed, 1 preexisting failure
  (test_ncnn_model_without_runtime_fails_before_ultralytics_load は
   今回より前から存在する stale テストで `_check_runtime_dependency`
   メソッドが存在しない。今回のスコープ外。)
- ONNX 未配置時の `timeout 6 ./scripts/run_demo.sh` → カメラのみ
  フェイルセーフで起動し画面更新継続(従来同等)。

結果:

- Colab で `yolo_bear.onnx` を作成し `models/yolo_bear.onnx` に配置すれば、
  Pi 側に PyTorch/ultralytics/NCNN を新規インストールせずに
  `ai_model_ok=true` の推論復旧が可能になった。
- 未コミット変更として記録。ファイルシステム編集時刻ベース。

残課題:

- ユーザーが Colab(`notebooks/export_bear_yolo_onnx.ipynb`)で
  `yolo_bear.onnx` を生成し、`models/yolo_bear.onnx` に配置すること。
  配置後 `./scripts/run_demo.sh` を再起動し、`ai_model_ok=true` と
  画面更新を確認する。
- `_detect_onnx` は NMS を持たない簡易パース。熊単一クラス想定で
  ハッカソン演示には十分だが、誤検出が多い場合は NMS を追加すること。
- 既存の stale テスト `test_ncnn_model_without_runtime_fails_before_ultralytics_load`
  を別途 `_init_ncnn` の RuntimeError 期待に更新すること。

### 2026-07-06T11:10:54+09:00 — Camera AI 依存分離と Colab export 復旧

根拠: 未コミット差分とファイルシステム編集時刻。Gitコミット日時ではない。

目的:

- Colab で `torch` / `torchvision` / `ultralytics` / `onnx` を一度アンインストール
  してから再インストールする手順が、途中キャンセル時に `ultralytics` 欠落と
  `torchvision` 欠落を起こしていたため、再発しにくい export 手順へ修正する。
- Raspberry Pi 実行環境では PyTorch/Ultralytics を入れず、ONNX/NCNN runtime に
  依存を限定する。

変更ファイル:

- `raspberry_pi/camera_ai/requirements.txt`
- `raspberry_pi/camera_ai/requirements.export.txt` (新規)
- `notebooks/export_bear_yolo_onnx.ipynb`
- `raspberry_pi/camera_ai/bear_detector.py`
- `raspberry_pi/camera_ai/run_camera_ai.py`
- `raspberry_pi/camera_ai/export_lightweight_yolo.py`
- `raspberry_pi/camera_ai/train_bear_yolo.py`
- `raspberry_pi/camera_ai/README.md`
- `README.md`, `README.ja.md`, `README.zh-CN.md`
- `docs/camera_ai_interface_spec.md`
- `tests/test_camera_ai_model_selection.py`
- `DEVELOPMENT_NOTES.md`

変更内容:

- Pi 実行用 `requirements.txt` から `ultralytics` を削除し、
  OpenCV/ONNX Runtime/PyYAML/NCNN/Flask の runtime 依存に限定。
- Colab/開発PCの学習・export 用に `requirements.export.txt` を追加し、
  export 後の読み込み確認用に `onnxruntime` も含めた。
- `export_bear_yolo_onnx.ipynb` の失敗した実行出力を消し、`pip uninstall` を廃止。
  既存 `torch` / `torchvision` は残し、import 不可の時だけ CPU wheel
  (`torch==2.5.1`, `torchvision==0.20.1`) を修復する手順へ変更。
  `ultralytics` は `--no-deps` で入れ、Colab の working torch stack を置換しない。
- `YoloBearDetector._check_runtime_dependency()` を追加し、NCNN/ONNX/Ultralytics の
  backend 別に早期エラーと正しいインストール案内を出すよう修正。
- ONNX backend を ONNX Runtime 実行へ寄せ、opset 18 export でも Pi 側で扱える
  runtime contract に更新。
- `run_camera_ai.py` とモデル選択テストの ONNX 優先説明を ONNX Runtime に合わせた。
- export/training スクリプトの `ultralytics` 欠落メッセージを
  `requirements.export.txt` 参照へ変更。
- README/仕様書に Pi runtime と Colab/export 依存の分離を追記。

安全・インターフェースへの影響:

- Arduino Uno Q の RELEASE_ON/OFF 判定、状態機械、JSON Lines/CSV interface は変更なし。
- Camera AI は引き続き追加認識層であり、単独で蜂蜜放出を許可しない。
- モデルや依存が欠落した場合は `AI_MODEL_LOAD_ERROR` / `ai_model_ok=false` で安全側を維持。

検証:

- `python3 -m json.tool notebooks/export_bear_yolo_onnx.ipynb >/dev/null` → OK
- `.venv/bin/python -m py_compile raspberry_pi/camera_ai/bear_detector.py
  raspberry_pi/camera_ai/export_lightweight_yolo.py
  raspberry_pi/camera_ai/train_bear_yolo.py` → OK
- `.venv/bin/python -m pytest tests/test_camera_ai_model_selection.py
  tests/test_camera_ai_approach_logic.py tests/test_decision_logic.py` → 21 passed
- `.venv/bin/python -m pytest` → 52 passed

結果:

- 未コミット変更として記録。Pi 側 runtime install が PyTorch/Ultralytics を引き込まない
  構成になった。
- 前回残課題だった stale テストは `_check_runtime_dependency()` 追加により解消。

残課題:

- Colab 上で修正後 notebook を実行し、`ultralytics` import と ONNX export が通ることを確認する。
- Pi に `models/yolo_bear.onnx` を配置後、`./scripts/run_demo.sh` で `ai_model_ok=true` を確認する。

### 2026-07-06T11:21:38+09:00 — 会場用 Camera AI → Arduino 機構ブリッジ

根拠: 未コミット差分とファイルシステム編集時刻。Gitコミット日時ではない。

目的:

- ハッカソン会場で、USBカメラの熊認識から安全判定ミラーを経由して Arduino の
  機構動作まで一通り確認できる経路を用意する。
- 郷田さんの最新 `Haruka GODA/beehivemotorC++/0to90.ino` に合わせ、
  Arduino メインスケッチを D3 直結サーボでも動くようにする。

変更ファイル:

- `arduino_uno_q/contact_pad_controller/config.h`
- `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino`
- `arduino_uno_q/contact_pad_controller/README.md`
- `raspberry_pi/integration/safety_to_actuator.py` (新規)
- `scripts/run_demo.sh`
- `raspberry_pi/README.md`
- `README.md`, `README.ja.md`, `README.zh-CN.md`
- `tests/test_safety_to_actuator.py` (新規)
- `DEVELOPMENT_NOTES.md`

変更内容:

- `GODA_ACTUATOR_MODE_DIRECT_SERVO` / `GODA_ACTUATOR_MODE_PCA9685` を追加し、
  既定を郷田さんの `0to90.ino` と同じ D3 直結サーボに変更。
- `contact_pad_controller.ino` の actuator layer を `Servo.h` direct servo と
  PCA9685 の条件コンパイルに分離。状態機械、timeout、cooldown、ERROR_SAFE は維持。
- Arduino JSON Lines に `actuator_mode` を追加し、会場で direct/PCA9685 の
  どちらを書き込んだか確認できるようにした。
- `safety_to_actuator.py` を追加。`feeding_decision_log.csv` の最新行が新鮮で
  `RELEASE_ON` の時だけ Arduino に `RELEASE` を送り、欠損・古いログ・ERROR_SAFE・
  emergency stop では `STOP` 側に倒す。
- `run_demo.sh` に `RUN_ACTUATOR_BRIDGE=1` と `ACTUATOR_BRIDGE_NO_SERIAL=1` を追加。
  既定は bridge OFF なので、不意に機構は動かない。
- README に会場用コマンド
  `RUN_CAMERA_AI_INFERENCE=1 RUN_ACTUATOR_BRIDGE=1 ./scripts/run_demo.sh` を追記。

安全・インターフェースへの影響:

- Arduino Uno Q の現場側状態機械が引き続き RELEASE_ON/OFF の最終 gate を持つ。
- Pi bridge は安全CSVの `RELEASE_ON` を Arduino の `RELEASE` デモ入力に変換するだけで、
  Arduino 側の release timeout / cooldown / ERROR_SAFE を迂回しない。
- bridge は明示的に `RUN_ACTUATOR_BRIDGE=1` を指定した時だけ起動する。
- 欠損、stale、ERROR_SAFE、emergency stop、例外時は `STOP` または no-release。

検証:

- `arduino-cli lib install Servo` → Servo 1.3.0 installed
- `arduino-cli compile --fqbn arduino:avr:uno arduino_uno_q/contact_pad_controller`
  → OK (direct servo mode, 10156 bytes / SRAM 1239 bytes)
- `arduino-cli compile --fqbn arduino:avr:uno --build-property
  compiler.cpp.extra_flags=-DGODA_ACTUATOR_MODE=1 arduino_uno_q/contact_pad_controller`
  → OK (PCA9685 mode, 14212 bytes / SRAM 1433 bytes)
- `bash -n scripts/run_demo.sh` → OK
- `.venv/bin/python -m py_compile raspberry_pi/integration/safety_to_actuator.py
  raspberry_pi/camera_ai/run_camera_ai.py raspberry_pi/camera_ai/bear_detector.py` → OK
- `.venv/bin/python -m pytest` → 57 passed
- `timeout 4 env RUN_CAMERA_AI=0 RUN_SAFETY_CONTROL=1 SAFETY_INPUT_MODE=scenario
  RUN_ACTUATOR_BRIDGE=1 ACTUATOR_BRIDGE_NO_SERIAL=1 RUN_DASHBOARD=0 ./scripts/run_demo.sh`
  → 起動確認 OK、timeout 終了コード 124 は想定通り

結果:

- 会場用に「Camera AI / safety CSV / Arduino serial / servo mechanism」の経路を
  1コマンドで起動できるようになった。
- 実機シリアルなしの no-serial bridge では startup `STOP` ログを確認。

残課題:

- Arduino IDE または `arduino-cli upload` で direct servo 版スケッチを Uno Q に書き込む。
- `models/yolo_bear.onnx` が Pi に無い場合は、修正済み Colab notebook で生成して配置する。
- 実機接続後、`RUN_CAMERA_AI_INFERENCE=1 RUN_ACTUATOR_BRIDGE=1 ./scripts/run_demo.sh` を起動し、
  `data/logs/camera_ai.status.log`, `feeding_decision_log.csv`,
  `actuator_bridge.status.log` を見ながら `ai_model_ok=true` と機構動作を確認する。
