"""
通义万相 (Qwen Wanxiang) 后端
支持阿里云通义万相的文生图 API

注意: 请填写正确的 API 配置信息
"""

import json
import urllib.request
import urllib.parse
import os
import sys

class QwenWanxiangBackend:
    NAME = "qwen-wanxiang"
    DISPLAY_NAME = "通义万相"

    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # 模型名可用：wanx-v1（经典） / wan2.1-t2i-turbo / wan2.2-t2i-flash（推荐，性价比高）
    # 可用环境变量 QWEN_MODEL 覆盖
    MODEL_NAME = "wan2.1-t2i-turbo"
    SUPPORTED_SIZES = {"1024x1024", "1280x720", "720x1280"}

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or self.MODEL_NAME

    @staticmethod
    def nearest_size(width: int, height: int) -> str:
        """映射到模型支持的档位：方形 1024，宽图 1280x720，竖图 720x1280。"""
        if height > width:
            return "720x1280"
        if width > height * 1.1:
            return "1280x720"
        return "1024x1024"

    def generate(self, prompt: str, output_path: str, width: int = 1024, height: int = 1024) -> dict:
        """
        调用通义万相 API 生成图片

        Args:
            prompt: 生成图像的文字描述
            output_path: 输出文件路径
            width: 图像宽度
            height: 图像高度

        Returns:
            dict: 包含状态和图片路径
        """
        if not self.api_key:
            return {"success": False, "error": "API key 未配置"}

        url = f"{self.BASE_URL}/images/generations"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": self.nearest_size(width, height)
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))

            if "data" in result and len(result["data"]) > 0:
                image_url = result["data"][0].get("url")
                if image_url:
                    return self._download_image(image_url, output_path)

            return {"success": False, "error": result.get("error", {}).get("message", "未知错误")}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _download_image(self, url: str, output_path: str) -> dict:
        """下载图片到本地"""
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=60) as response:
                image_data = response.read()

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(image_data)

            return {"success": True, "path": output_path}

        except Exception as e:
            return {"success": False, "error": f"下载失败: {str(e)}"}


def generate_wanxiang_image(prompt: str, api_key: str, output_path: str,
                            width: int = 1024, height: int = 1024) -> dict:
    """通义万相图片生成的便捷函数"""
    backend = QwenWanxiangBackend(api_key)
    return backend.generate(prompt, output_path, width, height)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python backend_qwen_wanxiang.py <api_key> <prompt> <output_path>")
        sys.exit(1)

    api_key = sys.argv[1]
    prompt = sys.argv[2]
    output_path = sys.argv[3]

    result = generate_wanxiang_image(prompt, api_key, output_path)

    if result["success"]:
        print(f"图片已保存至: {result['path']}")
    else:
        print(f"生成失败: {result['error']}")
        sys.exit(1)
