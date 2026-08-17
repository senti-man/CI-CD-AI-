"""
'AI 개발자'가 커뮤니티/모델 허브에서 받은 사전학습(pretrained) 체크포인트를
pickle.load()로 불러오는 순간을 재현한다.

개발자는 그냥 모델을 쓰려고 로드했을 뿐인데, 그 시점에 파일 안에 숨겨진
코드가 자동으로 실행된다.
"""
import pickle
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "malicious_model.pkl"


def main():
    print(f"[victim] '{MODEL_PATH.name}' 모델을 불러오는 중 (pickle.load)...")
    with open(MODEL_PATH, "rb") as f:
        checkpoint = pickle.load(f)  # <- 이 줄 하나가 악성 코드 실행을 트리거함
    print(
        "[victim] 로드 완료:",
        {k: v for k, v in checkpoint.items() if k != "weights"},
    )


if __name__ == "__main__":
    main()
