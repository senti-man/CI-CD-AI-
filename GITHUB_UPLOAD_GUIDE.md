# GitHub에 프로젝트 올리기 — 처음 하시는 분용

Gitea 때 하셨던 것(저장소 만들기 → 토큰 만들기 → push)이랑 순서가 완전히 똑같습니다. 사이트만 GitHub로 바뀌는 거예요.

---

## 0단계 — 준비 확인

- GitHub 계정이 있어야 합니다 (CVE 리포트 하셨다면 이미 있는 겁니다. github.com에서 오른쪽 위에 로그인 상태인지만 확인하세요).
- 이 컴퓨터에 Git이 설치돼 있는지: PowerShell에서 `git --version` 쳐서 버전이 뜨면 OK.

---

## 1단계 — GitHub에 빈 저장소 만들기 (웹 화면)

1. https://github.com 접속, 로그인
2. 오른쪽 위 **"+"** 아이콘 클릭 → **"New repository"** 클릭
3. 입력 항목:
   - **Repository name**: 원하는 이름 (예: `supply-chain-attack-project`)
   - **Description**: 비워도 됨
   - **Public / Private**: 팀 프로젝트니까 **Private** 추천 (나중에 언제든 Public으로 바꿀 수 있어요)
   - 아래 **"Add a README file"** 체크박스는 **체크하지 마세요** (이미 우리 파일 안에 README가 있어서, 체크하면 나중에 충돌이 생길 수 있어요)
4. 맨 아래 **"Create repository"** 클릭

만들어지면 `https://github.com/내계정/저장소이름` 같은 주소로 빈 저장소 페이지가 뜹니다. 이 주소를 기억해두세요.

---

## 2단계 — 개인 액세스 토큰(PAT) 만들기 (웹 화면)

GitHub도 Gitea 때처럼 비밀번호 대신 토큰으로 인증합니다.

1. 오른쪽 위 **프로필 사진** 클릭 → **Settings**
2. 왼쪽 메뉴 맨 아래 **Developer settings** 클릭
3. 왼쪽 메뉴 **Personal access tokens** → **Tokens (classic)** 클릭
4. **Generate new token** → **Generate new token (classic)** 클릭
5. 입력:
   - **Note**: 아무 이름 (예: `git-push`)
   - **Expiration**: 90 days 정도로 설정 (기간 지나면 새로 만들면 됩니다)
   - 권한 체크박스 중 **`repo`** 하나만 체크 (맨 위 항목, 체크하면 하위 항목들이 자동으로 다 체크됨)
6. 맨 아래 **Generate token** 클릭
7. 화면에 뜬 토큰 값(`ghp_`로 시작하는 긴 문자열)을 **바로 복사**하세요 — 이 화면을 벗어나면 다시 못 봅니다.

---

## 3단계 — 로컬 파일 업로드 (PowerShell)

```powershell
cd C:\Users\Admin\Downloads
git init
git add ONBOARDING.md GITHUB_UPLOAD_GUIDE.md .gitignore ai_supply_chain_demo cicd_supply_chain_demo
git commit -m "init: 공급망 공격 PoC, 제안서, 온보딩 가이드"
git branch -M main
git remote add origin https://<토큰>@github.com/<내계정>/<저장소이름>.git
git push -u origin main
```

- `<토큰>` 자리에 2단계에서 복사한 토큰
- `<내계정>`, `<저장소이름>`은 1단계에서 만든 실제 값으로 바꾸세요
- 만약 이미 `C:\Users\Admin\Downloads`에서 `git init`을 해보신 적이 있다면 `git init`에서 "재초기화" 메시지만 뜨고 에러는 아니니 그냥 넘어가면 됩니다

---

## 4단계 — 확인

`https://github.com/내계정/저장소이름` 새로고침 → 파일들이 올라와 있으면 성공입니다.

---

## 5단계 — 팀원과 공유하기

Private로 만드셨다면 팀원을 직접 초대해야 저장소가 보입니다.

1. 저장소 페이지 → **Settings** 탭
2. 왼쪽 메뉴 **Collaborators** 클릭
3. **Add people** 클릭 → 팀원 GitHub 아이디(또는 가입 이메일) 입력 → 초대

초대받은 팀원은 이메일이나 GitHub 알림으로 초대장이 오고, 수락하면 저장소가 보입니다.

---

## 자주 만나는 문제

- **push할 때 로그인 창이 뜨고 실패한다** → 토큰을 URL에 직접 넣는 3단계 방식을 쓰면 이 문제 자체가 안 생깁니다.
- **`remote origin already exists` 에러** → 이미 remote가 설정돼 있다는 뜻입니다. `git remote set-url origin https://<토큰>@github.com/<내계정>/<저장소이름>.git`로 바꿔주면 됩니다 (Gitea 때 쓰신 것과 같은 명령입니다).
- **비밀번호/토큰에 특수문자가 있어서 명령이 깨진다** → `ONBOARDING.md`의 Q3 항목과 동일한 문제입니다. 작은따옴표로 전체 URL을 감싸세요.
