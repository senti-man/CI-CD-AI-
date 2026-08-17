"""
AI 공급망 공격 시나리오를 처음부터 끝까지 자동으로 실행하는 오케스트레이터.

순서:
  1) 공격자 C2 서버를 로컬(127.0.0.1)에서 띄운다.
  2) '개발자'가 requirements.txt로 패키지를 설치한다고 가정하고 venv에 설치한다.
     (이 안에 악성 패키지 ai-lint-helper 가 섞여 들어감)
  3) '개발자'가 그 패키지를 import 해서 실제로 사용하는 순간을 재현한다.
     -> 이 시점에 악성 코드가 자동 실행되어 C2로 신호를 보낸다.
  4) 결과(C2가 받은 로그, 생성된 흔적 파일)를 보여준다.

모든 통신은 127.0.0.1 안에서만 이루어지며, 외부 네트워크로는 절대 나가지 않습니다.
"""
import json
import os
import subprocess
import sys
import time
import venv

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(ROOT, ".venv")
ARTIFACTS = os.path.join(ROOT, "artifacts")
C2_LOG = os.path.join(ARTIFACTS, "c2_log.jsonl")
PERSIST_MARKER = os.path.join(ARTIFACTS, "SIMULATED_persistence_marker_pip_package.txt")


def count_lines(path):
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def read_new_lines(path, start_count):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    return lines[start_count:]


def venv_python():
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def step(msg):
    print(f"\n=== {msg} ===")


def main():
    os.makedirs(ARTIFACTS, exist_ok=True)
    # c2_log.jsonl은 지우지 않습니다 - 다른 시나리오(mcp_attack, poisoned_model)와
    # 신호가 함께 쌓여서 "하나의 공격자가 여러 경로로 침투했다"는 그림을 볼 수 있습니다.
    # 이 시나리오만의 흔적(지속성 마커)만 재실행 시 헷갈리지 않게 정리합니다.
    if os.path.exists(PERSIST_MARKER):
        os.remove(PERSIST_MARKER)
    c2_log_start_count = count_lines(C2_LOG)

    step("1) 가짜 공격자 C2 서버 기동 (127.0.0.1:8899)")
    c2_proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "attacker_c2", "c2_server.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(1)
    print("C2 서버 PID:", c2_proc.pid)

    try:
        step("2) 개발자 PC 환경(venv) 준비")
        if not os.path.exists(venv_python()):
            venv.EnvBuilder(with_pip=True).create(VENV_DIR)
            print("venv 생성 완료:", VENV_DIR)
        else:
            print("기존 venv 재사용:", VENV_DIR)

        step("3) '개발자'가 requirements.txt를 설치 (여기에 악성 패키지가 섞여 있음)")
        subprocess.run(
            [venv_python(), "-m", "pip", "install", "-q", "-r", "requirements.txt"],
            cwd=os.path.join(ROOT, "fake_victim"),
            check=True,
        )
        print("설치 완료: ai-lint-helper (겉보기엔 평범한 AI 코딩 헬퍼 패키지)")

        step("4) '개발자'가 실제로 그 패키지를 사용 (import) -> 감염 시점")
        result = subprocess.run(
            [venv_python(), "-c", "import ai_lint_helper"],
            cwd=os.path.join(ROOT, "fake_victim"),
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.stderr:
            print("[stderr]", result.stderr)

        time.sleep(1)  # C2 로그 flush 대기

        step("5) 결과 확인: 공격자(C2)가 이번 실행에서 새로 받은 데이터")
        new_lines = read_new_lines(C2_LOG, c2_log_start_count) if os.path.exists(C2_LOG) else []
        if new_lines:
            for line in new_lines:
                rec = json.loads(line)
                print(json.dumps(rec, ensure_ascii=False, indent=2))
        else:
            print("(새 C2 로그 없음 - 감염 트리거가 실패했을 수 있습니다)")

        step("6) 결과 확인: 남겨진 '지속성' 시뮬레이션 흔적")
        if os.path.exists(PERSIST_MARKER):
            with open(PERSIST_MARKER, encoding="utf-8") as f:
                print(f.read())

        step("완료")
        print(f"모든 증거물은 다음 폴더에 있습니다: {ARTIFACTS}")
        print("팀 프로젝트에서는 이 증거물(c2_log.jsonl, 패키지 소스코드)을 가지고")
        print("IoC/TTP 추출, YARA 룰 검증, 보고서 작성을 진행하면 됩니다.")

    finally:
        c2_proc.terminate()
        try:
            c2_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            c2_proc.kill()


if __name__ == "__main__":
    main()
