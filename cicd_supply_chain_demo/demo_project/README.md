# demo-project (피해자 역할 오픈소스 프로젝트)

이 폴더 내용을 Gitea에 새로 만든 `demo-project` 저장소에 그대로
push하시면 됩니다. 그냥 평범한 오픈소스 프로젝트를 재현한 거라
`.gitea/workflows/build.yml` 하나만 가진 단순한 CI 워크플로우가 전부입니다.

## 준비 단계 (Gitea 웹 UI에서)

1. `demo-project` 저장소 생성 후 이 폴더 내용을 push
2. 저장소 Settings → Actions → Secrets에서 더미 시크릿 등록
   - Name: `FAKE_DEPLOY_TOKEN`
   - Value: `fake-deploy-token-1234567890` (완전히 가짜 값, 실제 서비스 키 아님)
3. Settings → Actions가 켜져 있는지 확인 (인스턴스 전체 설정에서 이미 켰다면 그대로 두면 됨)

여기까지 되면 공격자 역할 계정으로 이 저장소를 fork해서
`../samples/malicious_workflow.yml` 내용을 참고해 `.gitea/workflows/build.yml`에
악성 스텝을 추가한 PR을 올리고 병합해보면 PoC가 완성됩니다. 자세한
절차는 `../README.md`에 있습니다.
