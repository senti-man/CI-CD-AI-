# AI 공급망 공격 시뮬레이션 (팀 프로젝트용 데모)

전부 로컬(127.0.0.1)에서만 도는 완전 무해한 시뮬레이션입니다. 실제
악성코드가 아니고 외부로 나가는 통신도 전혀 없습니다. AV에 걸릴 일 없게
일부러 난독화나 회피 기법 없이 평문 코드로만 짰습니다.

## 1. 한 줄 비유

레고 조립 설명서 앱을 다운로드했는데, 그 앱이 설치되는 순간 몰래 방 사진을
찍어서 낯선 사람한테 보내버린다고 상상해보시면 됩니다. 개발자들도 코드
짤 때 남이 만든 부품(패키지), AI 도구(MCP 서버), 남이 학습시킨 AI 모델
파일을 수없이 가져다 씁니다. 공격자는 그 부품 중 하나에 몰래 나쁜 코드를
심어두고, 개발자가 그걸 설치하거나 쓰거나 불러오기만 해도 그 코드가
자동으로 돌게 만듭니다. 이게 AI 공급망 공격입니다.

이 프로젝트는 같은 원리를 트리거만 다르게 해서 세 가지 경로로
재현했습니다.

| 경로 | 트리거 시점 | 폴더 |
|---|---|---|
| ① 악성 오픈소스 패키지 | `pip install` 후 `import`하는 순간 | `malicious_package/`, `fake_victim/` |
| ② 악성 MCP 서버 | AI 에이전트가 그 서버의 '도구'를 호출하는 순간 | `mcp_attack/` |
| ③ 오염된 AI 모델 파일 | `pickle.load()`로 모델을 불러오는 순간 | `poisoned_model/` |

세 경로 다 같은 공격자 C2 서버(`attacker_c2/c2_server.py`, 127.0.0.1:8899)로
신호를 보내게 만들어서, 공격자 한 명이 여러 침투 경로를 동시에 운영하는
실제 공격 인프라의 모습을 흉내 냈습니다. `artifacts/c2_log.jsonl` 하나에
세 경로의 로그가 전부 쌓입니다.

## 2. 빠른 실행

```bash
# ① 악성 패키지 시나리오
python run_demo.py

# ② 악성 MCP 서버 시나리오
python mcp_attack/run_mcp_demo.py

# ③ 오염된 모델 파일 시나리오
python poisoned_model/run_model_demo.py

# 아무 시나리오나 실행하면서 타임라인(프로세스/네트워크/파일시스템/C2로그)을 동시에 캡처
python analysis/capture_timeline.py run_demo.py
python analysis/capture_timeline.py mcp_attack/run_mcp_demo.py
python analysis/capture_timeline.py poisoned_model/run_model_demo.py
```

결과물은 전부 `artifacts/` 폴더에 쌓입니다(`c2_log.jsonl`, `timeline.csv`,
`SIMULATED_persistence_marker_*.txt`). 이 폴더가 팀원들이 포렌식 실습할
"증거"입니다.

## 3. 시나리오별 공격 흐름

### ① 악성 패키지 (`malicious_package/`)

```
공격자가 "ai-lint-helper"라는 이름으로 그럴듯한 패키지를 배포
        ↓
개발자가 requirements.txt로 무심코 같이 설치 (pip install)
        ↓
개발자가 실제로 import ai_lint_helper (사용하는 순간)
        ↓
모듈 최상단 코드가 즉시 실행 → 정찰 + 가짜 비밀파일 읽기 + C2 전송 + 지속성 흔적
```

### ② 악성 MCP 서버 (`mcp_attack/`)

```
공격자가 "smart-code-formatter"라는 MCP 서버를 배포
        ↓
개발자가 AI 에이전트 설정에 이 서버를 추가 (한 번만 설정하면 이후 자동 신뢰)
        ↓
AI가 정상적인 코딩 작업 중 "format_code" 도구를 호출
        ↓
도구 핸들러 코드가 실행되는 순간 → 정찰 + 가짜 비밀파일 읽기 + C2 전송
        ↓
AI/개발자 눈에는 "정상적으로 포맷된 코드" 결과만 보임 (악성 행위는 안 보임)
```

### ③ 오염된 AI 모델 파일 (`poisoned_model/`)

```
공격자가 "super-resolution-v2"라는 pretrained 모델 체크포인트(.pkl)를 커뮤니티에 배포
        ↓
개발자가 그 모델을 pickle.load()로 불러옴 (그냥 쓰려고 로드했을 뿐)
        ↓
pickle의 __reduce__ 메커니즘이 파일에 내장된 코드를 그대로 exec()로 실행
        ↓
정찰 + 가짜 비밀파일 읽기 + C2 전송 (외부 모듈 없이 파일 자체에 코드가 내장됨)
```

## 4. 탐지 도구 (`detection/`)

| 도구 | 대상 | 방식 |
|---|---|---|
| `suspicious_pattern.yar` + `mini_yara_matcher.py` | 패키지 소스코드 (텍스트) | 문자열 패턴 기반 (YARA `N of (...)`) |
| `pickle_safety_scanner.py` | 모델 파일 (바이너리 pickle opcode) | opcode 디스어셈블 후 위험한 GLOBAL/STACK_GLOBAL 탐지 (실행 없이 정적 탐지) |

```bash
python detection/mini_yara_matcher.py
python detection/pickle_safety_scanner.py poisoned_model/malicious_model.pkl
```

학원 실습 환경에 진짜 `yara`/`yara-python`이 깔려 있다면 `suspicious_pattern.yar`
파일을 그대로 쓰시면 됩니다(`yara detection/suspicious_pattern.yar 대상파일`).
이 PC는 Python 3.14용 사전 빌드 wheel이 없어서 대신 미니 매처를 만들어
썼습니다.

두 도구가 다른 이유는 이렇습니다. 패키지 코드는 사람이 읽는 평문
텍스트라서 문자열 매칭(YARA)이 잘 통하는데, pickle 모델 파일은 바이너리
opcode 스트림이라 "무슨 함수를 참조하는지"를 구조적으로 봐야 합니다.
탐지 기법은 파일 형식에 맞춰서 골라야 한다는 게 이 비교에서 얻을 수
있는 교훈입니다.

## 5. 타임라인/동적 분석 (`analysis/`)

`analysis/capture_timeline.py`는 시나리오 실행 중 아래 세 가지 증거를 모아
시간순으로 정렬한 `artifacts/timeline.csv`를 만듭니다.

- 프로세스 생성/종료 (psutil)
- 네트워크 연결 (psutil, best-effort — 아주 짧은 연결은 놓칠 수 있어서 아래 C2 로그로 보완함)
- C2 서버 수신 로그 (`c2_log.jsonl`) — 언제 무엇을 전송했는지 가장 믿을 만한 증거

실제로 pip 시나리오를 캡처해보면 재밌는 게 하나 걸립니다. pip가
자체적으로 `151.101.0.223:443`(PyPI/Fastly CDN)으로 연결하는 게 같이
찍히는데, 이건 "새 pip 버전이 있다"는 정상 알림 확인용 트래픽입니다.
낯선 네트워크 연결이 다 악성인 건 아니고, 정상과 비정상을 가려내는 것
자체가 분석의 핵심이라는 걸 팀원들과 같이 확인해보면 좋은 토론거리가
됩니다.

`analysis/static_analysis_report.md`는 ①번 시나리오 기준으로 써본 정적
분석 리포트 예시입니다. 팀 보고서 템플릿으로 그대로 갖다 쓰셔도 됩니다.

## 6. IoC / TTP 요약

### IoC (침해지표)
- 네트워크: `127.0.0.1:8899`(실환경이면 낯선 외부 IP:PORT)로의 `POST /beacon`
- 파일: `ai-lint-helper` 패키지, `smart-code-formatter` MCP 서버 바이너리, `malicious_model.pkl`
- 파일시스템 흔적: `SIMULATED_persistence_marker_*.txt`
- 행위: 설치/도구호출/모델로드 직후 곧바로 아웃바운드 HTTP가 발생함 (정상 도구라면 있을 수 없는 타이밍)

### MITRE ATT&CK 매핑

| 단계 | Technique | 관련 시나리오 |
|---|---|---|
| 초기 침투 | T1195.001/.002 - Supply Chain Compromise | ①②③ 전체 |
| 실행 | T1059.006 - Command and Scripting Interpreter: Python | ①②③ 전체 |
| 실행 (역직렬화) | T1204 / CWE-502 Deserialization of Untrusted Data | ③ |
| 탐색/정찰 | T1082 - System Information Discovery | ①②③ 전체 |
| 수집 | T1005 - Data from Local System | ①②③ 전체 |
| 명령 및 제어 | T1071.001 - Application Layer Protocol: Web Protocols | ①②③ 전체 |
| 유출 | T1041 - Exfiltration Over C2 Channel | ①②③ 전체 |
| 지속성(시뮬레이션) | T1547 - Boot or Logon Autostart Execution | ① |
| AI 특화 신뢰 남용 | AI 에이전트가 도구 설명(description)만 보고 자동으로 신뢰/실행 | ② (MCP 고유 위협면) |

## 7. 팀 프로젝트 역할 배분 아이디어 (6~7인, 2~3주)

| 역할 | 인원 | 할 일 |
|---|---|---|
| 시나리오 A (패키지) 담당 | 1~2 | ① 흐름 재검증, 정적/동적 분석 리포트 고도화, YARA 룰 튜닝 |
| 시나리오 B (MCP) 담당 | 1~2 | ② 흐름 재검증, "도구 설명만 보고 신뢰"하는 문제를 더 깊게 분석해서 발표 |
| 시나리오 C (모델 파일) 담당 | 1~2 | ③ 흐름 재검증, pickle_safety_scanner 고도화(위험 함수 더 추가), safetensors 같은 안전한 대안 조사 |
| 타임라인/보고서 담당 | 1 | `capture_timeline.py`로 세 시나리오 전부 캡처해서 통합 타임라인과 최종 보고서 작성 |

공통 산출물은 팀 보고서(사고 원인 → 공격 흐름 → IoC/TTP → 탐지 방법 →
대응 방안)와 발표용 데모 시연입니다. 위 "빠른 실행" 명령어 그대로 라이브
데모가 가능합니다.

## 8. 안전 설계 관련 메모

- 모든 통신은 `127.0.0.1`로 고정해서 절대 외부로 안 나갑니다.
- 훔치는 "비밀 파일"에는 완전 가짜 값만 들어있습니다(`sk-FAKE...` 등).
- 지속성(재부팅 후에도 살아남기)은 실제 레지스트리나 시작프로그램을
  건드리지 않고, "이런 흔적이 남았을 것"이라는 텍스트 파일로만
  시뮬레이션했습니다.
- pickle RCE도 정찰과 beacon까지만 하고 파일 삭제나 랜섬웨어 같은 실제
  파괴적 행위는 없습니다.
- 코드에 난독화나 인코딩, 회피 기법을 안 넣었습니다. 실제 악성코드가
  아니라서 AV 오탐 걱정 없이 누구나 코드를 읽고 분석 연습을 할 수
  있습니다.
- 다 지우고 싶으면 이 폴더(`ai_supply_chain_demo/`) 통째로 삭제하면
  끝입니다(`.venv` 포함).
