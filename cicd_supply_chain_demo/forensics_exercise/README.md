# 포렌식 분석 실습 — CI/CD 공급망 침해 사고

여기 있는 증거는 전부 `cicd_supply_chain_demo`를 실제로 돌려서 나온 진짜
로그·커밋·API 응답입니다. 연습문제용으로 지어낸 가짜 데이터가 아닙니다.
다만 우리 프로젝트를 설명하는 주석 몇 줄은 "사고를 처음 보는 분석가라면
알 수 없었을 정보"라서 실습 취지에 맞게 빼뒀습니다.

## 시나리오

당신은 `demo-project`(오픈소스 CI/CD 파이프라인)를 운영하는 팀의 침해사고
대응팀원입니다. 배포용 시크릿(`FAKE_DEPLOY_TOKEN`)이 새어나간 것 같다는
제보를 받고 조사에 들어갑니다. 지금 손에 쥔 건 저장소 커밋 히스토리,
Actions 실행 기록, 그리고 우연히 확보한 수상한 서버의 접속 로그뿐입니다.

## 실습 구성

```
evidence/
  phase1_initial_investigation/   1부 — 사고를 막 발견한 시점의 증거만
    git_log.txt                     최초 3개 커밋 (베이스~병합)
    suspicious_commit.diff          의심되는 커밋의 diff
    pr1_metadata.json                해당 PR의 메타데이터 (작성자/병합자 등)
    actions_runs_1_2.json           초기 Actions 실행 기록 2건
    attacker_server_log_excerpt.txt 유출 시점 로그 발췌

  phase2_full_incident_record/    2부 — 대응 조치까지 포함한 사고 전체 기록
    git_log_full.txt                전체 커밋 히스토리
    actions_runs_all.json           전체 Actions 실행 기록
    attacker_server_log_full.txt    공격자 서버 전체 로그
    pull_requests_all.json          전체 PR 이력 (병합/차단 포함)
    branch_protection_config.json   유지관리자가 나중에 건 브랜치 보호 규칙

  pr1_pr3_reference_diffs/        참고용 — 각 공격 시도의 diff 원본
```

진행 순서는 이렇습니다. `worksheet.md`를 열고, Part 1은
`phase1_initial_investigation/` 증거만 보면서 풀어보세요(사고가 어떻게
마무리됐는지 아직 모르는 척하고). Part 2로 넘어가면 그때
`phase2_full_incident_record/`까지 열어서 전체 그림을 그리고 보고서를
쓰시면 됩니다. 막히면 `answer_key.md`를 참고하시되, 일단 혼자 끝까지
풀어보고 넘기는 게 훨씬 남습니다.

## 커리큘럼이랑 어떻게 연결되나

침해사고 대응절차 7단계, IoC/TTPs(MITRE ATT&CK) 모듈을 CI/CD라는 구체적인
사례에 그대로 적용해보는 실습입니다.

| 커리큘럼 단계 | 이 실습에서 하는 것 |
|---|---|
| 흔적 수집 | 이미 제공돼 있음 — 사실 실무에선 이 부분이 제일 힘듭니다 |
| 아티팩트 분석 | Part 1의 diff/PR 메타데이터 분석 |
| 타임라인 재구성 | Part 1의 Q4 |
| IoC/TTP 도출 | Part 1의 Q5, Q6 |
| 사고 원인 및 대응방안 도출 | Part 2 전체 |
| 보고서 작성 | Part 3 |
