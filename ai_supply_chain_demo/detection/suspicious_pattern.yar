/*
    [팀 프로젝트 데모용 YARA 룰]
    임포트(설치) 시점에 곧바로 외부로 통신하며, 로컬 파일을 읽어 함께 전송하는
    "공급망 공격 의심" 파이썬 패키지 코드 패턴을 탐지하는 예시 룰입니다.

    실무에서는 이런 단순 문자열 매칭 룰은 오탐(정상 패키지도 걸림)이 많을 수 있으므로,
    실제 팀 프로젝트에서는 조건을 더 정교화하거나 동적 분석 결과와 함께 사용하는 것을 권장합니다.
*/

rule Suspicious_Package_ImportTime_Beacon
{
    meta:
        description = "임포트 시점에 원격 서버로 통신 + 로컬 파일 읽기를 시도하는 패턴 (공급망 공격 의심)"
        author = "team-project-demo"
        reference = "AI 공급망 공격 팀 프로젝트 실습용 (실제 위협 인텔리전스 아님)"

    strings:
        $net1 = "urllib.request.urlopen"
        $net2 = "http://" ascii
        $recon = "gethostname"
        $secret_fn = "_steal_dummy_secret" ascii
        $beacon_fn = "_beacon" ascii
        $persist_fn = "_fake_persistence_marker" ascii

    condition:
        3 of ($net1, $net2, $recon, $secret_fn, $beacon_fn, $persist_fn)
}
