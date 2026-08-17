"""
오염된 AI 모델 파일 공급망 공격 시나리오를 처음부터 끝까지 실행하는 오케스트레이터.

순서:
  1) 공격자 C2 서버 기동 (다른 시나리오와 동일한 C2 재사용)
  2) 공격자가 악성 모델 파일(malicious_model.pkl)을 만들어 배포했다고 가정
  3) '개발자'가 그 모델을 pickle.load()로 불러오는 순간 -> 감염
  4) 이번 실행에서 C2가 새로 받은 데이터를 보여줌
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))  # poisoned_model/
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
        step("2) 공격자가 악성 모델 파일(malicious_model.pkl)을 제작")
        subprocess.run([sys.executable, "build_poisoned_model.py"], cwd=ROOT, check=True)

        step("3) '개발자'가 그 모델을 pickle.load()로 사용 -> 감염 시점")
        result = subprocess.run(
            [sys.executable, "victim_load_model.py"], cwd=ROOT, capture_output=True, text=True
        )
        print(result.stdout)
        if result.stderr:
            print("[stderr]", result.stderr)

        time.sleep(1)

        step("4) 결과 확인: 공격자(C2)가 이번 실행에서 새로 받은 데이터")
        new_lines = read_new_lines(C2_LOG, c2_log_start_count) if os.path.exists(C2_LOG) else []
        if new_lines:
            for line in new_lines:
                print(json.dumps(json.loads(line), ensure_ascii=False, indent=2))
        else:
            print("(새 C2 로그 없음 - 감염 트리거가 실패했을 수 있습니다)")

        step("완료")
        print("다음으로 detection/pickle_safety_scanner.py 로 이 파일을 '실행하지 않고'")
        print("정적으로 스캔해서 탐지할 수 있는지 확인해보세요.")

    finally:
        c2_proc.terminate()
        try:
            c2_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            c2_proc.kill()


if __name__ == "__main__":
    main()
