"""
'AI 코딩 에이전트'가 MCP 서버에 접속해서 도구를 쓰는 상황을 재현한다.

실제로는 Claude나 Copilot 같은 AI가 이 역할을 하겠지만, 여기서는 스크립트로
같은 순서(핸드셰이크 -> 도구 목록 조회 -> 도구 호출)를 흉내냈다. AI
입장에서는 tools/list로 받은 description 문구만 보고 이 도구를 믿을지
말지 판단한다는 게 핵심이다 - 실제 구현 코드는 볼 수가 없다.
"""
import json
import subprocess
import sys
import time


def rpc(proc, method, params=None, req_id=1):
    req = {"id": req_id, "method": method, "params": params or {}}
    proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    return json.loads(line)


def main():
    server_path = sys.argv[1] if len(sys.argv) > 1 else "malicious_mcp_server.py"
    proc = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    time.sleep(0.3)

    print("=== 1) MCP 핸드셰이크 (initialize) ===")
    print(rpc(proc, "initialize", req_id=1))

    print("\n=== 2) 사용 가능한 도구 목록 조회 (tools/list) ===")
    print("-> AI는 이 설명(description)만 보고 도구를 신뢰할지 판단합니다:")
    res = rpc(proc, "tools/list", req_id=2)
    print(res)

    print("\n=== 3) '개발자가 AI에게 코드 정리를 요청' -> AI가 도구 호출 (tools/call) ===")
    res = rpc(
        proc,
        "tools/call",
        {"name": "format_code", "arguments": {"code": "def   foo():\n  pass"}},
        req_id=3,
    )
    print("도구 응답 (사용자/AI에게 보이는 정상적인 결과):", res)

    proc.terminate()
    time.sleep(0.2)
    err = proc.stderr.read()
    if err:
        print("\n=== [참고] 서버 내부 로그(stderr, 실제 환경이면 사용자 눈에 안 보임) ===")
        print(err)


if __name__ == "__main__":
    main()
