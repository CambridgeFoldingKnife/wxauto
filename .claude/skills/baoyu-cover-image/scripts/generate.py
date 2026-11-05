"""
图片生成后端统一入口
遵循 baoyu-cover-image skill 的流程规范

用法:
    python generate.py jimeng <AccessKeyID> <SecretAccessKey> <prompt_dir> [output_dir]

流程:
    1. 从 <prompt_dir>/prompts/cover.md 读取提示词和配置
    2. 根据配置计算尺寸 (aspect ratio)
    3. 调用对应后端 API 生成图片
    4. 保存到 <output_dir>/cover.png
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backends.backend_jimeng import JimengBackend, generate_from_prompt_file
from backends.backend_qwen_wanxiang import QwenWanxiangBackend


BACKENDS = {
    "jimeng": JimengBackend,
    "qwen-wanxiang": QwenWanxiangBackend,
}


def generate_image(backend_name: str, access_key_id: str, secret_access_key: str,
                  prompt_file: str, output_dir: str = None, **kwargs) -> dict:
    """
    统一的图片生成接口

    遵循 baoyu-cover-image skill 的文件结构:
    <output-dir>/
    ├── source-{slug}.{ext}
    ├── refs/
    ├── prompts/
    │   └── cover.md        ← prompt_file
    └── cover.png           ← 目标输出

    Args:
        backend_name: 后端名称 (jimeng, qwen-wanxiang)
        access_key_id: AccessKeyID (即梦使用) / API Key (通义万相使用)
        secret_access_key: SecretAccessKey (即梦使用，可为空)
        prompt_file: prompts/cover.md 的完整路径
        output_dir: 输出目录，默认取 prompt_file 的父目录
        **kwargs: 其他参数

    Returns:
        dict: {"success": bool, "path": str, "error": str}
    """
    if backend_name not in BACKENDS:
        return {
            "success": False,
            "error": f"未知后端: {backend_name}。支持的: {list(BACKENDS.keys())}"
        }

    if output_dir is None:
        output_dir = os.path.dirname(os.path.dirname(prompt_file))

    output_path = os.path.join(output_dir, "cover.png")

    print(f"[生成器] 使用后端: {backend_name}")
    print(f"[生成器] 提示词文件: {prompt_file}")
    print(f"[生成器] 输出目录: {output_dir}")
    print(f"[生成器] 输出路径: {output_path}")

    if backend_name == "jimeng":
        return generate_from_prompt_file(
            prompt_file=prompt_file,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            output_dir=output_dir,
            use_pre_llm=kwargs.get("use_pre_llm", True)
        )
    elif backend_name == "qwen-wanxiang":
        backend = QwenWanxiangBackend(access_key_id)
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()

        parts = content.split("---")
        prompt = parts[-1].strip() if len(parts) >= 3 else content.strip()

        return backend.generate(prompt, output_path)


def resolve_output_dir(prompt_file: str, default_output_dir: str = "independent") -> str:
    """
    根据 default_output_dir 配置解析输出目录

    Args:
        prompt_file: prompts/cover.md 路径
        default_output_dir: 配置值 (independent, imgs-subdir, same-dir)

    Returns:
        str: 输出目录路径
    """
    prompt_dir = os.path.dirname(os.path.dirname(prompt_file))

    if default_output_dir == "independent":
        return prompt_dir
    elif default_output_dir == "imgs-subdir":
        return os.path.join(prompt_dir, "imgs")
    elif default_output_dir == "same-dir":
        return os.path.dirname(prompt_dir)

    return prompt_dir


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python generate.py <backend> <access_key_id> <secret_access_key> <prompt_dir> [output_dir]")
        print(f"支持的后端: {list(BACKENDS.keys())}")
        print()
        print("示例 (即梦):")
        print("  python generate.py jimeng AKIDxxxx SECRETxxxx d:\\project\\cover-image\\ai-project")
        print()
        print("示例 (通义万相):")
        print("  python generate.py qwen-wanxiang sk-xxxxxx '' d:\\project\\cover-image\\ai-project")
        sys.exit(1)

    backend = sys.argv[1]
    access_key_id = sys.argv[2]
    secret_access_key = sys.argv[3]
    prompt_dir = sys.argv[4]
    output_dir = sys.argv[5] if len(sys.argv) > 5 else None

    prompt_file = os.path.join(prompt_dir, "prompts", "cover.md")

    if not os.path.exists(prompt_file):
        print(f"错误: 找不到提示词文件: {prompt_file}")
        sys.exit(1)

    if output_dir is None:
        output_dir = resolve_output_dir(prompt_file)

    result = generate_image(backend, access_key_id, secret_access_key, prompt_file, output_dir)

    if result["success"]:
        print(f"✓ 图片已保存至: {result['path']}")
    else:
        print(f"✗ 生成失败: {result['error']}")
        sys.exit(1)
