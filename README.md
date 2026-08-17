# CI/CD·AI 공급망 침해 대응 프로젝트

침해사고 대응(DFIR) 교육 과정의 팀 프로젝트로 만든 저장소입니다. CI/CD 파이프라인과 AI 생태계(패키지·MCP 서버·모델 파일)를 노리는 공급망 공격을 로컬 환경에서 재현하고, 탐지·대응 체계를 구축·검증합니다.

---

## ⚠️ 중요 — 이 저장소에 대해 꼭 알아야 할 것

- **전부 교육 목적의 로컬 시뮬레이션입니다.** 실제 서비스, 실제 계정, 실제 크리덴셜을 대상으로 한 공격이 아닙니다.
- 모든 통신은 각자의 컴퓨터 안(`127.0.0.1`)에서만 이루어지며, 외부 네트워크나 제3자 시스템으로 나가지 않습니다.
- 여기서 "탈취되는" 시크릿/토큰/비밀번호는 **전부 가짜 값**입니다 (`sk-FAKE...`, `fake-deploy-token-...` 등). 실제 서비스 키가 아닙니다.
- 코드에 실제 악성코드 배포 능력(난독화, 회피 기법, 실제 파괴적 행위 등)은 포함돼 있지 않습니다. 누구나 읽고 분석할 수 있도록 평문으로 작성했습니다.
- 이 저장소의 내용을 실제 시스템, 허가받지 않은 제3자 서비스, 공개 오픈소스 프로젝트 등에 적용하지 않습니다.

---

## 폴더 구조

| 경로 | 내용 |
|---|---|
| [`ai_supply_chain_demo/`](ai_supply_chain_demo/) | 악성 패키지·MCP 서버·오염된 AI 모델 파일 시나리오 + 탐지 도구 |
| [`cicd_supply_chain_demo/`](cicd_supply_chain_demo/) | CI/CD 파이프라인(Gitea Actions) 침해 PoC, 탐지 게이트, 포렌식 실습 자료 |
| [`cicd_supply_chain_demo/PROPOSAL.md`](cicd_supply_chain_demo/PROPOSAL.md) | 팀 프로젝트 제안서 (진행 이력, 아키텍처, 일정, 역할 분담 포함) |
| [`ONBOARDING.md`](ONBOARDING.md) | Docker/Git/터미널 기초 + 실전 에러 FAQ |
| [`GITHUB_UPLOAD_GUIDE.md`](GITHUB_UPLOAD_GUIDE.md) | 이 저장소에 올리는 방법 자체를 정리한 가이드 |

---

## 처음 시작하신다면

1. Docker/Git이 처음이시면 [`ONBOARDING.md`](ONBOARDING.md) 먼저 읽어주세요.
2. 직접 손으로 재현해보고 싶으시면 [`cicd_supply_chain_demo/HANDS_ON_GUIDE.md`](cicd_supply_chain_demo/HANDS_ON_GUIDE.md)를 순서대로 따라가시면 됩니다.
3. 전체 그림과 지금까지 진행 상황은 [`cicd_supply_chain_demo/PROPOSAL.md`](cicd_supply_chain_demo/PROPOSAL.md)를 봐주세요.

---

## 라이선스 / 사용 조건

이 저장소는 교육 목적으로만 공개합니다. 내용을 참고하실 때는 위 "중요" 항목에 명시한 안전 원칙(로컬 한정, 가짜 시크릿만 사용, 실제 시스템에 적용 금지)을 동일하게 지켜주세요.
