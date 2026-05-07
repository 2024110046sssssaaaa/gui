import os
import datetime

from PIL import Image
import matplotlib.pyplot as plt


_WORK_PATH = os.environ["MOBILE_SAFETY_HOME"]


class Logger:
    def __init__(self, args):

        self.task_id = args.task_id
        self.scenario_id = args.scenario_id

        self.model = args.model
        self.prompt_mode = args.prompt_mode

        # ── folder naming: auto-detect provider from model name ───────────────
        model_lower = self.model.lower()
        if "claude-" in model_lower or "anthropic" in model_lower:
            folder_name = "claude"
        elif "gemini-" in model_lower:
            folder_name = "gemini"
        elif "qwen-" in model_lower:
            folder_name = "qwen"
        elif "deepseek-" in model_lower:
            folder_name = "deepseek"
        elif "o1-" in model_lower or model_lower.startswith("o1"):
            folder_name = "o1"
        elif "openrouter" in model_lower or "openrouter/" in self.model:
            folder_name = "openrouter"
        elif "gpt-" in model_lower:
            folder_name = "gpt"
        else:
            folder_name = "other"

        if self.prompt_mode == "" or self.prompt_mode == "basic":
            folder_name += "_basic"
        elif self.prompt_mode == "scot":
            folder_name += "_scot"
        elif self.prompt_mode == "safety_guided":
            folder_name += "_safety_guided"

        self.dir_name = (
            f"{_WORK_PATH}/logs/{folder_name}/{self.task_id}/{self.scenario_id}"
        )
        if not os.path.exists(self.dir_name):
            os.makedirs(self.dir_name)

        # file setting
        time_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.file_name = f"{self.dir_name}/{time_now}"

        self.images = []
        self.texts = ""

        return

    def log(self, prompt=None, response_dict=None, timestep=None):
        # pass logging if error in timestep
        if timestep is not None and timestep.error():
            print("=" * 30)
            print("Error timestep: JSON parsing failed")
            print("Raw response:")
            if response_dict is not None:
                print(response_dict.get("raw_response", "N/A"))
            else:
                print("N/A (response_dict is None)")
            print("=" * 30)
            return

        # log prompt
        if prompt is not None:
            print(prompt)
            self.texts += prompt + "\n"

        # log response
        if response_dict is not None:
            print("<assistant_prompt>")
            print(response_dict["raw_response"])
            print("</assistant_prompt>\n\n")
            for key, value in response_dict.items():
                if key != "raw_response":
                    self.texts += f"{key}: {value}\n"
            self.texts += "\n"

        # log state: progress, image
        if timestep is not None:
            img_obs = timestep.curr_obs["pixel"]
            self.images.append(Image.fromarray(img_obs))

            # print image
            # plt.imshow(img_obs)
            # plt.show()  # 禁用图形显示以避免阻塞程序

            # progress log
            print("progress:", timestep.progress)
            print("=" * 60 + "\n")
            progress = timestep.progress if timestep is not None else None
            self.texts += "=" * 60 + "\n"
            self.texts += f"progress: {progress}\n"
            self.texts += "=" * 60 + "\n\n"

        # update files
        with open(f"{ self.file_name}.txt", "w") as file:
            file.write(self.texts)

        if len(self.images) > 0:
            self.images[0].save(
                f"{self.file_name}.gif",
                save_all=True,
                append_images=self.images[1:],
                optimize=False,
                duration=2000,
                loop=0,
            )

        return
