import base64
import json
import logging
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from http import HTTPStatus
from io import BytesIO
from typing import Dict, List

import backoff
import requests

# Optional provider SDKs. The benchmark can still run without them
# as long as the chosen `--model` doesn't require the missing SDK.
try:
    import dashscope  # type: ignore
except ImportError:  # pragma: no cover
    dashscope = None

try:
    import google.generativeai as genai  # type: ignore
except ImportError:  # pragma: no cover
    genai = None

try:
    import openai  # type: ignore
except ImportError:  # pragma: no cover
    class _OpenAIStub:
        class RateLimitError(Exception): ...
        class BadRequestError(Exception): ...
        class InternalServerError(Exception): ...
    openai = _OpenAIStub()  # type: ignore

try:
    import tiktoken  # type: ignore
except ImportError:  # pragma: no cover
    tiktoken = None

try:
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover
    Image = None

try:
    from google.api_core.exceptions import InvalidArgument, ResourceExhausted, InternalServerError, BadRequest  # type: ignore
except ImportError:  # pragma: no cover
    class InvalidArgument(Exception): ...
    class ResourceExhausted(Exception): ...
    class InternalServerError(Exception): ...
    class BadRequest(Exception): ...

try:
    from groq import Groq  # type: ignore
except ImportError:  # pragma: no cover
    Groq = None
from requests.exceptions import SSLError

from mm_agents.accessibility_tree_wrap.heuristic_retrieve import filter_nodes, draw_bounding_boxes
from mm_agents.prompts import SYS_PROMPT_IN_SCREENSHOT_OUT_CODE, SYS_PROMPT_IN_SCREENSHOT_OUT_ACTION, \
    SYS_PROMPT_IN_A11Y_OUT_CODE, SYS_PROMPT_IN_A11Y_OUT_ACTION, \
    SYS_PROMPT_IN_BOTH_OUT_CODE, SYS_PROMPT_IN_BOTH_OUT_ACTION, \
    SYS_PROMPT_IN_SOM_OUT_TAG

logger = logging.getLogger("desktopenv.agent")


def _safe_for_log(s):
    """Make string safe for logging on consoles with non-UTF-8 encoding (e.g. Windows GBK)."""
    if s is None:
        return None
    return s.encode("ascii", "replace").decode("ascii")


pure_text_settings = ['a11y_tree']

attributes_ns_ubuntu = "https://accessibility.windows.example.org/ns/attributes"
attributes_ns_windows = "https://accessibility.windows.example.org/ns/attributes"
state_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/state"
state_ns_windows = "https://accessibility.windows.example.org/ns/state"
component_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/component"
component_ns_windows = "https://accessibility.windows.example.org/ns/component"
value_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/value"
value_ns_windows = "https://accessibility.windows.example.org/ns/value"
class_ns_windows = "https://accessibility.windows.example.org/ns/class"
# More namespaces defined in OSWorld, please check desktop_env/server/main.py


# Function to encode the image
def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')


def encoded_img_to_pil_img(data_str):
    base64_str = data_str.replace("data:image/png;base64,", "")
    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))

    return image


def save_to_tmp_img_file(data_str):
    base64_str = data_str.replace("data:image/png;base64,", "")
    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))

    tmp_img_path = os.path.join(tempfile.mkdtemp(), "tmp_img.png")
    image.save(tmp_img_path)

    return tmp_img_path


def linearize_accessibility_tree(accessibility_tree, platform="ubuntu"):

    if platform == "ubuntu":
        _attributes_ns = attributes_ns_ubuntu
        _state_ns = state_ns_ubuntu
        _component_ns = component_ns_ubuntu
        _value_ns = value_ns_ubuntu
    elif platform == "windows":
        _attributes_ns = attributes_ns_windows
        _state_ns = state_ns_windows
        _component_ns = component_ns_windows
        _value_ns = value_ns_windows
    else:
        raise ValueError("Invalid platform, must be 'ubuntu' or 'windows'")

    filtered_nodes = filter_nodes(ET.fromstring(accessibility_tree), platform)
    linearized_accessibility_tree = ["tag\tname\ttext\tclass\tdescription\tposition (top-left x&y)\tsize (w&h)"]

    # Linearize the accessibility tree nodes into a table format
    for node in filtered_nodes:
        if node.text:
            text = (
                node.text if '"' not in node.text \
                    else '"{:}"'.format(node.text.replace('"', '""'))
            )

        elif node.get("{{{:}}}class".format(class_ns_windows), "").endswith("EditWrapper") \
                and node.get("{{{:}}}value".format(_value_ns)):
            node_text = node.get("{{{:}}}value".format(_value_ns), "")
            text = (node_text if '"' not in node_text \
                        else '"{:}"'.format(node_text.replace('"', '""'))
                    )
        else:
            text = '""'

        linearized_accessibility_tree.append(
            "{:}\t{:}\t{:}\t{:}\t{:}\t{:}\t{:}".format(
                node.tag, node.get("name", ""),
                text,
                node.get("{{{:}}}class".format(_attributes_ns), "") if platform == "ubuntu" else node.get("{{{:}}}class".format(class_ns_windows), ""),
                node.get("{{{:}}}description".format(_attributes_ns), ""),
                node.get('{{{:}}}screencoord'.format(_component_ns), ""),
                node.get('{{{:}}}size'.format(_component_ns), "")
            )
        )

    return "\n".join(linearized_accessibility_tree)


def tag_screenshot(screenshot, accessibility_tree, platform="ubuntu"):
    nodes = filter_nodes(ET.fromstring(accessibility_tree), platform=platform, check_image=True)
    # Make tag screenshot
    marks, drew_nodes, element_list, tagged_screenshot = draw_bounding_boxes(nodes, screenshot)

    return marks, drew_nodes, tagged_screenshot, element_list


def parse_actions_from_string(input_string):
    if input_string.strip() in ['WAIT', 'DONE', 'FAIL']:
        return [input_string.strip()]
    # Search for a JSON string within the input string
    actions = []
    matches = re.findall(r'```json\s+(.*?)\s+```', input_string, re.DOTALL)
    if matches:
        # Assuming there's only one match, parse the JSON string into a dictionary
        try:
            for match in matches:
                action_dict = json.loads(match)
                actions.append(action_dict)
            return actions
        except json.JSONDecodeError as e:
            return f"Failed to parse JSON: {e}"
    else:
        matches = re.findall(r'```\s+(.*?)\s+```', input_string, re.DOTALL)
        if matches:
            # Assuming there's only one match, parse the JSON string into a dictionary
            try:
                for match in matches:
                    action_dict = json.loads(match)
                    actions.append(action_dict)
                return actions
            except json.JSONDecodeError as e:
                return f"Failed to parse JSON: {e}"
        else:
            try:
                action_dict = json.loads(input_string)
                return [action_dict]
            except json.JSONDecodeError:
                raise ValueError("Invalid response format: " + input_string)


def retrieve_codes_outside_blocks(input_string):
    codes = []
    lines = [line.strip() for line in input_string.split('\n') if line.strip()]
    # Only extract WAIT/DONE/FAIL if they appear as standalone lines (exact match)
    if 'WAIT' in lines: codes.append('WAIT')
    if 'DONE' in lines: codes.append('DONE')
    if 'FAIL' in lines:
        codes.append('FAIL')
    return codes


def parse_code_from_string(input_string):
    """
    Parse pyautogui code and thought from model output.
    Be tolerant to imperfect formatting so that we almost always
    extract at least one actionable code snippet.
    Also extracts any text outside code blocks as the thought.
    """
    if not isinstance(input_string, str):
        return [], ""

    special_codes_outside_block = retrieve_codes_outside_blocks(input_string)
    # normalize separators
    input_string = "\n".join([line.strip() for line in input_string.split(';') if line.strip()])
    if input_string.strip() in ['WAIT', 'DONE', 'FAIL']:
        return [input_string.strip()], ""

    # Extract text outside code blocks as thought
    thought = input_string
    pattern = r"```(?:\w+\s+)?(.*?)```"
    matches = re.findall(pattern, input_string, re.DOTALL)
    if matches:
        for match in matches:
            thought = thought.replace(f"```{match.strip()}```", "").replace(f"```json\n{match.strip()}\n```", "")
            thought = thought.replace(f"```\n{match.strip()}\n```", "")
            thought = thought.replace(f"```{match.strip()}```", "")
        thought = thought.strip()

    codes: List[str] = []

    if matches:
        for match in matches:
            match = match.strip()
            commands = ['WAIT', 'DONE', 'FAIL']

            if match in commands:
                codes.append(match.strip())
            elif match.split('\n')[-1] in commands:
                if len(match.split('\n')) > 1:
                    codes.append("\n".join(match.split('\n')[:-1]))
                codes.append(match.split('\n')[-1])
            else:
                codes.append(match)
    else:
        # Fallback: try to extract at least one line containing pyautogui.*
        candidate_lines = []
        for line in input_string.splitlines():
            line = line.strip()
            if not line:
                continue
            if 'pyautogui.' in line:
                candidate_lines.append(line)
        if candidate_lines:
            # Build a minimal script from these lines
            codes.append("\n".join(candidate_lines))

    # Append special codes like WAIT/DONE/FAIL if model mentioned them outside code blocks
    for c in special_codes_outside_block:
        if c not in codes:
            codes.append(c)

    return codes, thought


def parse_code_from_som_string(input_string, masks):
    # parse the output string by masks
    tag_vars = ""
    for i, mask in enumerate(masks):
        x, y, w, h = mask
        tag_vars += "tag_" + str(i + 1) + "=" + "({}, {})".format(int(x + w // 2), int(y + h // 2))
        tag_vars += "\n"

    actions, _ = parse_code_from_string(input_string)

    for i, action in enumerate(actions):
        if action.strip() in ['WAIT', 'DONE', 'FAIL']:
            pass
        else:
            action = tag_vars + action
            actions[i] = action

    return actions


def trim_accessibility_tree(linearized_accessibility_tree, max_tokens):
    enc = tiktoken.encoding_for_model("gpt-4")
    tokens = enc.encode(linearized_accessibility_tree)
    if len(tokens) > max_tokens:
        linearized_accessibility_tree = enc.decode(tokens[:max_tokens])
        linearized_accessibility_tree += "[...]\n"
    return linearized_accessibility_tree


class PromptAgent:
    def __init__(
            self,
            platform="ubuntu",
            model="gpt-4-vision-preview",
            max_tokens=1500,
            top_p=0.9,
            temperature=0.5,
            action_space="computer_13",
            observation_type="screenshot_a11y_tree",
            # observation_type can be in ["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"]
            max_trajectory_length=3,
            a11y_tree_max_tokens=10000
    ):
        self.platform = platform
        self.model = model
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.action_space = action_space
        self.observation_type = observation_type
        self.max_trajectory_length = max_trajectory_length
        self.a11y_tree_max_tokens = a11y_tree_max_tokens

        self.thoughts = []
        self.actions = []
        self.observations = []


        if observation_type == "screenshot":
            if action_space == "computer_13":
                self.system_message = SYS_PROMPT_IN_SCREENSHOT_OUT_ACTION
            elif action_space == "pyautogui":
                self.system_message = SYS_PROMPT_IN_SCREENSHOT_OUT_CODE
            else:
                raise ValueError("Invalid action space: " + action_space)
        elif observation_type == "a11y_tree":
            if action_space == "computer_13":
                self.system_message = SYS_PROMPT_IN_A11Y_OUT_ACTION
            elif action_space == "pyautogui":
                self.system_message = SYS_PROMPT_IN_A11Y_OUT_CODE
            else:
                raise ValueError("Invalid action space: " + action_space)
        elif observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = SYS_PROMPT_IN_BOTH_OUT_ACTION
            elif action_space == "pyautogui":
                self.system_message = SYS_PROMPT_IN_BOTH_OUT_CODE
            else:
                raise ValueError("Invalid action space: " + action_space)
        elif observation_type == "som":
            if action_space == "computer_13":
                raise ValueError("Invalid action space: " + action_space)
            elif action_space == "pyautogui":
                self.system_message = SYS_PROMPT_IN_SOM_OUT_TAG
            else:
                raise ValueError("Invalid action space: " + action_space)
        else:
            raise ValueError("Invalid experiment type: " + observation_type)

    def predict(self, instruction: str, obs: Dict) -> List:
        """
        Predict the next action(s) based on the current observation.
        """
        system_message = self.system_message + "\nYou are asked to complete the following task: {}".format(instruction)

        # Prepare the payload for the API call
        messages = []
        masks = None

        # Append the system message
        messages.append({
            "role": "system",
            "content": [
                {
                    "type": "input_text" if self.model == "computer-use-preview" else "text",
                    "text": system_message
                },
            ]
        })

        assert len(self.observations) == len(self.actions) and len(self.actions) == len(self.thoughts) \
            , "The number of observations and actions should be the same."

        # Truncate the trajectory if it exceeds the max_trajectory_length
        if len(self.observations) > self.max_trajectory_length:
            if self.max_trajectory_length == 0:
                _observations = []
                _actions = []
                _thoughts = []
            else:
                _observations = self.observations[-self.max_trajectory_length:]
                _actions = self.actions[-self.max_trajectory_length:]
                _thoughts = self.thoughts[-self.max_trajectory_length:]
        else:
            _observations = self.observations
            _actions = self.actions
            _thoughts = self.thoughts

        # Append trajectory of observations, thoughts, and actions taken so far
        for previous_obs, previous_action, previous_thought in zip(_observations, _actions, _thoughts):
            if self.observation_type == "screenshot_a11y_tree":
                _screenshot = previous_obs["screenshot"]
                _linearized_accessibility_tree = previous_obs["accessibility_tree"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text" if self.model == "computer-use-preview" else "text",
                            "text": "Given the screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                                _linearized_accessibility_tree)
                        },
                        {
                            "type": "input_image" if self.model == "computer-use-preview" else "image_url",
                            "image_url": f"data:image/png;base64,{_screenshot}" if self.model == "computer-use-preview" else {
                                "url": f"data:image/png;base64,{_screenshot}",
                                "detail": "high"
                            }
                        }
                    ]
                })
            elif self.observation_type in ["screenshot", "som"]:
                _screenshot = previous_obs["screenshot"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text" if self.model == "computer-use-preview" else "text",
                            "text": f'Given the {"tagged " if self.observation_type == "som" else ""}screenshot as below. What’s the next step you’ll take to help with the task?'
                        },
                        {
                            "type": "input_image" if self.model == "computer-use-preview" else "image_url",
                            "image_url": f"data:image/png;base64,{_screenshot}" if self.model == "computer-use-preview" else {
                                "url": f"data:image/png;base64,{_screenshot}",
                                "detail": "high"
                            }
                        }
                    ]
                })
            elif self.observation_type == "a11y_tree":
                _linearized_accessibility_tree = previous_obs["accessibility_tree"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text" if self.model == "computer-use-preview" else "text",
                            "text": "Given the info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                                _linearized_accessibility_tree)
                        }
                    ]
                })
            else:
                raise ValueError("Invalid observation_type type: " + self.observation_type)

            messages.append({
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text" if self.model == "computer-use-preview" else "text",
                        "text": previous_thought.strip() if len(previous_thought) > 0 else "No valid action"
                    },
                ]
            })

        # Append the current observation
        if self.observation_type in ["screenshot", "screenshot_a11y_tree"]:
            base64_image = encode_image(obs["screenshot"])
            linearized_accessibility_tree = linearize_accessibility_tree(accessibility_tree=obs["accessibility_tree"],
                                                                         platform=self.platform)
            logger.debug("LINEAR AT: %s", _safe_for_log(linearized_accessibility_tree) if 'a11y' in self.observation_type else None)

            if linearized_accessibility_tree:
                linearized_accessibility_tree = trim_accessibility_tree(linearized_accessibility_tree,
                                                                        self.a11y_tree_max_tokens)

            if self.observation_type == "screenshot_a11y_tree":
                self.observations.append({
                    "screenshot": base64_image,
                    "accessibility_tree": linearized_accessibility_tree
                })
            else:
                self.observations.append({
                    "screenshot": base64_image,
                    "accessibility_tree": None
                })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "input_text" if self.model == "computer-use-preview" else "text",
                        "text": "Given the screenshot as below. What's the next step that you will do to help with the task?"
                        if self.observation_type == "screenshot"
                        else "Given the screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                            linearized_accessibility_tree)
                    },
                    {
                        "type": "input_image" if self.model == "computer-use-preview" else "image_url",
                        "image_url": f"data:image/png;base64,{base64_image}" if self.model == "computer-use-preview" else {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            })
        elif self.observation_type == "a11y_tree":
            linearized_accessibility_tree = linearize_accessibility_tree(accessibility_tree=obs["accessibility_tree"],
                                                                         platform=self.platform)
            logger.debug("LINEAR AT: %s", _safe_for_log(linearized_accessibility_tree))

            if linearized_accessibility_tree:
                linearized_accessibility_tree = trim_accessibility_tree(linearized_accessibility_tree,
                                                                        self.a11y_tree_max_tokens)

            self.observations.append({
                "screenshot": None,
                "accessibility_tree": linearized_accessibility_tree
            })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "input_text" if self.model == "computer-use-preview" else "text",
                        "text": "Given the info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                            linearized_accessibility_tree)
                    }
                ]
            })
        elif self.observation_type == "som":
            # Add som to the screenshot
            masks, drew_nodes, tagged_screenshot, linearized_accessibility_tree = tag_screenshot(obs["screenshot"], obs[
                "accessibility_tree"], self.platform)
            base64_image = encode_image(tagged_screenshot)
            logger.debug("LINEAR AT: %s", _safe_for_log(linearized_accessibility_tree))

            if linearized_accessibility_tree:
                linearized_accessibility_tree = trim_accessibility_tree(linearized_accessibility_tree,
                                                                        self.a11y_tree_max_tokens)

            self.observations.append({
                "screenshot": base64_image,
                "accessibility_tree": linearized_accessibility_tree
            })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "input_text" if self.model == "computer-use-preview" else "text",
                        "text": "Given the tagged screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                            linearized_accessibility_tree)
                    },
                    {
                        "type": "input_image" if self.model == "computer-use-preview" else "image_url",
                        "image_url": f"data:image/png;base64,{base64_image}" if self.model == "computer-use-preview" else {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            })
        else:
            raise ValueError("Invalid observation_type type: " + self.observation_type)

        # with open("messages.json", "w") as f:
        #     f.write(json.dumps(messages, indent=4))

        # logger.info("PROMPT: %s", messages)

        try:
            response = self.call_llm({
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "top_p": self.top_p,
                "temperature": self.temperature
            })
        except Exception as e:
            logger.error("Failed to call " + self.model + ", Error: " + str(e))
            response = ""

        logger.info("RESPONSE: %s", _safe_for_log(response))

        try:
            # 只有主模型实际返回了内容（而非 API 失败返回空字符串）时才尝试 fallback
            main_model_returned_content = bool(response)

            actions, thought = self.parse_actions(response, masks)

            # 主模型 API 调用失败时，不 fallback，直接标记为 FAIL
            # 只有主模型返回了内容但解析不出有效代码时，才尝试 qwen-vl-max fallback
            if not actions or (actions and all(a.strip() in ['WAIT', 'DONE', 'FAIL'] for a in actions)):
                if main_model_returned_content and self.action_space == "pyautogui":
                    logger.info("Main model produced no code, trying qwen-vl-max fallback...")
                    fallback_result = self._call_qwen_fallback(messages, obs, thought)
                    if fallback_result:
                        actions, thought = fallback_result
                        logger.info("Qwen fallback succeeded, generated actions: %s", actions)
                    else:
                        actions = ["FAIL"]

            # 如果模型没有给出任何可解析的动作，也视为一次“明确拒绝/放弃”，用 FAIL 标记出来，
            # 避免在日志中表现为完全没有行为。
            if not actions:
                actions = ["FAIL"]

            self.actions.append(actions)
            if self.model == "computer-use-preview":
                print(response)
                match response[0]['type']:
                    case 'reasoning':
                        self.thoughts.append(response[0]['summary'][0]['text'])
                    case 'message':
                        self.thoughts.append(response[0]['content'][0]['text'])
            else:
                self.thoughts.append(thought if thought else response)
        except ValueError as e:
            print("Failed to parse action from response", e)
            # 解析完全失败时，也返回一个 FAIL，让评测能记录“拒绝/失败”而不是沉默
            actions = ["FAIL"]
            self.thoughts.append("")

        return response, actions

    @backoff.on_exception(
        backoff.constant,
        # here you should add more model exceptions as you want,
        # but you are forbidden to add "Exception", that is, a common type of exception
        # because we want to catch this kind of Exception in the outside to ensure each example won't exceed the time limit
        (
                # General exceptions
                SSLError,

                # OpenAI exceptions
                openai.RateLimitError,
                openai.BadRequestError,
                openai.InternalServerError,

                # Google exceptions
                InvalidArgument,
                ResourceExhausted,
                InternalServerError,
                BadRequest,

                # Groq exceptions
                # todo: check
        ),
        interval=30,
        max_tries=10
    )
    def call_llm(self, payload):

        if self.model.startswith("gpt") or self.model.startswith("o") or self.model.startswith("gemini"):
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"
            }
            if self.model.startswith("o"):
                del payload['max_tokens']
                del payload['top_p']
                del payload['temperature']
            logger.info("Generating content with GPT model: %s", self.model)
            
            # Support custom API base URL (for aaaapi.com and other OpenAI-compatible APIs)
            api_base = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com/v1')
            api_base = api_base.rstrip('/')
            # If base URL already includes /chat/completions path, use it directly
            if '/chat/completions' in api_base:
                api_endpoint = api_base
            else:
                api_endpoint = f"{api_base}/chat/completions"
            
            response = requests.post(
                api_endpoint,
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                if response.json()['error']['code'] == "context_length_exceeded":
                    logger.error("Context length exceeded. Retrying with a smaller context.")
                    payload["messages"] = [payload["messages"][0]] + payload["messages"][-1:]
                    retry_response = requests.post(
                        api_endpoint,
                        headers=headers,
                        json=payload
                    )
                    if retry_response.status_code != 200:
                        logger.error(
                            "Failed to call LLM even after attempt on shortening the history: " + retry_response.text)
                        return ""

                logger.error("Failed to call LLM: " + response.text)
                time.sleep(5)
                return ""
            else:
                return response.json()['choices'][0]['message']['content']

        elif self.model == "computer-use-preview":
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"
            }
            logger.info("Generating content with computer-use-preview model")
            
            # For computer-use-preview, we only want the system message and the most recent message
            filtered_messages = []
            
            # Add system message if present
            if len(payload["messages"]) > 1 and payload["messages"][0]["role"] == "system":
                filtered_messages.append(payload["messages"][0])
            
            # Add only the most recent message
            filtered_messages.append(payload["messages"][-1])
            
            # Prepare the request payload
            request_payload = {
                "model": "computer-use-preview",
                "tools": [{
                    "type": "computer_use_preview",
                    "display_width": 1024,
                    "display_height": 768,
                    "environment": "linux"  # Use the platform from the agent's configuration
                }],
                "input": filtered_messages,
                "reasoning": {
                    "generate_summary": "concise"
                },
                "truncation": "auto"
            }
            
            # Make the API call
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers=headers,
                json=request_payload
            )

            response_data = response.json()
            #logger.info(json.dumps(response_data["output"], indent=2))
            logger.info(json.dumps(response_data, indent=2))

            if response.status_code != 200:
                raise openai.InternalServerError(response.text)
            else:
                # Store any pending safety checks to mark them as acknowledged in the next request
                if "pending_safety_checks" in response_data["output"][1]:
                    self.safety_checks.append(response_data["output"][1]["pending_safety_checks"])
                return response_data["output"]
    
        elif self.model.startswith("claude"):
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            claude_messages = []

            for i, message in enumerate(messages):
                claude_message = {
                    "role": message["role"],
                    "content": []
                }
                assert len(message["content"]) in [1, 2], "One text, or one text with one image"
                for part in message["content"]:

                    if part['type'] == "image_url":
                        image_source = {}
                        image_source["type"] = "base64"
                        image_source["media_type"] = "image/png"
                        image_source["data"] = part['image_url']['url'].replace("data:image/png;base64,", "")
                        claude_message['content'].append({"type": "image", "source": image_source})

                    if part['type'] == "text":
                        claude_message['content'].append({"type": "text", "text": part['text']})

                claude_messages.append(claude_message)

            # the claude not support system message in our endpoint, so we concatenate it at the first user message
            if claude_messages[0]['role'] == "system":
                claude_system_message_item = claude_messages[0]['content'][0]
                claude_messages[1]['content'].insert(0, claude_system_message_item)
                claude_messages.pop(0)

            logger.debug("CLAUDE MESSAGE: %s", repr(claude_messages))

            headers = {
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": claude_messages,
                "temperature": temperature,
                "top_p": top_p
            }

            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )

            if response.status_code != 200:

                logger.error("Failed to call LLM: " + response.text)
                time.sleep(5)
                return ""
            else:
                return response.json()['content'][0]['text']

        elif self.model.startswith("mistral"):
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            assert self.observation_type in pure_text_settings, f"The model {self.model} can only support text-based input, please consider change based model or settings"

            mistral_messages = []

            for i, message in enumerate(messages):
                mistral_message = {
                    "role": message["role"],
                    "content": ""
                }

                for part in message["content"]:
                    mistral_message['content'] = part['text'] if part['type'] == "text" else ""

                mistral_messages.append(mistral_message)

            from openai import OpenAI

            client = OpenAI(api_key=os.environ["TOGETHER_API_KEY"],
                            base_url='https://api.together.xyz',
                            )

            flag = 0
            while True:
                try:
                    if flag > 20:
                        break
                    logger.info("Generating content with model: %s", self.model)
                    response = client.chat.completions.create(
                        messages=mistral_messages,
                        model=self.model,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        temperature=temperature
                    )
                    break
                except:
                    if flag == 0:
                        mistral_messages = [mistral_messages[0]] + mistral_messages[-1:]
                    else:
                        mistral_messages[-1]["content"] = ' '.join(mistral_messages[-1]["content"].split()[:-500])
                    flag = flag + 1

            try:
                return response.choices[0].message.content
            except Exception as e:
                print("Failed to call LLM: " + str(e))
                return ""

        elif self.model.startswith("THUDM"):
            # THUDM/cogagent-chat-hf
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            cog_messages = []

            for i, message in enumerate(messages):
                cog_message = {
                    "role": message["role"],
                    "content": []
                }

                for part in message["content"]:
                    if part['type'] == "image_url":
                        cog_message['content'].append(
                            {"type": "image_url", "image_url": {"url": part['image_url']['url']}})

                    if part['type'] == "text":
                        cog_message['content'].append({"type": "text", "text": part['text']})

                cog_messages.append(cog_message)

            # the cogagent not support system message in our endpoint, so we concatenate it at the first user message
            if cog_messages[0]['role'] == "system":
                cog_system_message_item = cog_messages[0]['content'][0]
                cog_messages[1]['content'].insert(0, cog_system_message_item)
                cog_messages.pop(0)

            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": cog_messages,
                "temperature": temperature,
                "top_p": top_p
            }

            base_url = "http://127.0.0.1:8000"

            response = requests.post(f"{base_url}/v1/chat/completions", json=payload, stream=False)
            if response.status_code == 200:
                decoded_line = response.json()
                content = decoded_line.get("choices", [{}])[0].get("message", "").get("content", "")
                return content
            else:
                print("Failed to call LLM: ", response.status_code)
                return ""

        elif self.model.startswith("gemini-original"):
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            gemini_messages = []
            for i, message in enumerate(messages):
                role_mapping = {
                    "assistant": "model",
                    "user": "user",
                    "system": "system"
                }
                assert len(message["content"]) in [1, 2], "One text, or one text with one image"
                gemini_message = {
                    "role": role_mapping[message["role"]],
                    "parts": []
                }

                # The gemini only support the last image as single image input
                for part in message["content"]:

                    if part['type'] == "image_url":
                        # Put the image at the beginning of the message
                        gemini_message['parts'].insert(0, encoded_img_to_pil_img(part['image_url']['url']))
                    elif part['type'] == "text":
                        gemini_message['parts'].append(part['text'])
                    else:
                        raise ValueError("Invalid content type: " + part['type'])

                gemini_messages.append(gemini_message)

            # the system message of gemini-1.5-pro-latest need to be inputted through model initialization parameter
            system_instruction = None
            if gemini_messages[0]['role'] == "system":
                system_instruction = gemini_messages[0]['parts'][0]
                gemini_messages.pop(0)

            api_key = os.environ.get("GENAI_API_KEY")
            assert api_key is not None, "Please set the GENAI_API_KEY environment variable"
            genai.configure(api_key=api_key)
            logger.info("Generating content with Gemini model: %s", self.model)
            gemini_model = genai.GenerativeModel(
                self.model,
                system_instruction=system_instruction
            )

            with open("response.json", "w") as f:
                messages_to_save = []
                for message in gemini_messages:
                    messages_to_save.append({
                        "role": message["role"],
                        "content": [part if isinstance(part, str) else "image" for part in message["parts"]]
                    })
                json.dump(messages_to_save, f, indent=4)

            response = gemini_model.generate_content(
                gemini_messages,
                generation_config={
                    "candidate_count": 1,
                    # "max_output_tokens": max_tokens,
                    "top_p": top_p,
                    "temperature": temperature
                },
                safety_settings={
                    "harassment": "block_none",
                    "hate": "block_none",
                    "sex": "block_none",
                    "danger": "block_none"
                },
                request_options={"timeout": 120}
            )

            return response.text

        elif self.model == "llama3-70b":
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            assert self.observation_type in pure_text_settings, f"The model {self.model} can only support text-based input, please consider change based model or settings"

            groq_messages = []

            for i, message in enumerate(messages):
                groq_message = {
                    "role": message["role"],
                    "content": ""
                }

                for part in message["content"]:
                    groq_message['content'] = part['text'] if part['type'] == "text" else ""

                groq_messages.append(groq_message)

            # The implementation based on Groq API
            client = Groq(
                api_key=os.environ.get("GROQ_API_KEY"),
            )

            flag = 0
            while True:
                try:
                    if flag > 20:
                        break
                    logger.info("Generating content with model: %s", self.model)
                    response = client.chat.completions.create(
                        messages=groq_messages,
                        model="llama3-70b-8192",
                        max_tokens=max_tokens,
                        top_p=top_p,
                        temperature=temperature
                    )
                    break
                except:
                    if flag == 0:
                        groq_messages = [groq_messages[0]] + groq_messages[-1:]
                    else:
                        groq_messages[-1]["content"] = ' '.join(groq_messages[-1]["content"].split()[:-500])
                    flag = flag + 1

            try:
                return response.choices[0].message.content
            except Exception as e:
                print("Failed to call LLM: " + str(e))
                return ""

        elif self.model.startswith("qwen"):
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            qwen_messages = []

            for i, message in enumerate(messages):
                qwen_message = {
                    "role": message["role"],
                    "content": []
                }
                assert len(message["content"]) in [1, 2], "One text, or one text with one image"
                for part in message["content"]:
                    qwen_message['content'].append(
                        {"image": "file://" + save_to_tmp_img_file(part['image_url']['url'])}) if part[
                                                                                                      'type'] == "image_url" else None
                    qwen_message['content'].append({"text": part['text']}) if part['type'] == "text" else None

                qwen_messages.append(qwen_message)

            flag = 0
            response = None
            last_error = None
            while True:
                try:
                    if flag > 20:
                        break
                    logger.info("Generating content with model: %s", self.model)

                    if self.model in ["qwen-vl-plus", "qwen-vl-max"]:
                        response = dashscope.MultiModalConversation.call(
                            model=self.model,
                            messages=qwen_messages,
                            result_format="message",
                            max_length=max_tokens,
                            top_p=top_p,
                            temperature=temperature
                        )

                    elif self.model in ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-0428", "qwen-max-0403",
                                        "qwen-max-0107", "qwen-max-longcontext"]:
                        response = dashscope.Generation.call(
                            model=self.model,
                            messages=qwen_messages,
                            result_format="message",
                            max_length=max_tokens,
                            top_p=top_p,
                            temperature=temperature
                        )

                    else:
                        raise ValueError("Invalid model: " + self.model)

                    if response.status_code == HTTPStatus.OK:
                        break
                    else:
                        logger.error('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                            response.request_id, response.status_code,
                            response.code, response.message
                        ))
                        raise Exception("Failed to call LLM: " + response.message)
                except Exception as e:
                    last_error = e
                    if flag == 0:
                        qwen_messages = [qwen_messages[0]] + qwen_messages[-1:]
                    else:
                        for i in range(len(qwen_messages[-1]["content"])):
                            if "text" in qwen_messages[-1]["content"][i]:
                                qwen_messages[-1]["content"][i]["text"] = ' '.join(
                                    qwen_messages[-1]["content"][i]["text"].split()[:-500])
                    flag = flag + 1

            try:
                if response is None:
                    raise RuntimeError(f"Qwen call failed after retries: {last_error}")
                if self.model in ["qwen-vl-plus", "qwen-vl-max"]:
                    return response['output']['choices'][0]['message']['content'][0]['text']
                else:
                    return response['output']['choices'][0]['message']['content']

            except Exception as e:
                print("Failed to call LLM: " + str(e))
                return ""

        elif self.model.startswith("Qwen2.5-VL") or self.model.startswith("Qwen3-VL"):
            # vLLM OpenAI-compatible server backend
            # Server: set VLLM_BASE_URL=http://<server-ip>:8080/v1
            # Model name: set VLLM_MODEL=Qwen2.5-VL-7B-Instruct
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            vllm_base_url = os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:8080/v1")
            vllm_model = os.environ.get("VLLM_MODEL", self.model)

            # Convert messages to vLLM-compatible format (OpenAI vision format)
            vllm_messages = []
            for message in messages:
                vllm_content = []
                for part in message["content"]:
                    if part["type"] == "image_url":
                        img_url = part["image_url"]["url"]
                        # Ensure data URI format for vLLM
                        if not img_url.startswith("data:"):
                            img_url = f"data:image/png;base64,{img_url}"
                        vllm_content.append({
                            "type": "image_url",
                            "image_url": {"url": img_url}
                        })
                    elif part["type"] == "text":
                        vllm_content.append({"type": "text", "text": part["text"]})
                vllm_messages.append({"role": message["role"], "content": vllm_content})

            request_payload = {
                "model": vllm_model,
                "messages": vllm_messages,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "temperature": temperature,
            }

            logger.info("Calling vLLM server: %s with model %s", vllm_base_url, vllm_model)

            flag = 0
            while True:
                try:
                    if flag > 10:
                        break
                    resp = requests.post(
                        f"{vllm_base_url}/chat/completions",
                        json=request_payload,
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        logger.error("vLLM request failed: %s - %s", resp.status_code, resp.text)
                        time.sleep(2)
                        flag += 1
                except requests.exceptions.Timeout:
                    logger.error("vLLM request timeout, retrying...")
                    flag += 1
                except Exception as e:
                    logger.error("vLLM call error: %s", e)
                    time.sleep(2)
                    flag += 1

            return ""

        else:
            raise ValueError("Invalid model: " + self.model)

    def _call_qwen_fallback(self, messages, obs, thought):
        """
        当主模型无法生成 pyautogui 代码时，使用 qwen-vl-max 作为 fallback，
        基于截图、a11y tree 和主模型的文本指令生成 pyautogui 代码。
        与 SYS_PROMPT_IN_A11Y_OUT_CODE 模板保持一致。
        """
        if dashscope is None:
            logger.warning("dashscope not installed, cannot use qwen-vl-max fallback")
            return None

        try:
            base64_image = encode_image(obs["screenshot"])
            linearized_tree = linearize_accessibility_tree(obs["accessibility_tree"], self.platform)

            # 为主模型输出生成的文本指令作为参考
            instruction_context = ""
            if thought:
                instruction_context = f"\n主模型（gpt-5.1）输出的指令参考：\n{thought}"

            qwen_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": "file://" + save_to_tmp_img_file(f"data:image/png;base64,{base64_image}"),
                        },
                        {
                            "text": f"""You are an agent which follow my instruction and perform desktop computer tasks as instructed.
You have good knowledge of computer and good internet connection and assume your code will run on a computer for controlling the mouse and keyboard.
For each step, you will get an observation of the desktop by accessibility tree, which is based on AT-SPI library. And you will predict the action of the computer based on the accessibility tree.

You are required to use `pyautogui` to perform the action grounded to the observation, but DONOT use the `pyautogui.locateCenterOnScreen` function to locate the element you want to operate with since we have no image of the element you want to operate with. DONOT USE `pyautogui.screenshot()` to make screenshot.
Return one line or multiple lines of python code to perform the action each time, be time efficient. When predicting multiple lines of code, make some small sleep like `time.sleep(0.5);` interval so that the machine could take; Each time you need to predict a complete code, no variables or function can be shared from history
You need to to specify the coordinates of by yourself based on your observation of current observation, but you should be careful to ensure that the coordinates are correct.
You ONLY need to return the code inside a code block, like this:
```python
# your code here
```
Specially, it is also allowed to return the following special code:
When you think you have to wait for some time, return ```WAIT```;
When you think the task can not be done, return ```FAIL```, don't easily say ```FAIL```, try your best to do the task;
When you think the task is done, return ```DONE```.

My computer's password is 'password', feel free to use it when you need sudo rights.

Accessibility tree:
{linearized_tree}{instruction_context}

CRITICAL: After your reflection, you MUST output a code block starting with ```python. Do not output any description or explanation. The code is the ONLY thing that matters after your reflection."""
                        }
                    ]
                }
            ]

            response = dashscope.MultiModalConversation.call(
                model="qwen-vl-max",
                messages=qwen_messages,
                result_format="message",
                max_length=1024,
                top_p=0.9,
                temperature=0.7
            )

            if response.status_code == HTTPStatus.OK:
                qwen_text = response['output']['choices'][0]['message']['content'][0]['text']
                logger.info("Qwen fallback response: %s", _safe_for_log(qwen_text))
                actions, _ = parse_code_from_string(qwen_text)
                if actions:
                    return actions, thought
                else:
                    logger.warning("Qwen fallback produced no parseable code")
                    return None
            else:
                logger.error("Qwen fallback failed: %s", response.message)
                return None

        except Exception as e:
            logger.error("Qwen fallback exception: %s", str(e))
            return None

    def parse_actions(self, response: str, masks=None):
        thought = ""

        if self.model == "computer-use-preview":
            actions = []
            for output in response:
                if output["type"] == "computer_call":
                    output["action"]["action_type"] = output["action"]["type"].upper()
                    actions.append(output["action"])

        elif self.observation_type in ["screenshot", "a11y_tree", "screenshot_a11y_tree"]:
            if self.action_space == "computer_13":
                actions = parse_actions_from_string(response)
            elif self.action_space == "pyautogui":
                actions, thought = parse_code_from_string(response)
            else:
                raise ValueError("Invalid action space: " + self.action_space)

        elif self.observation_type in ["som"]:
            if self.action_space == "computer_13":
                raise ValueError("Invalid action space: " + self.action_space)
            elif self.action_space == "pyautogui":
                actions, thought = parse_code_from_string(response)
            else:
                raise ValueError("Invalid action space: " + self.action_space)

        return actions, thought


    def reset(self, _logger=None):
        global logger
        logger = _logger if _logger is not None else logging.getLogger("desktopenv.agent")

        self.thoughts = []
        self.actions = []
        self.observations = []
