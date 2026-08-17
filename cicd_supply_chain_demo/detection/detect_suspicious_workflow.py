"""
CI/CD 워크플로우 YAML에서 "시크릿을 외부로 유출하는 스텝"을 정규식/구조
기반 휴리스틱으로 잡아내는 탐지 스크립트.

판단 기준은 이렇다. 같은 스텝(run 블록) 안에 (a) 네트워크로 나가는 명령
(curl, wget, Invoke-WebRequest, Invoke-RestMethod, nc, python
urllib.request 등)이 있고 (b) `${{ secrets.XXX }}` 형태로 시크릿을
참조하는 부분이 같이 있으면 "시크릿 유출 의심"으로 HIGH 등급을 매긴다.

네트워크 명령만 있고 시크릿 참조가 없으면(공개 API 조회 같은 경우) 정상으로
보고 플래그하지 않는다 - 이게 오탐률을 낮추는 핵심이다.

사용법:
  python detect_suspicious_workflow.py 파일1.yml 파일2.yml ...
  python detect_suspicious_workflow.py ../samples/*.yml   (셸에서 와일드카드 확장 시)
"""
import re
import sys
from pathlib import Path

import yaml

NETWORK_CMD_PATTERNS = [
    re.compile(r"\bcurl\b", re.IGNORECASE),
    re.compile(r"\bwget\b", re.IGNORECASE),
    re.compile(r"Invoke-WebRequest", re.IGNORECASE),
    re.compile(r"Invoke-RestMethod", re.IGNORECASE),
    re.compile(r"\bnc\s+-", re.IGNORECASE),
    re.compile(r"urllib\.request", re.IGNORECASE),
    re.compile(r"requests\.(post|get)\(", re.IGNORECASE),
    re.compile(r"System\.Net\.WebClient", re.IGNORECASE),
]

SECRET_REF_PATTERN = re.compile(r"\$\{\{\s*secrets\.[A-Za-z0-9_]+\s*\}\}")

SUSPICIOUS_NAME_HINTS = re.compile(
    r"cache|setup|cleanup|prepare|init|config|temp|artifact", re.IGNORECASE
)


def find_network_matches(text):
    return [p.pattern for p in NETWORK_CMD_PATTERNS if p.search(text)]


def analyze_step(job_name, step, index):
    run_text = step.get("run")
    if not isinstance(run_text, str):
        return None  # uses: 액션 스텝 등은 이 휴리스틱 범위 밖

    net_matches = find_network_matches(run_text)
    secret_matches = SECRET_REF_PATTERN.findall(run_text)

    if net_matches and secret_matches:
        step_name = step.get("name", f"(이름 없음, {index}번째 스텝)")
        verdict = "HIGH"
        reasons = [
            f"네트워크 명령 발견: {net_matches}",
            f"시크릿 참조 발견: {secret_matches}",
        ]
        if SUSPICIOUS_NAME_HINTS.search(step_name):
            reasons.append("스텝 이름이 의도적으로 평범해 보이도록 위장된 패턴과 일치 (예: cache/setup 등)")
        return {
            "job": job_name,
            "step": step_name,
            "verdict": verdict,
            "reasons": reasons,
            "run": run_text.strip(),
        }
    return None


def scan_file(path: Path):
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    findings = []
    jobs = (data or {}).get("jobs", {}) or {}
    for job_name, job in jobs.items():
        steps = job.get("steps", []) or []
        for i, step in enumerate(steps):
            finding = analyze_step(job_name, step, i)
            if finding:
                findings.append(finding)
    return findings


def main():
    targets = sys.argv[1:]
    if not targets:
        print("사용법: python detect_suspicious_workflow.py 파일1.yml [파일2.yml ...]")
        return

    total_files = 0
    flagged_files = 0

    for t in targets:
        path = Path(t)
        if not path.exists():
            print(f"[skip] 파일 없음: {t}")
            continue
        total_files += 1
        findings = scan_file(path)
        if findings:
            flagged_files += 1
            print(f"\n[WARNING] {path} - 의심 스텝 {len(findings)}건 발견")
            for f in findings:
                print(f"  - job={f['job']!r} step={f['step']!r} verdict={f['verdict']}")
                for r in f["reasons"]:
                    print(f"      · {r}")
        else:
            print(f"[OK] {path} - 의심 스텝 없음")

    print(f"\n=== 요약: {total_files}개 파일 중 {flagged_files}개에서 의심 스텝 탐지 ===")

    # CI 게이트로 쓸 때 의심 스텝이 하나라도 있으면 잡을 실패시키기 위한 종료 코드.
    # 로컬에서 그냥 훑어볼 때도 셸 exit code만 1이 될 뿐 동작엔 지장 없음.
    if flagged_files:
        sys.exit(1)


if __name__ == "__main__":
    main()
