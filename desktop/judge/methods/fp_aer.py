import json
import base64
import os
from pathlib import Path
from judge.methods.fp_prompts import SYS_PROMPT_FP_V1, SYS_PROMPT_FP_V2

STEP_TEMPLATE = """
|-----
Step: {step_number}
Reasoning and action: {response}
"""


def format_steps(steps: list, step_template: str = None) -> str:
    if step_template is None:
        step_template = STEP_TEMPLATE

    steps_str = ""
    for i, step in enumerate(steps):
        # Handle both 'response' and 'action' field names
        response = step.get("response") or step.get("action", "")
        steps_str += step_template.format(
            step_number=i,
            response=response,
        )
    return steps_str


def image_to_base64(image_path: Path) -> str:
    """Convert an image file to a Base64-encoded string."""
    image_path = Path(image_path)
    if not image_path.exists():
        return None

    with open(image_path, "rb") as image_file:
        x = base64.b64encode(image_file.read()).decode("utf-8")
    if image_path.suffix == ".png":
        return f"data:image/png;base64,{x}"
    elif image_path.suffix.lower() in [".jpg", ".jpeg"]:
        return f"data:image/jpeg;base64,{x}"
    else:
        raise ValueError(f"Unsupported image format: {image_path.suffix}")


def get_caption(
    client,
    traj_dir,
    captioner_model="gpt-4o-2024-11-20",
    temperature=0,
    max_completion_tokens=1024,
    seed=0,
):
    """Get caption for the last screenshot (not used for false positive judging)."""
    return "[Caption not available]"


def create_fp_chat_messages_from_trajectory(
    instruction,
    traj_dir,
    sys_prompt_version="v1",
    client=None,
    skip_caption=True,
):
    """
    Create chat messages for false positive judging.
    This is similar to aer.py but uses the false positive system prompt.
    """
    if sys_prompt_version == "v1":
        system_message = SYS_PROMPT_FP_V1
    elif sys_prompt_version == "v2":
        system_message = SYS_PROMPT_FP_V2
    else:
        system_message = SYS_PROMPT_FP_V1

    # Load trajectory
    traj_path = os.path.join(traj_dir, "traj.jsonl")
    if os.path.exists(traj_path):
        with open(traj_path, "r", encoding="utf-8") as f:
            exec_traj = [json.loads(line) for line in f if line.strip()]
    else:
        exec_traj = []

    # Format steps
    steps_str = format_steps(exec_traj)

    # For false positive tests, we use a11y_tree or a caption
    a11y_tree = None
    if os.path.exists(os.path.join(traj_dir, "better_log.json")):
        with open(os.path.join(traj_dir, "better_log.json"), "r", encoding="utf-8") as f:
            log_data = json.load(f)
            # Get the last step's a11y_tree if available
            if "steps" in log_data and log_data["steps"]:
                last_step = log_data["steps"][-1]
                if "a11y_tree" in last_step:
                    a11y_tree = last_step["a11y_tree"]

    # Build user message
    user_message = f"""User Intent: {instruction}

Action History:
{steps_str}

"""
    if a11y_tree:
        user_message += f"""The detailed final state of the accessibility tree:
```md
{a11y_tree[:15000]}
```
"""
    else:
        # Try to get screenshot
        if exec_traj:
            last_screenshot = exec_traj[-1].get("screenshot_file", "step_0.png")
            screenshot_path = os.path.join(traj_dir, last_screenshot)
            if os.path.exists(screenshot_path):
                image_base64 = image_to_base64(screenshot_path)
                if image_base64:
                    # Return image message instead
                    return [
                        {"role": "system", "content": system_message},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"User Intent: {instruction}\n\nAction History:\n{steps_str}\n\nThe last snapshot of the screenshot is shown in the image."},
                                {"type": "image_url", "image_url": {"url": image_base64}},
                            ],
                        },
                    ]
        user_message += "[No accessibility tree or screenshot available]"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]
