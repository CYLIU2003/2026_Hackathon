# A1 Front Paw Contact Pad System

## 개요

이 저장소는 A1 **Bear Honey Buffet** 해커톤 프로젝트의 **Front Paw Contact Pad System** 프로토타입을 다룬다.

현재 프로토타입은 시뮬레이션 입력과 접촉 패드 제어에 더해 Raspberry Pi 카메라 AI 인식 모듈을 포함한다. 곰 또는 대상 물체의 접근을 감지하고, 앞발 접촉 또는 향후 전기저항/접촉 패드 입력을 확인하며, 꿀 잔량과 안전 상태를 확인한 뒤 꿀 방출 신호를 안전하게 판단한다.

카메라 AI는 추가 인식 레이어이며, 단독 안전 제어기가 아니다. YOLO 감지만으로 꿀을 방출해서는 안 된다.

제어 로직의 초기 버전은 여전히 **시뮬레이션 센서 입력** 만으로도 동작할 수 있다. 기존 Arduino/접촉 패드와 전기저항 접촉 확인 경로는 저장소에 유지하며, 이후 별도로 통합한다.

---

## 프로젝트 비전

A1 시스템 전체는 네 개의 레이어로 나뉜다.

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

이 저장소는 인식, 접촉 확인, 안전 판단 로직, 로그 기록, 데모 지원을 담당한다. 꿀 방출 구동 측은 단순한 RELEASE_ON/OFF 인터페이스와 이후 PCA9685 + 서보 통합으로 다룬다.

---

## 이 시스템이 수행하는 일

이 시스템은 다음을 확인한다.

```text
1. 곰 또는 대상 물체가 접근하는가       ai_bear_approaching / bear_detected
2. 앞발이 접촉 패드에 닿았는가           paw_contact / raw_contact_value
3. 꿀의 양이 충분한가                    honey_amount_percent
4. 시스템이 안전 상태인가                system_safe
5. 비상 정지가 눌리지 않았는가           emergency_stop == false
6. 꿀 방출 메커니즘을 작동해도 되는가    RELEASE_ON / RELEASE_OFF
```

모든 조건을 만족하면 다음을 출력한다.

```text
RELEASE_ON
```

조건 중 하나라도 만족하지 않으면 다음을 출력한다.

```text
RELEASE_OFF
```

---

## 하드웨어 개념

### Arduino Uno Q

Arduino Uno Q 는 현장 측 접촉 확인 및 안전 제어 보드로 유지한다.

주요 역할:

```text
- 접촉 패드 입력
- 향후 전기저항/접촉 측정
- 시뮬레이션 센서 입력
- 임계값 판단
- 꿀 방출 판단 로직
- LED / GPIO / release signal 출력
- serial 또는 network 통신
```

Arduino Uno Q / 전기저항 측정 / 접촉 패드 로직은 문서와 구현에서 계속 유지해야 한다. camera AI 는 `ai_bear_approaching` 을 추가할 수 있지만, `paw_contact`, `raw_contact_value`, 접촉 임계값, 비상 정지, RELEASE_OFF fail-safe 동작을 대체하지 않는다.

Arduino Uno Q 는 Linux를 실행할 수 있는 MPU 측과 실시간 제어용 MCU 측을 함께 갖는 구조이므로, 현장 제어에 적합하다.

참고:

```text
https://docs.arduino.cc/hardware/uno-q
https://docs.arduino.cc/tutorials/uno-q/user-manual/
```

### Raspberry Pi 4B

Raspberry Pi 4B 4GB 는 AI 카메라 인식, 로그 기록, 상위 상태 처리에 사용한다.

주요 역할:

```text
- BUFFALO BSW500M USB 카메라에서 이미지 캡처
- OpenCV / V4L2 카메라 캡처 실행
- 경량 YOLO로 곰 접근 감지
- ai_bear_approaching 상태 출력
- Arduino Uno Q 에서 상태 데이터 수신
- CSV 로그 저장
- 대시보드 표시
- 최신 상태 시각화
- 발표용 데모 지원
- SSH / Tailscale 등을 통한 원격 확인
```

Raspberry Pi 를 유일한 안전 제어기로 사용해서는 안 된다. 카메라 AI는 추가 인식 레이어이며, 단독 안전 제어기가 아니다.

### BUFFALO BSW500M USB 카메라

BUFFALO BSW500M USB 웹 카메라는 Raspberry Pi 4B 에 연결한다.

```text
- /dev/video0: 실제 이미지 스트림 장치
- /dev/video1: metadata device, 이미지 캡처에 사용하지 않음
- 권장 FourCC: 먼저 MJPG, 실패 시 YUYV fallback
- 권장 해상도: 먼저 640x480, 실패 시 320x240 fallback
```

### PCA9685 + 서보 모터

PCA9685 + 서보 모터 + 외부 전원은 꿀 방출 메커니즘 측 구동에 사용한다.

```text
- 입력: RELEASE_ON / RELEASE_OFF
- 역할: 데모용 꿀 방출 메커니즘 구동
- 안전: 제어 없는 방출 금지. 기본 상태는 RELEASE_OFF
```

---

## 시스템 아키텍처

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

첫 번째 MVP에서는 다음을 구현한다.

### 입력

```text
simulated_bear_detected
ai_bear_approaching
simulated_paw_contact
raw_contact_value
simulated_honey_amount_percent
simulated_system_safe
emergency_stop
```

### 로직

```text
release_allowed = (
    ai_bear_approaching
    and paw_contact
    and honey_amount_percent >= honey_min_threshold_percent
    and system_safe
    and not emergency_stop
)
```

### 출력

```text
- RELEASE_ON / RELEASE_OFF
- LED ON/OFF
- JSON Lines over serial
- CSV log on Raspberry Pi
- Camera AI JSON Lines / CSV state
```

---

## 상태 머신

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

오류 발생 시:

```text
ANY_STATE
  ↓ invalid data / emergency stop / communication error
ERROR_SAFE
  ↓ reset
IDLE
```

`ERROR_SAFE` 상태에서는 반드시 `RELEASE_OFF` 로 유지한다.

---

## 안전 정책

이 프로젝트는 해커톤용 프로토타입이며, 사람이나 동물에게 해를 끼쳐서는 안 된다.

금지 사항:

```text
- 접촉 패드에 고전압 또는 대전류 사용
- 전기 충격 장치 설계
- 전문가 감독 없이 실제 곰으로 테스트
- 유효한 측정 없이 실제 곰의 저항값이라고 주장
- 안전 정지 없이 꿀 방출 제어
```

반드시 지킬 것:

```text
- 초기 상태와 이상 상태는 RELEASE_OFF
- 실제 센서가 없을 때는 시뮬레이션 입력 사용
- 카메라 AI는 추가 인식 레이어이며, 단독 안전 제어기가 아니다
- YOLO 감지만으로 꿀 방출을 허용하지 않는다
- RELEASE_ON 에 시간 제한 설정
- 중요한 상태 변화는 로그로 기록
- 접촉 패드 제어와 벌집 메커니즘을 분리
```

꿀 방출은 필요한 조건이 모두 만족될 때만 허용한다.

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

## 데이터 형식

Arduino Uno Q 에서 Raspberry Pi 로 JSON Lines 를 전송한다.

예시:

```json
{"timestamp":"2026-05-23T18:30:00+09:00","bear_detected":false,"paw_contact":false,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_OFF","state":"IDLE","event":"IDLE"}
{"timestamp":"2026-05-23T18:30:05+09:00","bear_detected":true,"paw_contact":true,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_ON","state":"RELEASING","event":"RELEASE_START"}
```

Raspberry Pi 측에서는 CSV 로그로 저장한다.

예시:

```csv
timestamp,bear_detected,paw_contact,honey_amount_percent,system_safe,emergency_stop,release_state,state,event
2026-05-23T18:30:00+09:00,false,false,80,true,false,RELEASE_OFF,IDLE,IDLE
2026-05-23T18:30:05+09:00,true,true,80,true,false,RELEASE_ON,RELEASING,RELEASE_START
```

Camera AI 도 Raspberry Pi 에서 JSON Lines 를 출력한다.

```json
{"source":"camera_ai","ai_camera_ok":true,"ai_model_ok":true,"ai_bear_detected":true,"ai_bear_confidence":0.82,"ai_bear_box_area_ratio":0.18,"ai_bear_approaching":true,"event":"AI_BEAR_APPROACHING"}
```

이 camera AI 필드는 안전 판단 레이어의 입력일 뿐이며, `RELEASE_ON` 을 직접 명령하지 않는다.

---

## 권장 저장소 구조

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
│  └─ yolo_bear.pt
├─ outputs/
│  └─ camera_test.jpg
├─ examples/
│  └─ sample_log.csv
└─ scripts/
   └─ run_demo.sh
```

---

`models/` 와 `outputs/` 는 실행 및 데모 때 사용하는 폴더이다.
모델 가중치와 카메라 출력 이미지는 팀이 작은 샘플을 남기기로 정한 경우를 제외하고 보통 Git에 커밋하지 않는다.

---

## Camera AI 모듈

Camera AI 모듈은 Raspberry Pi 4B 4GB 와 BUFFALO BSW500M USB 웹 카메라에서 동작한다.

카메라 AI는 추가 인식 레이어이며, 단독 안전 제어기가 아니다.

하드웨어 및 실행 전제:

```text
- 대상 장치: Raspberry Pi 4B 4GB
- 카메라: BUFFALO BSW500M USB 웹 카메라
- 캡처 장치: /dev/video0
- metadata device: /dev/video1, 캡처에 사용하지 않음
- 모델 경로: models/yolo_bear.pt
- 권장 해상도: 640x480 또는 320x240
- 권장 FourCC: 먼저 MJPG, 실패 시 YUYV fallback
- 실패 동작: ai_bear_approaching=false
```

`models/yolo_bear.pt` 가 없으면 시스템은 `AI_MODEL_LOAD_ERROR` 를 출력하고, `ai_model_ok=false` 로 설정하며 fail-safe 상태를 유지한다.

Camera AI 실행 명령:

```bash
python3 -m compileall -q raspberry_pi/camera_ai
python3 raspberry_pi/camera_ai/camera_test.py --device /dev/video0
python3 -m raspberry_pi.camera_ai.run_camera_ai --terminal-status --no-jsonl --once
```

카메라 디버그 명령:

```bash
lsusb
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext
fuser -v /dev/video0
```

---

## 각 폴더의 역할

| 경로 | 역할 |
|---|---|
| `arduino_uno_q/contact_pad_controller/` | Arduino Uno Q 메인 제어. 시뮬레이션 입력, 접촉 패드 상태 머신, 꿀 양 임계값 판단, RELEASE_ON/OFF 출력, LED/GPIO, JSON Lines 출력을 담당한다. |
| `raspberry_pi/logger/` | Raspberry Pi 시리얼 로거. Arduino와 AI의 JSON Lines를 수신하여 CSV 로그로 저장한다. |
| `raspberry_pi/dashboard/` | 데모 및 모니터링용 대시보드. 접촉 상태, AI 상태, 방출 상태를 함께 표시한다. |
| `raspberry_pi/camera_ai/` | 선택적인 카메라 AI 인식 레이어. `/dev/video0` 카메라 테스트, YOLO 로드, 곰 접근 추정, AI 상태 출력을 담당한다. 단, 꿀 방출을 직접 명령해서는 안 된다. |
| `docs/` | 블록 다이어그램, 상태 머신, 인터페이스 사양, camera AI 설계 메모 등 설계 문서. |
| `data/logs/` | 실행 시 생성되는 CSV/JSONL 로그 폴더. 작은 샘플을 제외한 생성 로그는 보통 Git에 커밋하지 않는다. |
| `examples/` | 데모와 설명에 쓰는 작은 샘플 입출력 파일. |
| `models/` | 로컬 YOLO 모델 가중치 폴더. 기대 경로는 `models/yolo_bear.pt` 이다. 기본적으로 Git에 커밋하지 않는다. |
| `outputs/` | 카메라 테스트 이미지와 임시 데모 출력. 기본적으로 Git에 커밋하지 않는다. |
| `scripts/` | 데모 실행 보조 스크립트. |
| `tests/` | 판단 로직과 camera AI 보조 처리에 대한 Python 테스트. |
| 루트 파일 | 프로젝트 전체 지시, 안전 가드레일, 변수 목록, 다국어 README를 둔다. |

---

## 개발 로드맵

### Phase 1: 시뮬레이션 제어 로직

```text
[ ] 곰/접촉/꿀 잔량/안전 상태 시뮬레이션 입력
[ ] RELEASE_ON/OFF 판단 로직
[ ] 비상 정지와 RELEASE_OFF fail-safe
[ ] JSON Lines 출력
```

### Phase 2: Raspberry Pi 카메라 단독 테스트

```text
[ ] BUFFALO BSW500M 을 Raspberry Pi 4B 에 연결
[ ] /dev/video0 이 이미지 스트림인지 확인
[ ] /dev/video1 은 이미지 캡처에 사용하지 않음
[ ] camera_test.py 로 1프레임 캡처
```

### Phase 3: YOLO 모델 배치와 AI 추론

```text
[ ] models/yolo_bear.pt 배치
[ ] AI_MODEL_LOAD_ERROR 가 사라지는지 확인
[ ] 카메라 프레임에 YOLO 추론 실행
[ ] ai_bear_approaching 을 fail-safe 로 출력
```

### Phase 4: AI 상태 로깅과 대시보드 통합

```text
[ ] camera AI JSON Lines / CSV 기록
[ ] ai_camera_ok 와 ai_model_ok 표시
[ ] ai_bear_detected 와 ai_bear_approaching 표시
[ ] 접촉 상태와 방출 상태를 함께 표시
```

### Phase 5: 저항/접촉 패드 통합

```text
[ ] Arduino Uno Q 접촉 패드 로직 유지
[ ] raw_contact_value 추가 또는 검증
[ ] 접촉 임계값 로직 추가
[ ] 안전한 더미 물체로만 테스트
```

### Phase 6: PCA9685 / 서보 꿀 방출 통합

```text
[ ] PCA9685 와 외부 서보 전원 연결
[ ] RELEASE_ON/OFF 를 안전한 서보 동작에 매핑
[ ] 방출 timeout 과 cooldown 추가
[ ] 리셋 또는 오류 시 RELEASE_OFF 기본값 확인
```

### Phase 7: Fail-Safe 포함 전체 시스템 데모

```text
[ ] Camera AI 가 접근을 감지
[ ] 접촉/저항 레이어가 paw_contact 확인
[ ] 꿀 잔량과 안전 조건 통과
[ ] 비상 정지가 RELEASE_OFF 강제
[ ] YOLO 감지만으로 꿀을 방출하지 않음
```

---

## 팀 설명문

```text
I will develop the front paw contact pad system as a separate electronic/control module.
Raspberry Pi 4B with a BUFFALO BSW500M camera will be used for YOLO-based bear approach detection, logging, and dashboard support.
Arduino Uno Q and the contact/resistance layer remain responsible for contact confirmation and fail-safe release logic.
PCA9685 and a servo motor will be used on the honey release mechanism side.
Camera AI is an additional perception layer, not the only safety controller.
```

---

## 현재 가정

```text
- 벌집 메커니즘 측은 단순한 RELEASE_ON/OFF 신호를 받을 수 있다
- Raspberry Pi 4B 는 BUFFALO BSW500M 의 /dev/video0 을 이미지 캡처에 사용한다
- /dev/video1 은 metadata이며 이미지 캡처에 사용하지 않는다
- 물리 접촉/저항 통합은 camera AI 와 별도로 유지한다
- PCA9685 + 서보 모터 + 외부 전원은 액추에이터 측에서 사용한다
- 실제 동물 테스트는 하지 않는다
- 이 프로젝트는 해커톤용 개념 검증이다
```

---

## MVP v0.1 완료 조건

```text
[ ] Uno Q 가 시뮬레이션 입력을 생성할 수 있다
[ ] Uno Q 가 RELEASE_ON/OFF 를 판단할 수 있다
[ ] Raspberry Pi 가 /dev/video0 에서 이미지를 캡처할 수 있다
[ ] Camera AI 가 fail-safe ai_bear_approaching 을 출력할 수 있다
[ ] LED 또는 serial 로 RELEASE_ON/OFF 를 확인할 수 있다
[ ] Raspberry Pi 가 상태 데이터를 수신할 수 있다
[ ] Raspberry Pi 가 CSV 로그를 저장할 수 있다
[ ] 이상 상태에서 RELEASE_OFF 로 돌아간다
[ ] YOLO 감지만으로 꿀 방출을 트리거할 수 없다
[ ] README에 시스템 동작 방식이 설명되어 있다
[ ] 팀이 접촉 패드와 벌집 메커니즘의 경계를 이해할 수 있다
```

---

## 시작하기 (MVP 시뮬레이션)

이 프로토타입은 **시뮬레이션 센서 입력** 만으로도 동작한다. 실제 센서가 없어도 먼저 제어 로직을 확인할 수 있다.

### Arduino Uno Q

1. `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino` 를 연다.
2. Arduino Uno Q 에 빌드하고 업로드한다.
3. 시리얼 모니터를 **115200 baud** 로 연다.
4. JSON Lines 출력을 확인한다.

### Raspberry Pi 로거

1. 의존성을 설치한다.
   ```bash
   pip install -r raspberry_pi/logger/requirements.txt
   ```
2. 로거를 실행한다.
   ```bash
   python raspberry_pi/logger/serial_logger.py --serial-port /dev/ttyACM0 --baudrate 115200
   ```
3. CSV 로그는 `data/logs/` 에 저장된다.

### Raspberry Pi Camera AI

1. 경량 YOLO 모델을 `models/yolo_bear.pt` 에 배치한다.
2. 카메라를 확인한다.
   ```bash
   python3 raspberry_pi/camera_ai/camera_test.py --device /dev/video0
   ```
3. AI를 한 번 실행한다.
   ```bash
   python3 -m raspberry_pi.camera_ai.run_camera_ai --terminal-status --no-jsonl --once
   ```

### Raspberry Pi 대시보드

1. 의존성을 설치한다.
   ```bash
   pip install -r raspberry_pi/dashboard/requirements.txt
   ```
2. 대시보드를 실행한다.
   ```bash
   python raspberry_pi/dashboard/app.py --log-dir data/logs --host 0.0.0.0 --port 8080
   ```
3. `http://<pi-ip>:8080` 을 열어 최신 상태를 확인한다.

---

## 데이터 형식 메모

- Arduino Uno Q 는 **JSON Lines** 를 전송한다.
- Camera AI 도 **JSON Lines** 를 전송한다.
- Raspberry Pi 는 **CSV 로그** 를 저장한다.
- 실시간 시계가 추가되기 전까지 `timestamp` 는 **uptime** (`T+<ms>`) 으로 취급한다.
- 전체 schema는 `docs/interface_spec.md` 와 `docs/camera_ai_interface_spec.md` 를 참고한다.

---

## 한 문장 요약

이 프로젝트는 Raspberry Pi 4B와 BUFFALO BSW500M USB 카메라를 사용하여 YOLO 기반 곰 접근 감지를 수행하며, 기존 Arduino/접촉 패드 안전 판단 로직을 유지하여 AI 감지, 접촉 확인, 꿀 잔량, 안전 조건이 모두 만족될 때만 꿀 방출을 허용한다.
