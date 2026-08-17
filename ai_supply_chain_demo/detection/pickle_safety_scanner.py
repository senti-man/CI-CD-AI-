"""
파이썬 pickle 파일을 실행하지 않고 opcode를 정적으로 분석해서, 위험한 코드
실행 함수(GLOBAL/STACK_GLOBAL 참조)가 들어있는지 찾아내는 단순한 스캐너다.
picklescan이나 fickling 같은 실제 도구가 하는 일을 교육용으로 간략화했다.

pickle 파일은 opcode 스트림으로 이루어져 있고, 그 안에 GLOBAL(최신
프로토콜에서는 STACK_GLOBAL) opcode로 '이 모듈의 이 함수를 가져와라'는
지시가 들어갈 수 있다. exec, eval, os.system, subprocess.* 같은 걸
참조하는 GLOBAL이 있다면 아주 의심스러운 파일이다.
"""
import pickletools
import sys
from pathlib import Path

DANGEROUS_CALLABLES = {
    ("builtins", "exec"),
    ("builtins", "eval"),
    ("os", "system"),
    ("os", "popen"),
    ("nt", "system"),
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "run"),
    ("subprocess", "check_output"),
}


def scan(path: Path):
    findings = []
    data = path.read_bytes()

    pending_strings = []  # STACK_GLOBAL 직전에 쌓인 문자열 push들 (module, name 후보)

    for opcode, arg, pos in pickletools.genops(data):
        if opcode.name == "GLOBAL":
            # 구형 프로토콜(0~2): arg가 "module name" 형태의 문자열
            module, _, name = arg.partition(" ")
            if (module, name) in DANGEROUS_CALLABLES:
                findings.append((pos, module, name, "GLOBAL"))
            pending_strings.clear()

        elif opcode.name in ("SHORT_BINUNICODE", "BINUNICODE", "BINUNICODE8", "UNICODE"):
            pending_strings.append(arg)
            if len(pending_strings) > 2:
                pending_strings = pending_strings[-2:]

        elif opcode.name == "STACK_GLOBAL":
            # 최신 프로토콜: 직전에 push된 두 문자열이 (module, name)
            if len(pending_strings) >= 2:
                module, name = pending_strings[-2], pending_strings[-1]
                if (module, name) in DANGEROUS_CALLABLES:
                    findings.append((pos, module, name, "STACK_GLOBAL"))
            pending_strings.clear()

        elif opcode.name == "MEMOIZE":
            # MEMOIZE는 스택 맨 위 값을 memo에 저장만 할 뿐 push/pop을 하지 않으므로
            # 문자열 push 직후에 흔히 끼어듦 - 버퍼를 지우면 안 됨
            pass

        else:
            pending_strings.clear()

    return findings


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "poisoned_model/malicious_model.pkl"
    path = Path(target)
    if not path.exists():
        print(f"[skip] 파일 없음: {path}")
        return

    findings = scan(path)
    if findings:
        print(f"[WARNING] '{path}' 에서 위험한 opcode {len(findings)}건 발견 (파일을 실행하지 않고 탐지):")
        for pos, module, name, kind in findings:
            print(f"  - offset {pos} ({kind}): {module}.{name}  <- 코드/명령 실행 함수가 파일 안에 포함됨")
        print("\n=> 이 pickle 파일은 신뢰할 수 없습니다. 로드(pickle.load)하지 마세요.")
        print("   안전한 대안: safetensors 포맷 사용, torch.load(weights_only=True), 서명/해시 검증 등")
    else:
        print(f"[OK] '{path}' 에서 위험한 opcode가 발견되지 않았습니다.")


if __name__ == "__main__":
    main()
