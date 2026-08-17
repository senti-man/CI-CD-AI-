# 정적 분석 리포트 (예시) — ai-lint-helper 악성 패키지

팀 프로젝트 보고서 쓸 때 이 형식 그대로 템플릿으로 갖다 쓰셔도 됩니다.
샘플 개요, 정적 분석, 행위 분석, IoC/TTP, 대응방안 순서로 구성했습니다.

## 1. 샘플 개요

| 항목 | 값 |
|---|---|
| 파일명 | `ai_lint_helper/__init__.py` |
| 배포 형태 | PyPI 스타일 패키지 (`ai-lint-helper`), `pip install`로 설치되어 개발 환경에 유입 |
| 파일 크기 | 3,594 bytes |
| SHA256 | `98a21aa5754b6bc1c660264f18cb1930aae5b7138c72e29cf810613a52bbac8d` |
| MD5 | `87c528fe238bd647634554b67b38d887` |
| 위장 기능 | "AI가 짠 코드 스타일을 자동 정리해주는 헬퍼"로 위장 (설치 시 그럴듯한 로그 출력) |

실무에서는 여기에 VirusTotal 조회 결과, 최초 발견 시각, 배포 채널(PyPI
프로젝트 URL, 등록자 계정 나이 등)도 같이 기록합니다.

## 2. 정적 분석 — 코드/문자열 분석

소스가 평문(비난독화) 파이썬이라 바로 읽고 함수 단위로 나눠볼 수
있었습니다.

| 함수 | 역할 | 비고 |
|---|---|---|
| `_looks_legit()` | 정상 도구처럼 보이는 초기화 로그 출력 | 위장(디코이) 목적 |
| `_collect_recon()` | `socket.gethostname()`, `os.environ["USERNAME"]`, `os.getcwd()` 로 호스트/계정/경로 수집 | 정찰(Discovery) |
| `_steal_dummy_secret()` | 로컬 파일(`dummy_secrets.txt`)을 열어 내용을 읽음 | 실제 환경이면 `.env`, `id_rsa`, AWS 자격증명 등을 노릴 위치 |
| `_beacon(payload)` | `urllib.request.urlopen()`으로 외부(여기선 127.0.0.1:8899)에 HTTP POST | C2 통신 |
| `_fake_persistence_marker()` | 파일 생성으로 지속성 흉내 | 실제라면 레지스트리 Run 키/시작프로그램/예약 작업 자리 |

가장 눈에 띄는 건 임포트 시점 실행입니다. 위 함수들이 클래스나
`if __name__ == "__main__"` 안에 있는 게 아니라 모듈 최상단에서 바로
호출됩니다. `import ai_lint_helper` 한 줄만 실행해도 사용자가 함수를
하나도 직접 부르지 않았는데 악성 코드가 전부 돌아간다는 뜻입니다. npm의
`postinstall` 스크립트나 pip 패키지의 `setup.py`, 모듈 임포트 시점 실행과
똑같은, 공급망 공격의 핵심 트릭입니다.

### 의심스러운 API 호출 목록
- `urllib.request.urlopen` — 외부 통신
- `socket.gethostname` — 호스트 정보 수집
- `os.environ.get("USERNAME")` — 계정명 수집
- 파일 `open()` — 로컬 파일 읽기 (자격증명 후보 탐색 패턴: 여러 경로를 순회하며 존재하는 파일을 찾음)

## 3. 행위(동적) 분석 요약

`run_demo.py` 실행 결과 `artifacts/c2_log.jsonl` 에 기록된 실제 수신 데이터:

```json
{
  "recon": {"hostname": "DESKTOP-XXXXX", "user": "Admin", "cwd": "...\\fake_victim"},
  "stolen_preview": "# 이 파일은 100% 가짜 값입니다. ...",
  "event": "beacon"
}
```

패키지 설치 후 단 한 줄(`import ai_lint_helper`)만 실행해도 호스트 정보와
파일 내용 일부가 외부로 전송된다는 걸 실측으로 확인했습니다.

## 4. YARA 탐지

`detection/suspicious_pattern.yar` 룰로 검증 (`detection/mini_yara_matcher.py` 결과):

| 대상 | 결과 |
|---|---|
| `ai_lint_helper/__init__.py` (악성 패키지) | **MATCH** (6/6 문자열 매치, 임계값 3 충족) |
| `attacker_c2/c2_server.py` (공격자 서버 코드) | no match |
| `fake_victim/requirements.txt` | no match |

룰이 악성 패키지만 정확히 탐지하고, 언뜻 관련 있어 보이는 다른 컴포넌트
(C2 서버, requirements 파일)에는 오탐하지 않는다는 걸 확인했습니다.

## 5. IoC 요약

- 파일 해시: 위 SHA256/MD5
- 패키지명: `ai-lint-helper` (부정확한/신뢰되지 않는 출처)
- 네트워크: `POST /beacon` to `127.0.0.1:8899` (실환경이면 낯선 외부 IP:PORT)
- 파일시스템: `SIMULATED_persistence_marker.txt` 생성 흔적

## 6. TTP (MITRE ATT&CK)

README.md의 "MITRE ATT&CK 매핑" 표 참조 (T1195.002, T1059.006, T1082, T1005, T1071.001, T1041, T1547).

## 7. 대응 방안 (예시)

1. 해당 패키지를 의존성에서 즉시 제거하고, 감염된 환경은 재설치/초기화.
2. 사내 패키지 설치를 사설 미러/화이트리스트 레지스트리로 제한 (SBOM 관리).
3. CI/CD에 설치 전 정적 스캔(YARA, 의존성 신뢰도 검사) 단계 추가.
4. 해당 개발자 계정으로 이루어진 이후 활동(커밋, 배포 등) 재검토 — 자격증명 유출 가능성 대비 로테이션.
