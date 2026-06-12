"""SPEC.md 与 src/config.py 配置一致性校验脚本

用正则对比 SPEC.md 和 src/config.py 中的 chunk_size、chunk_overlap 值，
输出一致/不一致结果。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "SPEC.md"
CONFIG_PATH = ROOT / "src" / "config.py"

# 需要校验的参数及其正则
# config.py 中的赋值形如: CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
# 用通用正则提取 getenv 的默认值字符串
PARAMS = {
    "chunk_size": {
        "spec_pattern": re.compile(r"chunk_size[：:]\s*(\d+)", re.IGNORECASE),
        "config_pattern": re.compile(r'CHUNK_SIZE\s*=\s*int\(\s*os\.getenv\(\s*"CHUNK_SIZE",\s*"(\d+)"'),
    },
    "chunk_overlap": {
        "spec_pattern": re.compile(r"chunk_overlap[：:]\s*(\d+)", re.IGNORECASE),
        "config_pattern": re.compile(r'CHUNK_OVERLAP\s*=\s*int\(\s*os\.getenv\(\s*"CHUNK_OVERLAP",\s*"(\d+)"'),
    },
}


def extract_spec_value(spec_text: str, param: str) -> str | None:
    """从 SPEC.md 提取参数值"""
    m = PARAMS[param]["spec_pattern"].search(spec_text)
    return m.group(1) if m else None


def extract_config_value(config_text: str, param: str) -> str | None:
    """从 config.py 提取参数默认值"""
    info = PARAMS[param]
    m = info["config_pattern"].search(config_text)
    return m.group(1) if m else None


def main() -> int:
    errors = 0

    spec_text = SPEC_PATH.read_text(encoding="utf-8")
    config_text = CONFIG_PATH.read_text(encoding="utf-8")

    for param in PARAMS:
        spec_val = extract_spec_value(spec_text, param)
        config_val = extract_config_value(config_text, param)

        if spec_val is None:
            print(f"[WARN] {param}: SPEC.md 中未找到对应定义")
            continue
        if config_val is None:
            print(f"[FAIL] {param}: src/config.py 中未找到对应配置")
            errors += 1
            continue

        if spec_val == config_val:
            print(f"[OK]   {param}: SPEC={spec_val}, config={config_val}")
        else:
            print(f"[FAIL] {param}: SPEC={spec_val}, config={config_val} (不一致)")
            errors += 1

    if errors:
        print(f"\n共 {errors} 项不一致")
        return 1
    else:
        print("\n所有参数一致")
        return 0


if __name__ == "__main__":
    sys.exit(main())
