import os
import re
import cv2

from PIL import Image
from openai import OpenAI
from datetime import datetime

from mobile_safety.agent.LLM_agent import LLM_Agent
from mobile_safety.agent.utils import encode_image, parse_response


_WORK_PATH = os.environ["MOBILE_SAFETY_HOME"]


class GPTAgent(LLM_Agent):
    def __init__(self, model_name="gpt-4o-2024-05-13", seed=42, port=5554):

        super().__init__(model_name, seed, port)

        # Support both OpenAI and Qwen (DashScope) APIs
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL", None)
        
        # 修复Windows平台检测bug - 设置默认HTTP头避免platform.system()调用
        default_headers = {
            "X-Stainless-OS": "Windows",
            "X-Stainless-Runtime": "CPython",
            "X-Stainless-Runtime-Version": "3.11"
        }
        
        if base_url:
            self.model = OpenAI(api_key=api_key, base_url=base_url, default_headers=default_headers)
        else:
            self.model = OpenAI(api_key=api_key, default_headers=default_headers)
        
        self.time_list = []

        return

    def get_response(self, timestep=None, system_prompt=None, user_prompt=None):

        img_pil_path = self.save_image(timestep)

        user_prompt = re.sub(r"<context>", self.context, user_prompt)

        start_time = datetime.now()
        
        print(f"[API] 正在调用 {self.model_name}...")
        print(f"[API] 图片路径: {img_pil_path}")
        
        try:
            completion = self.model.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encode_image(img_pil_path)}"
                                },
                            },
                        ],
                    },
                ],
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"],
                top_p=self.config["top_p"],
                seed=self.seed,
                timeout=120.0,
            )
            response = completion.choices[0].message.content
            print(f"[API] 响应成功")
        except Exception as e:
            print(f"[API] 调用失败: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

        end_time = datetime.now()
        time_elapsed = end_time - start_time
        self.time_list.append(time_elapsed.total_seconds())
        print(f"Time elapsed: {time_elapsed.total_seconds()}")

        # parse response
        response_dict = parse_response(response)
        if response_dict["action"] == None:
            print("Error in response")
        if response_dict["context"] != "":
            self.context = response_dict["context"]

        # return used prompt for logging
        prompt = ""
        prompt += "<system_prompt>\n" + system_prompt + "</system_prompt>\n\n"
        prompt += "<user_prompt>\n" + user_prompt + "</user_prompt>\n\n"

        return response_dict, prompt

    def save_image(self, timestep=None):
        img_obs = timestep.curr_obs["pixel"]
        # 进一步减小图像尺寸以加快 API 响应速度（从 512x1024 减小到 384x768）
        img_cv = cv2.resize(img_obs, dsize=(384, 768), interpolation=cv2.INTER_AREA)
        img_pil = Image.fromarray(img_cv)
        img_pil_path = f"{_WORK_PATH}/logs/tmp_{self.port}.png"
        img_pil.save(img_pil_path, quality=70, optimize=True)
        
        # 打印文件大小用于调试
        import os
        file_size = os.path.getsize(img_pil_path)
        print(f"[DEBUG] 图片已保存: {img_pil_path}, 大小: {file_size/1024:.1f}KB")

        return img_pil_path
