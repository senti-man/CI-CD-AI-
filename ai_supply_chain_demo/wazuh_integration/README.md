# Wazuh 연동 설계 (팀 프로젝트 확장)

이 폴더는 설계 산출물입니다. 이 PC에는 Docker가 없어서 Wazuh Manager를
직접 띄우지는 못했고, 학원/팀 VM에 그대로 가져다 붙일 수 있는 설정
파일과 절차만 정리해뒀습니다.

## 1. 왜 Wazuh인가

지금까지 만든 세 시나리오(pip 패키지 / MCP 서버 / pickle 모델)는 실행하면
"C2가 이런 데이터를 받았다"까지는 눈으로 확인할 수 있는데, 실제
SOC(보안관제) 환경이라면 사람이 로그를 일일이 열어보지 않아도 자동으로
탐지 알림이 떠야 합니다. Wazuh는 오픈소스 SIEM/XDR이라 이런 걸 해줍니다.

- 엔드포인트에 에이전트를 심어서 파일 변경(FIM), 로그, 프로세스 실행을 실시간으로 수집
- 커스텀 룰로 "이런 패턴이 보이면 알림"을 정의
- 룰에 MITRE ATT&CK 태그를 붙이면 대시보드에서 바로 ATT&CK 매트릭스로 보여줌
- (선택) Active Response로 탐지 시 자동 대응(프로세스 종료 등)까지 가능

우리 프로젝트의 IoC/TTP 표를 그대로 Wazuh 룰로 옮기면, README.md에
표로만 있던 내용이 실제로 동작하는 탐지 파이프라인이 됩니다.

## 2. 아키텍처

```
[Wazuh Agent가 설치된 "피해자" PC]              [Wazuh Manager]
  이 저장소(ai_supply_chain_demo)가
  실제로 실행되는 PC와 동일

  ├─ syscheck(FIM)                     로그/이벤트 수신
  │   fake_victim/, malicious_package/,     │
  │   mcp_attack/, poisoned_model/,         │
  │   artifacts/ 폴더 실시간 감시            │
  │                                          ▼
  ├─ localfile (json)                 커스텀 decoder로 필드 분해
  │   artifacts/c2_log.jsonl 수집           │
  │                                          ▼
  └─ (선택) Sysmon eventchannel        local_rules.xml 룰 매칭
      프로세스/네트워크 이벤트                │
                                              ▼
                                    MITRE ATT&CK 태그 부착된 Alert
                                              │
                                              ▼
                                   Wazuh Dashboard에서 확인
                                   (Security Events / MITRE ATT&CK 탭)
```

## 3. 파일 구성과 배포 절차

| 파일 | 어디에 넣는가 |
|---|---|
| `agent_ossec_conf_snippet.xml` | 피해자 PC의 Wazuh Agent `ossec.conf` 안 `<ossec_config>` 태그 내부 |
| `rules/local_rules.xml` | Wazuh Manager의 `/var/ossec/etc/rules/local_rules.xml` |

### 배포 순서

1. Wazuh Manager를 준비합니다 (학원/팀 VM에서, 보통 Docker Compose 단일
   노드가 제일 빠릅니다 — 공식 `wazuh-docker` 저장소의 `single-node` 구성을
   추천합니다. 정확한 버전별 명령은 그때그때 공식 문서를 확인하는 게
   좋습니다, 버전마다 조금씩 바뀝니다.)
2. 피해자 PC(=이 데모가 도는 PC)에 Wazuh Agent를 설치하고 Manager 주소로 등록합니다.
3. `agent_ossec_conf_snippet.xml` 내용을 Agent의 `ossec.conf`에 추가하고
   경로를 실제 설치 위치에 맞게 고친 다음 에이전트 서비스를 재시작합니다.
4. 배포 전에 꼭 검증하고 넘어가야 합니다. Manager에서
   `wazuh-logtest`(버전에 따라 `/var/ossec/bin/ossec-logtest`)를 실행해서
   `artifacts/c2_log.jsonl`의 실제 한 줄을 붙여넣고, JSON 필드가 예상한
   이름(`payload.event` 등)으로 제대로 분해되는지 확인해야 합니다. 이
   저장소는 실제 Wazuh 인스턴스에 붙여서 테스트해본 게 아니라서, 필드
   경로나 상위 룰 ID(554 등)는 버전에 따라 다를 수 있습니다.
   `local_rules.xml` 상단 주석에도 같은 얘기를 적어뒀습니다.
5. `rules/local_rules.xml` 내용을 Manager의 `local_rules.xml`에 추가하고
   Manager를 재시작합니다.
6. `python run_demo.py`(또는 다른 시나리오)를 실행하고 Wazuh Dashboard의
   Security Events에서 알림을 확인합니다.

## 4. 룰 설계 요약 (`rules/local_rules.xml`)

| Rule ID | 레벨 | 내용 |
|---|---|---|
| 100100 | 3 | C2로 온 모든 beacon (베이스 룰) |
| 100101 | 10 | pip 패키지 경로 beacon — T1195.002, T1071.001, T1005 |
| 100102 | 10 | MCP 서버 경로 beacon — T1195.002, T1071.001, T1005 |
| 100103 | 12 | pickle 모델 경로 beacon (RCE라 가장 높은 레벨) — T1195.002, T1204, T1071.001 |
| 100110 | 12 | 지속성 시뮬레이션 마커 파일 생성 (FIM) — T1547 |
| 100111 | 6 | 새 .pkl 파일 생성 감지 (FIM, 참고용 낮은 심각도) |
| 100120 | 14 | 5분 내 서로 다른 경로에서 다중 beacon — "다중 벡터 공급망 공격" 상관분석 룰 |

레벨(심각도)과 MITRE 매핑은 README.md의 IoC/TTP 표를 그대로 반영한
것입니다. 팀 보고서에서는 "표로 정리한 위협 인텔리전스를 실제 탐지
룰로 구현했다"는 흐름으로 풀어서 설명하면 좋습니다.

## 5. 팀 프로젝트 발표 시나리오 제안

1. Wazuh Dashboard를 화면에 띄워둔 채로 `python run_demo.py`를 라이브로 실행합니다.
2. 몇 초 뒤 Security Events에 알림이 뜨는 걸 보여줍니다.
3. MITRE ATT&CK 탭에서 그 알림이 T1195.002 등에 매핑되는 걸 보여줍니다.
4. 이어서 `mcp_attack/run_mcp_demo.py`, `poisoned_model/run_model_demo.py`도
   차례로 실행해서 서로 다른 경로가 각각 알림으로 잡히는 걸 보여줍니다.
5. 마지막으로 두 시나리오를 5분 안에 연달아 실행해서 상관분석 룰(100120)이
   "다중 벡터 공급망 공격"으로 알림을 격상시키는 것까지 보여주면 마무리가
   꽤 인상적일 겁니다.
