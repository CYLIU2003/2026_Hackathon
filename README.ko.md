# A1 Front Paw Contact Pad System

## 개요

이 저장소는 A1 **Bear Honey Buffet** 해커톤 프로젝트의 **Front Paw Contact Pad System** 프로토타입을 다룬다.

이 시스템의 목적은 곰이 접근하여 앞발로 접촉 패드를 눌렀는지 감지하거나 시뮬레이션하고, 그 결과에 따라 벌집 메커니즘에 안전한 꿀 방출 신호를 보내는 것이다.

초기 버전에서는 실제 센서가 필수는 아니다.  
센서가 아직 준비되지 않은 단계에서도 개발을 진행할 수 있도록, 먼저 시뮬레이션 입력으로 제어 로직을 검증한다.

---

## 프로젝트 비전

A1 시스템 전체는 크게 두 부분으로 나뉜다.

```text
[Bear]
  ↓
[Front Paw Contact Pad System]  ← 이 저장소 / LIU 담당
  ↓ release signal
[Honeycomb / Bee Hive Mechanism] ← Goda 담당
  ↓
[Honey is released]
```

이 저장소는 전자 제어, 감지 로직, 로그 기록, 데모 표시 부분만 담당한다.

---

## 이 시스템이 수행하는 일

Front Paw Contact Pad System 은 다음을 확인한다.

```text
1. 곰이 도착했는가
2. 앞발이 접촉 패드에 닿았는가
3. 꿀의 양이 충분한가
4. 시스템이 안전 상태인가
5. 꿀 방출 메커니즘을 작동시켜도 되는가
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

Arduino Uno Q 는 현장 측 메인 제어 보드로 사용한다.

주요 역할:

```text
- 접촉 패드 입력
- 시뮬레이션 센서 입력
- 임계값 판단
- 꿀 방출 판단 로직
- LED / GPIO / release signal 출력
- serial 또는 network 통신
```

Arduino Uno Q 는 Linux를 실행할 수 있는 MPU 측과 실시간 제어용 MCU 측을 함께 갖는 구조이므로, 현장 제어에 적합하다.

참고:

```text
https://docs.arduino.cc/hardware/uno-q
https://docs.arduino.cc/tutorials/uno-q/user-manual/
```

### Raspberry Pi 4B

Raspberry Pi 4B 는 상위 측 로그 기록, 시각화, 데모 표시 장치로 사용한다.

주요 역할:

```text
- Arduino Uno Q 에서 상태 데이터 수신
- CSV 로그 저장
- 대시보드 표시
- 최신 상태 시각화
- 발표용 데모 지원
- SSH / Tailscale 등을 통한 원격 확인
```

Raspberry Pi 를 유일한 안전 제어기로 사용해서는 안 된다.  
기본적인 방출 판단은 Arduino Uno Q 측에 둔다.

---

## 시스템 아키텍처

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

첫 번째 MVP에서는 다음을 구현한다.

### 입력

```text
simulated_bear_detected
simulated_paw_contact
simulated_honey_amount_percent
simulated_system_safe
emergency_stop
```

### 로직

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

### 출력

```text
- RELEASE_ON / RELEASE_OFF
- LED ON/OFF
- JSON Lines over serial
- CSV log on Raspberry Pi
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
- RELEASE_ON 에 시간 제한 설정
- 중요한 상태 변화는 로그로 기록
- 접촉 패드 제어와 벌집 메커니즘을 분리
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

## 개발 로드맵

### Phase 1: 설계

```text
[ ] 블록 다이어그램 작성
[ ] 상태 전이도 작성
[ ] JSON/CSV 인터페이스 정의
[ ] 벌집 메커니즘 측으로 전달할 release signal 정의
```

### Phase 2: Uno Q 단독 프로토타입

```text
[ ] simulated bear_detected input
[ ] simulated paw_contact input
[ ] simulated honey_amount input
[ ] release decision logic
[ ] LED 또는 serial 로 RELEASE_ON/OFF 출력
```

### Phase 3: Raspberry Pi 로거

```text
[ ] Uno Q 에서 JSON Lines 수신
[ ] 메시지 형식 검증
[ ] CSV 로그 저장
[ ] 터미널에 최신 상태 표시
```

### Phase 4: 데모 대시보드

```text
[ ] 최신 bear_detected 표시
[ ] 최신 paw_contact 표시
[ ] honey_amount 표시
[ ] release_state 표시
[ ] 최근 이벤트 로그 표시
```

### Phase 5: 실제 센서로 교체

```text
[ ] simulated bear_detected 를 실제 센서 후보로 교체
[ ] simulated paw_contact 를 실제 센서 후보로 교체
[ ] simulated honey_amount 를 실제 센서 후보로 교체
[ ] 더미 물체로만 테스트
```

---

## 팀 설명문

```text
I will develop the front paw contact pad system as a separate electronic/control module.
Arduino Uno Q will be used as the main controller for simulated sensor inputs and release decision logic.
Raspberry Pi 4B will be used for logging, dashboard, and presentation demo.
Since I do not have real sensors now, I will first build the logic using simulated inputs.
Later, the simulated inputs can be replaced with actual sensors.
```

---

## 현재 가정

```text
- 벌집 메커니즘 측은 단순한 RELEASE_ON/OFF 신호를 받을 수 있다
- 초기 단계에서는 물리 센서를 사용하지 않는다
- 첫 데모에서는 펌프나 밸브 대신 LED/serial 출력을 사용할 수 있다
- 실제 동물 테스트는 하지 않는다
- 이 프로젝트는 해커톤용 개념 검증이다
```

---

## MVP v0.1 완료 조건

```text
[ ] Uno Q 가 시뮬레이션 입력을 생성할 수 있다
[ ] Uno Q 가 RELEASE_ON/OFF 를 판단할 수 있다
[ ] LED 또는 serial 로 RELEASE_ON/OFF 를 확인할 수 있다
[ ] Raspberry Pi 가 상태 데이터를 수신할 수 있다
[ ] Raspberry Pi 가 CSV 로그를 저장할 수 있다
[ ] 이상 상태에서 RELEASE_OFF 로 돌아간다
[ ] README에 시스템 동작 방식이 설명되어 있다
[ ] 팀이 접촉 패드와 벌집 메커니즘의 경계를 이해할 수 있다
```

---

## 한 문장 요약

이 프로젝트는 Arduino Uno Q 를 앞발 접촉 패드의 메인 제어기로 사용하고, Raspberry Pi 4B 를 로그 기록 및 대시보드 장치로 사용한다. 초기에는 시뮬레이션 입력으로 안전한 꿀 방출 판단 로직을 검증하고, 이후 실제 센서로 교체한다.
