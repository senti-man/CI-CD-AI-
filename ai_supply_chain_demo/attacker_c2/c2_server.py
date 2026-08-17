"""
가짜 공격자 C2(Command & Control) 서버. 교육용 데모라 실제로는 아무것도 안 훔친다.

127.0.0.1(내 컴퓨터 안)에서만 접속을 받고 인터넷으로는 안 나간다. 감염된
'피해자 패키지'가 보내는 신호(beacon)를 받아서 artifacts/c2_log.jsonl에
기록만 한다.
"""
import http.server
import json
import os
import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "artifacts", "c2_log.jsonl")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except Exception:
            payload = {"raw": body.decode(errors="replace")}

        record = {
            "received_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "client_addr": self.client_address[0],
            "path": self.path,
            "payload": payload,
        }
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"[C2] 신호 수신: {record}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        pass  # 기본 HTTP 접속 로그는 끄고, 위의 커스텀 로그만 사용


if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", 8899), Handler)
    print("[C2] 127.0.0.1:8899 에서 대기 중입니다. (Ctrl+C로 종료)")
    server.serve_forever()
