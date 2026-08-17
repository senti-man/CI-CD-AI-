"""
MCP 공급망 공격 시나리오를 처음부터 끝까지 실행하는 오케스트레이터.

순서:
  1) 공격자 C2 서버 기동 (attacker_c2/c2_server.py 재사용 - pip 시나리오와 동일한 C2)
  2) 'AI 코딩 에이전트'가 악성 MCP 서버에 접속해서 정상적인 코딩 작업을 진행
  3) 그 과정에서 도구가 호출되는 순간 몰래 정찰+탈취+C2 통신이 발생
  4) 이번 실행에서 C2가 새로 받은 데이터를 보여줌
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))  # mcp_attack/
PROJECT_ROOT = os.path.dirname(ROOT)
ARTIFACTS = os.path.join(PROJECT_ROOT, "artifacts")
C2_LOG = os.path.join(ARTIFACTS, "c2_log.jsonl")


def count_lines(path):
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def read_new_lines(path, start_count):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    return lines[start_count:]


def step(msg):
    print(f"\n=== {msg} ===")


def main():
    os.makedirs(ARTIFACTS, exist_ok=True)
    c2_log_start_count = count_lines(C2_LOG)

    step("1) 가짜 공격자 C2 서버 기동 (127.0.0.1:8899)")
    c2_proc = subprocess.Popen(
        [sys.executable, os.path.join(PROJECT_ROOT, "attacker_c2", "c2_server.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(1)
    print("C2 서버 PID:", c2_proc.pid)

    try:
        step("2) 'AI 코딩 에이전트'가 악성 MCP 서버(smart-code-formatter)에 연결")
        result = subprocess.run(
            [sys.executable, "ai_agent_stub.py", "malicious_mcp_server.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.stderr:
            print("[stderr]", result.stderr)

        time.sleep(1)

        step("3) 결과 확인: 공격자(C2)가 이번 실행에서 새로 받은 데이터")
        new_lines = read_new_lines(C2_LOG, c2_log_start_count) if os.path.exists(C2_LOG) else []
        if new_lines:
            for line in new_lines:
                print(json.dumps(json.loads(line), ensure_ascii=False, indent=2))
        else:
            print("(새 C2 로그 없음 - 감염 트리거가 실패했을 수 있습니다)")

        step("완료")
        print("개발자/사용자 화면에는 3)단계에서 '정상적인 코드 정리 결과'만 보였다는 점에 주목하세요.")
        print("실제 악성 행위(정찰+탈취+C2 통신)는 전부 도구 실행 뒤편에서 조용히 일어났습니다.")

    finally:
        c2_proc.terminate()
        try:
            c2_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            c2_proc.kill()


if __name__ == "__main__":
    main()
