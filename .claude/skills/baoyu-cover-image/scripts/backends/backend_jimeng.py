"""
即梦 AI (Jimeng) 文生图 3.0 后端

依赖安装（★★★ 版本必须锁定，不要装最新版 ★★★）:
    pip install --index-url https://pypi.org/simple --only-binary :all: "volcengine==1.0.228"

  包名是 `volcengine`，**不是** `volcengine-python-sdk`。

  为什么不能装新版（5.x）：本文件用的是**旧式 API**——
      volcengine.ApiInfo / volcengine.Credentials /
      volcengine.ServiceInfo / volcengine.base.Service
  而 `volcengine-python-sdk` 5.x 已移除顶层 `volcengine` 命名空间
  （只剩 `volcenginesdk*` 子包），装它必然报 ModuleNotFoundError。

  也可直接参考仓库根目录 requirements.txt（已锁好版本）。
"""

import base64
import json
import os
import sys
import time
import yaml

try:
    from volcengine.ApiInfo import ApiInfo
    from volcengine.Credentials import Credentials
    from volcengine.ServiceInfo import ServiceInfo
    from volcengine.base.Service import Service
    import requests as _requests  # noqa: F401  确保 requests 可用
except ImportError:
    print("错误: 缺少 volcengine 旧式 SDK（即梦后端依赖）")
    print("★ 注意：要装的是 legacy 包 `volcengine`，不是 `volcengine-python-sdk`！")
    print("★ 版本必须锁定 1.0.x，装最新版（5.x）会报 No module named 'volcengine'。")
    print('运行: pip install --index-url https://pypi.org/simple --only-binary :all: "volcengine==1.0.228"')
    print("或改用通义万相后端（--backend qwen-wanxiang，无需该依赖）。")
    sys.exit(1)


class JimengBackend:
    NAME = "jimeng"
    DISPLAY_NAME = "即梦 AI (文生图 3.0)"

    SERVICE_HOST = "visual.volcengineapi.com"
    REGION = "cn-north-1"
    SERVICE_NAME = "cv"

    ACTION_SUBMIT = "CVSync2AsyncSubmitTask"
    ACTION_QUERY = "CVSync2AsyncGetResult"
    VERSION = "2022-08-31"
    REQ_KEY = "jimeng_t2i_v30"

    ASPECT_RATIOS = {
        "2.35:1": {"width": 2048, "height": 872},
        "16:9": {"width": 1024, "height": 576},
        "4:3": {"width": 1024, "height": 768},
        "3:2": {"width": 1024, "height": 683},
        "1:1": {"width": 1024, "height": 1024},
        "3:4": {"width": 768, "height": 1024},
    }

    def __init__(self, access_key_id: str, secret_access_key: str):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self._service = self._init_service()

    def _init_service(self):
        """初始化 Volcan Engine 服务（volcengine-python-sdk v5 适配）"""
        def _mk_api(action):
            return ApiInfo(
                "POST", "/",
                {"Action": action, "Version": self.VERSION},  # query
                None,                                          # form
                {"Content-Type": "application/json"},          # header
            )

        creds = Credentials(self.access_key_id, self.secret_access_key,
                            self.SERVICE_NAME, self.REGION)
        info = ServiceInfo(
            self.SERVICE_HOST,
            {"Content-Type": "application/json"},
            creds, 30, 30,
            "https",
        )
        service = Service(info, {
            self.ACTION_SUBMIT: _mk_api(self.ACTION_SUBMIT),
            self.ACTION_QUERY: _mk_api(self.ACTION_QUERY),
        })
        return service

    def _make_request(self, action: str, payload: dict) -> dict:
        """
        发起 API 请求

        Args:
            action: API 动作名称
            payload: 请求体数据

        Returns:
            dict: API 响应
        """
        query = {
            "Action": action,
            "Version": self.VERSION
        }

        try:
            response = self._service.request(action, query, json.dumps(payload))
            return json.loads(response) if isinstance(response, str) else response
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_prompt_from_file(self, prompt_file_path: str) -> dict:
        """
        从 prompts/cover.md 读取提示词和配置

        Args:
            prompt_file_path: prompts/cover.md 的完整路径

        Returns:
            dict: {"prompt": str, "config": dict}
        """
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        parts = content.split("---")
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            body = "---".join(parts[2:]).strip()

            config = yaml.safe_load(frontmatter) or {}
            body_lines = body.split("\n")

            visual_prompt_lines = []
            in_visual_section = False
            for line in body_lines:
                if "视觉概念" in line or "视觉" in line:
                    in_visual_section = True
                    continue
                if in_visual_section and line.startswith("#"):
                    break
                if in_visual_section:
                    clean_line = line.strip()
                    if clean_line and not clean_line.startswith("- **"):
                        visual_prompt_lines.append(clean_line)

            visual_prompt = "\n".join(visual_prompt_lines).strip()

            title = config.get("title", "")
            if title and title not in visual_prompt:
                visual_prompt = f"{title}\n{visual_prompt}"

            return {
                "prompt": visual_prompt,
                "config": config
            }

        return {"prompt": body.strip(), "config": {}}

    def calculate_dimensions(self, aspect: str) -> tuple:
        """
        根据 aspect 比例计算实际像素尺寸

        Args:
            aspect: 比例字符串，如 "2.35:1"

        Returns:
            tuple: (width, height)
        """
        if aspect in self.ASPECT_RATIOS:
            dims = self.ASPECT_RATIOS[aspect]
            return dims["width"], dims["height"]

        parts = aspect.split(":")
        if len(parts) == 2:
            try:
                w, h = int(parts[0]), int(parts[1])
                max_side = 1024
                if w > h:
                    width = min(max_side, w * 4)
                    height = int(width * h / w)
                else:
                    height = min(max_side, h * 4)
                    width = int(height * w / h)
                width = max(512, min(2048, width))
                height = max(512, min(2048, height))
                return width, height
            except ValueError:
                pass

        return 1024, 512

    def generate(self, prompt: str, output_path: str, width: int = None, height: int = None,
                 use_pre_llm: bool = True, seed: int = -1) -> dict:
        """
        调用即梦 API 生成图片

        Args:
            prompt: 生成图像的文字描述
            output_path: 输出文件路径
            width: 图像宽度 (512-2048)
            height: 图像高度 (512-2048)
            use_pre_llm: 是否开启文本扩写优化
            seed: 随机种子，-1 表示随机

        Returns:
            dict: 包含状态和图片路径
        """
        if not self.access_key_id or not self.secret_access_key:
            return {"success": False, "error": "AccessKeyID 或 SecretAccessKey 未配置"}

        if width is None or height is None:
            width, height = 1024, 512

        width = max(512, min(2048, width))
        height = max(512, min(2048, height))

        payload = {
            "req_key": self.REQ_KEY,
            "prompt": prompt,
            "use_pre_llm": use_pre_llm,
            "seed": seed if seed > 0 else -1,
            "width": width,
            "height": height
        }

        print(f"[即梦] 正在提交任务...")
        print(f"[即梦] 提示词: {prompt[:100]}...")

        response = self._make_request(self.ACTION_SUBMIT, payload)

        if response.get("code") == 10000:
            task_id = response.get("data", {}).get("task_id")
            if task_id:
                print(f"[即梦] 任务已提交, task_id: {task_id}")
                return self._wait_for_result(task_id, output_path)
            return {"success": False, "error": "未获取到 task_id"}
        else:
            error_msg = response.get("message", "未知错误")
            return {"success": False, "error": error_msg}

    def _wait_for_result(self, task_id: str, output_path: str, max_wait: int = 120) -> dict:
        """
        轮询等待任务结果

        Args:
            task_id: 任务ID
            output_path: 输出文件路径
            max_wait: 最大等待时间（秒）

        Returns:
            dict: 包含状态和图片路径
        """
        payload = {
            "task_id": task_id,
            "req_key": self.REQ_KEY,
        }

        print(f"[即梦] 正在等待图片生成...")
        start_time = time.time()
        poll_interval = 3

        while time.time() - start_time < max_wait:
            response = self._make_request(self.ACTION_QUERY, payload)
            elapsed = int(time.time() - start_time)

            if not isinstance(response, dict):
                time.sleep(poll_interval)
                continue

            if response.get("code") != 10000:
                return {"success": False,
                        "error": response.get("message") or response.get("error", "查询失败")}

            data = response.get("data") or {}
            state = data.get("status")

            if state == "done":
                print(f"[即梦] 图片生成完成, 耗时: {elapsed}秒")
                b64_items = data.get("binary_data_base64")
                if isinstance(b64_items, str):
                    b64_items = [b64_items]
                if b64_items:
                    try:
                        img_bytes = base64.b64decode(b64_items[0])
                        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                        if os.path.exists(output_path):
                            os.rename(output_path, output_path + ".backup")
                        with open(output_path, "wb") as f:
                            f.write(img_bytes)
                        print(f"[即梦] 图片已保存至: {output_path}")
                        return {"success": True, "path": output_path}
                    except Exception as e:  # noqa: BLE001
                        return {"success": False, "error": f"base64 写入失败: {e}"}
                urls = data.get("image_urls") or []
                if urls:
                    return self._download_image(urls[0], output_path)
                return {"success": False, "error": "完成但未获取到图片数据"}

            if state in ("fail", "failed", "error", "abort"):
                return {"success": False, "error": f"任务失败 (status={state})"}

            if state:
                print(f"[即梦] 生成中(status={state})... ({elapsed}秒)")

            if elapsed > 30:
                poll_interval = 5
            if elapsed > 60:
                poll_interval = 10

            time.sleep(poll_interval)

        return {"success": False, "error": "等待超时"}

    def _download_image(self, url: str, output_path: str) -> dict:
        """
        下载图片到本地

        Args:
            url: 图片 URL
            output_path: 输出文件路径

        Returns:
            dict: 包含状态和图片路径
        """
        try:
            import urllib.request

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=60) as response:
                image_data = response.read()

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if os.path.exists(output_path):
                backup_path = output_path + ".backup"
                os.rename(output_path, backup_path)

            with open(output_path, "wb") as f:
                f.write(image_data)

            print(f"[即梦] 图片已保存至: {output_path}")
            return {"success": True, "path": output_path}

        except Exception as e:
            return {"success": False, "error": f"下载失败: {str(e)}"}


def generate_from_prompt_file(prompt_file: str, access_key_id: str, secret_access_key: str,
                              output_dir: str = None, use_pre_llm: bool = True) -> dict:
    """
    从 prompts/cover.md 文件生成图片的便捷函数

    Args:
        prompt_file: prompts/cover.md 的完整路径
        access_key_id: Volcan Engine AccessKeyID
        secret_access_key: Volcan Engine SecretAccessKey
        output_dir: 输出目录，默认与 prompt_file 同级的目录
        use_pre_llm: 是否开启文本扩写优化

    Returns:
        dict: {"success": bool, "path": str, "error": str}
    """
    backend = JimengBackend(access_key_id, secret_access_key)

    data = backend.load_prompt_from_file(prompt_file)
    prompt = data["prompt"]
    config = data["config"]

    if output_dir is None:
        output_dir = os.path.dirname(os.path.dirname(prompt_file))

    output_path = os.path.join(output_dir, "cover.png")

    aspect = config.get("aspect", "16:9")
    width, height = backend.calculate_dimensions(aspect)

    print(f"[即梦] 使用配置: aspect={aspect}, width={width}, height={height}")

    return backend.generate(
        prompt=prompt,
        output_path=output_path,
        width=width,
        height=height,
        use_pre_llm=use_pre_llm
    )


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python backend_jimeng.py <AccessKeyID> <SecretAccessKey> <prompt_file> [output_dir]")
        print()
        print("示例:")
        print("  python backend_jimeng.py AKIDxxxx SECRETxxxx d:\\project\\prompts\\cover.md")
        sys.exit(1)

    access_key_id = sys.argv[1]
    secret_access_key = sys.argv[2]
    prompt_or_file = sys.argv[3]

    if os.path.isfile(prompt_or_file):
        result = generate_from_prompt_file(prompt_or_file, access_key_id, secret_access_key)
    else:
        output_path = sys.argv[4] if len(sys.argv) > 4 else "cover.png"
        backend = JimengBackend(access_key_id, secret_access_key)
        result = backend.generate(prompt_or_file, output_path)

    if result["success"]:
        print(f"✓ 图片已保存至: {result['path']}")
    else:
        print(f"✗ 生成失败: {result['error']}")
        sys.exit(1)
