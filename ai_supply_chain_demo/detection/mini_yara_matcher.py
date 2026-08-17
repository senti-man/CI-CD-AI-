"""
진짜 yara-python 대신 쓰는 아주 작은 YARA 흉내 엔진.

이 PC는 Python 3.14라 yara-python 사전 빌드 wheel이 아직 없고, 컴파일하려면
Visual C++ Build Tools(수 GB)가 필요하다. 그냥 맛보기로 검증하는 게
목적이라 실제 룰 파일(suspicious_pattern.yar)은 그대로 두고, 그 안의
strings와 N of (...) 조건만 파싱해서 똑같이 동작하는 단순한 매처를 만들었다.

학원 VM 같은 실습 환경에 진짜 yara나 yara-python이 깔려 있다면 이 스크립트
없이 아래처럼 바로 쓰면 된다.
    yara detection/suspicious_pattern.yar 대상파일
    또는
    import yara; yara.compile(filepath="detection/suspicious_pattern.yar").match(대상파일)
"""
import re
import sys
from pathlib import Path

RULE_PATH = Path(__file__).parent / "suspicious_pattern.yar"


def parse_rule(rule_text: str):
    strings = {}  # name -> (value, nocase)
    for m in re.finditer(r'\$(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*(ascii)?\s*(nocase)?', rule_text):
        name, value, _ascii, nocase = m.groups()
        strings[name] = (value, bool(nocase))

    cond_match = re.search(r"condition:\s*(\d+)\s+of\s*\(([^)]*)\)", rule_text)
    threshold = int(cond_match.group(1))
    names_in_condition = [n.strip().lstrip("$") for n in cond_match.group(2).split(",")]
    return strings, threshold, names_in_condition


def scan_file(path: Path, strings, threshold, names_in_condition):
    text = path.read_text(encoding="utf-8", errors="ignore")
    matched = []
    for name in names_in_condition:
        value, nocase = strings[name]
        haystack = text.lower() if nocase else text
        needle = value.lower() if nocase else value
        if needle in haystack:
            matched.append(name)
    is_match = len(matched) >= threshold
    return is_match, matched


def main():
    rule_text = RULE_PATH.read_text(encoding="utf-8")
    strings, threshold, names_in_condition = parse_rule(rule_text)

    print(f"[rule] {RULE_PATH.name}  (조건: {threshold} of {names_in_condition})\n")

    targets = sys.argv[1:]
    if not targets:
        targets = [
            "malicious_package/ai_lint_helper/__init__.py",
            "attacker_c2/c2_server.py",
            "fake_victim/requirements.txt",
        ]

    for t in targets:
        path = Path(t)
        if not path.exists():
            print(f"[skip] {t} (파일 없음)")
            continue
        is_match, matched = scan_file(path, strings, threshold, names_in_condition)
        status = "MATCH" if is_match else "no match"
        print(f"[{status}] {t}")
        if matched:
            print(f"         매치된 문자열: {matched}")


if __name__ == "__main__":
    main()
