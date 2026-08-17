"""
침해사고 대응 커리큘럼의 '타임라인 기반 분석'을 작은 규모로 재현한 스크립트.

실무에서는 Plaso 같은 도구로 OS 전체 아티팩트(이벤트 로그, 프리페치, 레지스트리 등)를
모아 슈퍼타임라인을 만들지만, 여기서는 우리가 만든 공급망 공격 데모 하나를 실행하면서
아래 세 가지 증거 소스를 실시간/사후에 모아 시간순으로 정렬한다.

  1) 프로세스 생성/종료  - psutil로 자식 프로세스를 추적
  2) 네트워크 연결       - psutil로 우리가 띄운 프로세스들의 연결을 폴링 (best-effort;
                          아주 짧은 연결은 폴링 간격 때문에 놓칠 수 있음 - 그래서 3)과 함께 씀)
  3) C2 서버 수신 로그    - 가장 신뢰도 높은 증거. artifacts/c2_log.jsonl 에 실제로
                          "언제 무엇을 받았는지"가 정확히 기록되어 있음

사용법:
  python analysis/capture_timeline.py                      (기본: run_demo.py = pip 시나리오)
  python analysis/capture_timeline.py mcp_attack/run_mcp_demo.py
  python analysis/capture_timeline.py poisoned_model/run_model_demo.py
"""
import csv
import datetime
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = PROJECT_ROOT / "artifacts"
C2_LOG = ARTIFACTS / "c2_log.jsonl"

EXCLUDE_DIR_PARTS = {".venv", "__pycache__"}

events = []
events_lock = threading.Lock()


def record(ts, category, detail):
    with events_lock:
        events.append((ts, category, detail))


def snapshot_files(root: Path):
    snap = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if EXCLUDE_DIR_PARTS & set(p.parts):
            continue
        try:
            snap[str(p)] = p.stat().st_mtime
        except FileNotFoundError:
            pass
    return snap


def count_lines(path: Path):
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def monitor_process(proc: subprocess.Popen, label: str, stop_event: threading.Event):
    try:
        ps_proc = psutil.Process(proc.pid)
    except psutil.NoSuchProcess:
        return
    record(time.time(), "process", f"{label} 프로세스 시작 (PID {proc.pid})")
    seen_conns = set()

    def check_connections(p, tag):
        try:
            for c in p.connections(kind="inet"):
                key = (p.pid, c.laddr, c.raddr, c.status)
                if key not in seen_conns:
                    seen_conns.add(key)
                    record(time.time(), "network", f"{tag}(PID {p.pid}): {c.laddr} -> {c.raddr} [{c.status}]")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    while not stop_event.is_set() and proc.poll() is None:
        check_connections(ps_proc, label)
        try:
            for child in ps_proc.children(recursive=True):
                check_connections(child, f"{label} 자식")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        time.sleep(0.1)

    record(time.time(), "process", f"{label} 프로세스 종료")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "run_demo.py"
    target_path = PROJECT_ROOT / target
    if not target_path.exists():
        print(f"대상 스크립트를 찾을 수 없습니다: {target_path}")
        return

    print(f"대상 시나리오: {target_path.relative_to(PROJECT_ROOT)}")

    print("1) 실행 전 파일시스템 스냅샷 촬영...")
    before = snapshot_files(PROJECT_ROOT)
    c2_log_start_count = count_lines(C2_LOG)

    print("2) 시나리오 실행 + 실시간 프로세스/네트워크 모니터링...\n")
    start_ts = time.time()
    proc = subprocess.Popen(
        [sys.executable, target_path.name], cwd=target_path.parent
    )
    stop_event = threading.Event()
    t = threading.Thread(target=monitor_process, args=(proc, target_path.stem, stop_event))
    t.start()
    proc.wait()
    stop_event.set()
    t.join()

    print("\n3) 실행 후 파일시스템 스냅샷 비교...")
    after = snapshot_files(PROJECT_ROOT)
    for path, mtime in after.items():
        if path not in before:
            record(mtime, "filesystem", f"새 파일 생성: {path}")
        elif before[path] != mtime:
            record(mtime, "filesystem", f"파일 수정: {path}")

    print("4) C2 서버 수신 로그에서 이번 실행분만 추출...")
    if C2_LOG.exists():
        with open(C2_LOG, encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[c2_log_start_count:]:
            rec = json.loads(line)
            ts = datetime.datetime.fromisoformat(rec["received_at"]).timestamp()
            payload = rec["payload"]
            record(
                ts,
                "network(C2 log)",
                f"beacon 수신: event={payload.get('event')} vector={payload.get('vector')} "
                f"host={payload.get('recon', {}).get('hostname')}",
            )

    with events_lock:
        events.sort(key=lambda e: e[0])

    ARTIFACTS.mkdir(exist_ok=True)
    out_csv = ARTIFACTS / "timeline.csv"
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "elapsed_sec", "category", "detail"])
        for ts, cat, detail in events:
            w.writerow(
                [
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                    round(ts - start_ts, 2),
                    cat,
                    detail,
                ]
            )

    print(f"\n=== 재구성된 타임라인 ({len(events)}개 이벤트) ===")
    for ts, cat, detail in events:
        t_str = time.strftime("%H:%M:%S", time.localtime(ts))
        print(f"[{t_str}] ({cat:16s}) {detail}")

    print(f"\nCSV 저장 위치: {out_csv}  (엑셀에서 바로 열어도 한글 안 깨짐)")


if __name__ == "__main__":
    main()
