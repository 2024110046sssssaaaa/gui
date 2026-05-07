"""
Agent Factory - Unified agent creation for all LLM providers.

Usage:
    from mobile_safety.agent.agent_factory import create_agent

    agent = create_agent(
        model_name="gpt-4o-2024-05-13",
        seed=42,
        port=5554
    )

Supported providers and model patterns:
  - openai:     "gpt-*" (e.g. "gpt-4o-2024-05-13")
  - anthropic:  "claude-*" (e.g. "claude-3-5-sonnet-20240620")
  - google:     "gemini-*" (e.g. "gemini-1.5-pro-001")
  - qwen:       "qwen-*" (e.g. "qwen-vl-max-latest")
  - deepseek:   "deepseek-*" (e.g. "deepseek-chat")
  - o1:         "o1-*" (e.g. "o1-preview", "o1-mini")
  - openrouter: any model when base_url matches openrouter pattern

Auto-detection priority:
  1. Exact prefix match (e.g. "claude-" -> Anthropic)
  2. Environment variable override (PROVIDER_OVERRIDE)
  3. Base URL heuristic (e.g. OPENAI_BASE_URL containing "openrouter" -> OpenRouter)
"""

import os
import re
import cv2
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from PIL import Image

from mobile_safety.agent.utils import encode_image, parse_response


def normalize_openai_base_url(base_url: str) -> Optional[str]:
    if not base_url:
        return None
    normalized = str(base_url).strip().rstrip("/")
    for suffix in ("/chat/completions", "/responses"):
        if normalized.lower().endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized or None


def uses_openai_compatible_gemini_proxy(model_name: str) -> bool:
    model_lower = (model_name or "").lower()
    if not model_lower.startswith("gemini-"):
        return False

    third_party_base = normalize_openai_base_url(os.environ.get("THIRD_PARTY_PROXY_BASE_URL"))
    openai_base = normalize_openai_base_url(os.environ.get("OPENAI_BASE_URL"))
    raw_auth_forced = os.environ.get("OPENAI_COMPATIBLE_FORCE_RAW_AUTH", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if third_party_base:
        return True
    if raw_auth_forced:
        return True
    return bool(openai_base and "aaaapi.com" in openai_base.lower())


# ── Provider enum ─────────────────────────────────────────────────────────────

class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    O1 = "o1"
    OPENROUTER = "openrouter"
    UNKNOWN = "unknown"


# ── Provider detection ────────────────────────────────────────────────────────

MODEL_PREFIX_MAP = {
    "claude-": Provider.ANTHROPIC,
    "gemini-": Provider.GOOGLE,
    "gpt-": Provider.OPENAI,
    "o1-": Provider.O1,
    "qwen-": Provider.QWEN,
    "deepseek-": Provider.DEEPSEEK,
}


def detect_provider(model_name: str) -> Provider:
    """Auto-detect provider from model name, env vars, and base URL."""
    override = os.environ.get("PROVIDER_OVERRIDE", "").strip().lower()
    if override:
        for p in Provider:
            if p.value == override:
                return p
        raise ValueError(f"Unknown PROVIDER_OVERRIDE: {override!r}")

    model_lower = model_name.lower()

    if uses_openai_compatible_gemini_proxy(model_name):
        return Provider.OPENAI

    # Prefix match
    for prefix, provider in MODEL_PREFIX_MAP.items():
        if model_lower.startswith(prefix):
            return provider

    # o1-* is already handled above, but check just "o1" as well
    if model_lower.startswith("o1"):
        return Provider.O1

    # Base URL heuristic
    base_url = os.environ.get("OPENAI_BASE_URL", "").lower()
    if base_url:
        if "openrouter" in base_url or "openrouter.ai" in base_url:
            return Provider.OPENROUTER
        if "deepseek" in base_url:
            return Provider.DEEPSEEK
        if "dashscope" in base_url or "qwen" in base_url:
            return Provider.QWEN

    return Provider.UNKNOWN


# ── Image utilities ───────────────────────────────────────────────────────────

def resize_and_save_image(img_obs, port: int, size: Tuple[int, int] = (384, 768),
                          quality: int = 70) -> str:
    """
    Resize a screenshot and save it to a temp path.
    Returns the saved file path.
    """
    import os as _os
    work_path = os.environ.get("MOBILE_SAFETY_HOME", "")
    img_cv = cv2.resize(img_obs, dsize=size, interpolation=cv2.INTER_AREA)
    img_pil = Image.fromarray(img_cv)
    img_pil_path = f"{work_path}/logs/tmp_{port}.png"
    img_pil.save(img_pil_path, quality=quality, optimize=True)
    return img_pil_path


# ── Provider-specific client wrappers ─────────────────────────────────────────

class OpenAIClient:
    """Unified OpenAI-compatible client (supports OpenAI, Qwen, DeepSeek, OpenRouter)."""
    def __init__(self, api_key: str = None, base_url: str = None, model_name: str = None,
                 provider: Provider = Provider.OPENAI):
        from openai import OpenAI

        if api_key is None:
            if os.environ.get("THIRD_PARTY_PROXY_API_KEY"):
                api_key = os.environ.get("THIRD_PARTY_PROXY_API_KEY", "")
            elif os.environ.get("AAAAPI_API_KEY"):
                api_key = os.environ.get("AAAAPI_API_KEY", "")
            elif provider in (Provider.DEEPSEEK,):
                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            elif provider in (Provider.QWEN,):
                api_key = os.environ.get("DASHSCOPE_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
            else:
                api_key = os.environ.get("OPENAI_API_KEY", "")

        if base_url is None:
            if os.environ.get("THIRD_PARTY_PROXY_BASE_URL"):
                base_url = normalize_openai_base_url(os.environ.get("THIRD_PARTY_PROXY_BASE_URL"))
            elif provider == Provider.QWEN:
                base_url = os.environ.get(
                    "OPENAI_BASE_URL",
                    "https://dashscope.aliyuncs.com/compatible-mode/v1"
                )
            elif provider == Provider.DEEPSEEK:
                base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            elif provider == Provider.OPENROUTER:
                base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            elif provider == Provider.O1:
                # o1 models use a different endpoint
                base_url = None
            else:
                base_url = os.environ.get("OPENAI_BASE_URL", None)
        base_url = normalize_openai_base_url(base_url)

        default_headers = {
            "X-Stainless-OS": "Windows",
            "X-Stainless-Runtime": "CPython",
            "X-Stainless-Runtime-Version": "3.11"
        }
        raw_auth_header = (
            os.environ.get("OPENAI_RAW_AUTH_HEADER")
            or os.environ.get("THIRD_PARTY_PROXY_AUTH_HEADER")
        )
        if not raw_auth_header and (os.environ.get("THIRD_PARTY_PROXY_BASE_URL") or (base_url and "aaaapi.com" in base_url.lower())):
            raw_auth_header = (
                os.environ.get("THIRD_PARTY_PROXY_API_KEY")
                or os.environ.get("AAAAPI_API_KEY")
                or api_key
            )
        if raw_auth_header:
            default_headers["Authorization"] = raw_auth_header

        self._model_name = model_name
        self._provider = provider

        if provider == Provider.O1:
            # o1 models don't support system messages or many parameters
            self._client = OpenAI(api_key=api_key, default_headers=default_headers)
        elif base_url:
            self._client = OpenAI(api_key=api_key, base_url=base_url,
                                  default_headers=default_headers)
        else:
            self._client = OpenAI(api_key=api_key, default_headers=default_headers)

    def chat(self, *, model: str, messages: list, temperature: float = 0.0,
             max_tokens: int = 2048, top_p: float = 1.0, seed: int = None,
             timeout: float = 120.0, **kwargs):
        """
        Unified chat completion interface.
        Adapts parameters per provider.
        """
        if self._provider == Provider.O1:
            # o1 doesn't support: system (as separate role), temperature, top_p, seed, frequency_penalty, presence_penalty
            # Filter out unsupported params for o1
            o1_messages = []
            for msg in messages:
                clean_msg = {k: v for k, v in msg.items() if k != "role" or v != "system"}
                if clean_msg.get("role") == "system":
                    # Merge system into first user message
                    continue
                o1_messages.append(clean_msg)

            return self._client.chat.completions.create(
                model=model,
                messages=o1_messages,
                timeout=timeout,
            )
        else:
            return self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                seed=seed,
                timeout=timeout,
                **kwargs
            )


class AnthropicClient:
    """Unified Anthropic client for Claude models."""
    def __init__(self, api_key: str = None):
        import anthropic
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = anthropic.Anthropic(api_key=api_key)

    def messages(self, *, model: str, system: str, messages: list,
                 temperature: float = 0.0, max_tokens: int = 2048,
                 top_p: float = 1.0, **kwargs):
        return self._client.messages.create(
            model=model,
            system=system,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs
        )


class GoogleClient:
    """Unified Google Generative AI client for Gemini models."""
    def __init__(self, api_key: str = None, model_name: str = None,
                 config: dict = None, safety_settings: list = None):
        import google.generativeai as genai
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)

        generation_config = {
            "temperature": config.get("temperature", 0.0) if config else 0.0,
            "top_p": config.get("top_p", 1.0) if config else 1.0,
            "max_output_tokens": config.get("max_tokens", 2048) if config else 2048,
        }

        if safety_settings is None and config:
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT",
                 "threshold": config.get("HARM_CATEGORY_HARASSMENT", "BLOCK_NONE")},
                {"category": "HARM_CATEGORY_HATE_SPEECH",
                 "threshold": config.get("HARM_CATEGORY_HATE_SPEECH", "BLOCK_NONE")},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                 "threshold": config.get("HARM_CATEGORY_SEXUALLY_EXPLICIT", "BLOCK_NONE")},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                 "threshold": config.get("HARM_CATEGORY_DANGEROUS_CONTENT", "BLOCK_NONE")},
            ]

        self._model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

    def generate(self, prompt, image=None):
        if image:
            return self._model.generate_content([prompt, image])
        return self._model.generate_content(prompt)


# ── Agent classes ─────────────────────────────────────────────────────────────

class MultiProviderAgent:
    """
    Unified agent that dispatches to the correct provider based on model name.
    Implements the same interface as the original GPTAgent / ClaudeAgent / GeminiAgent.
    """

    def __init__(self, model_name: str = "gpt-4o-2024-05-13", seed: int = 42,
                 port: int = 5554, config: dict = None):
        import os
        import yaml as _yaml
        import re as _re
        from datetime import datetime as _datetime

        self.model_name = model_name
        self.port = port
        self.seed = seed
        self.config = config or {}

        self.context = "I just started the task. I need to plan about what I will do."
        self.time_list = []

        work_path = os.environ.get("MOBILE_SAFETY_HOME", "")
        config_path = f"{work_path}/mobile_safety/agent/model_config.yaml"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                full_config = _yaml.safe_load(f)
            for m in full_config.get("models", []):
                if m["name"] == model_name:
                    self.config = {**self.config, **m.get("settings", {})}
                    break

        self._provider = detect_provider(model_name)
        self._init_client()

    def _init_client(self):
        if self._provider == Provider.ANTHROPIC:
            self._client = AnthropicClient()
        elif self._provider == Provider.GOOGLE:
            self._client = GoogleClient(
                model_name=self.model_name,
                config=self.config,
            )
        else:
            self._client = OpenAIClient(
                api_key=None,
                base_url=None,
                model_name=self.model_name,
                provider=self._provider,
            )

    def get_response(self, timestep=None, system_prompt: str = None,
                     user_prompt: str = None):
        import re as _re
        from datetime import datetime as _datetime

        if system_prompt:
            system_prompt = _re.sub(r"<context>", self.context, system_prompt)
        if user_prompt:
            user_prompt = _re.sub(r"<context>", self.context, user_prompt)

        img_pil_path = self._save_image(timestep)
        start_time = _datetime.now()

        if self._provider == Provider.ANTHROPIC:
            response = self._call_anthropic(system_prompt, user_prompt, img_pil_path)
        elif self._provider == Provider.GOOGLE:
            response = self._call_google(system_prompt, img_pil_path)
        else:
            response = self._call_openai_compatible(system_prompt, user_prompt)

        end_time = _datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        self.time_list.append(elapsed)
        print(f"[{self._provider.value.upper()}] Time elapsed: {elapsed:.2f}s")

        # parse response
        try:
            response_dict = parse_response(response)
            if response_dict["action"] is None:
                print("Error in response")
            if response_dict.get("context", "") != "":
                self.context = response_dict["context"]
        except Exception:
            response_dict = {"action": None, "context": "", "raw_response": str(response)}

        # return used prompt for logging
        log_prompt = ""
        log_prompt += "<system_prompt>\n" + (system_prompt or "") + "</system_prompt>\n\n"
        log_prompt += "<user_prompt>\n" + (user_prompt or "") + "</user_prompt>\n\n"

        return response_dict, log_prompt

    def _call_openai_compatible(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI-compatible API (OpenAI, Qwen, DeepSeek, OpenRouter, o1)."""
        img_pil_path = f"{os.environ.get('MOBILE_SAFETY_HOME', '')}/logs/tmp_{self.port}.png"

        messages = []
        if system_prompt:
            if self._provider == Provider.O1:
                # o1 merges system into user message
                messages.append({"role": "user", "content": f"[System]\n{system_prompt}\n\n[User]\n{user_prompt}"})
            else:
                messages.append({"role": "system", "content": system_prompt})
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encode_image(img_pil_path)}"}
                        },
                    ]
                })
        else:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encode_image(img_pil_path)}"}
                    },
                ]
            })

        try:
            print(f"[API] 正在调用 {self._provider.value.upper()} ({self.model_name})...")
            completion = self._client.chat(
                model=self.model_name,
                messages=messages,
                temperature=self.config.get("temperature", 0.0),
                max_tokens=self.config.get("max_tokens", 2048),
                top_p=self.config.get("top_p", 1.0),
                seed=self.seed,
                timeout=120.0,
            )
            response = completion.choices[0].message.content
            print(f"[API] 响应成功")
            return response
        except Exception as e:
            print(f"[API] 调用失败: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def _call_anthropic(self, system_prompt: str, user_prompt: str, img_pil_path: str) -> str:
        """Call Anthropic Claude API."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": encode_image(img_pil_path),
                        },
                    },
                ],
            }
        ]

        try:
            print(f"[API] 正在调用 ANTHROPIC ({self.model_name})...")
            completion = self._client.messages.create(
                model=self.model_name,
                system=system_prompt or "",
                messages=messages,
                temperature=self.config.get("temperature", 0.0),
                max_tokens=self.config.get("max_tokens", 2048),
                top_p=self.config.get("top_p", 1.0),
            )
            response = completion.content[0].text
            print(f"[API] 响应成功")
            return response
        except Exception as e:
            print(f"[API] 调用失败: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def _call_google(self, system_prompt: str, img_pil_path: str) -> str:
        """Call Google Gemini API."""
        from PIL import Image

        img_obs = None
        if hasattr(self, '_last_timestep') and self._last_timestep:
            img_obs = self._last_timestep.curr_obs.get("pixel")
        if img_obs is None:
            img_obs = self._last_timestep.curr_obs["pixel"]

        img_cv = cv2.resize(img_obs, dsize=(1024, 2048), interpolation=cv2.INTER_AREA)
        img_pil = Image.fromarray(img_cv)

        prompt = ""
        if system_prompt:
            prompt += system_prompt + "\n"
        prompt += "<context>"  # Gemini doesn't use re.sub the same way

        try:
            print(f"[API] 正在调用 GOOGLE ({self.model_name})...")
            response = self._client.generate(prompt=prompt, image=img_pil)
            print(f"[API] 响应成功")
            return response.text
        except Exception as e:
            print(f"[API] 调用失败: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def _save_image(self, timestep=None):
        import os
        work_path = os.environ.get("MOBILE_SAFETY_HOME", "")
        img_pil_path = f"{work_path}/logs/tmp_{self.port}.png"

        if timestep is not None:
            self._last_timestep = timestep
            img_obs = timestep.curr_obs["pixel"]
            img_cv = cv2.resize(img_obs, dsize=(384, 768), interpolation=cv2.INTER_AREA)
            img_pil = Image.fromarray(img_cv)
            img_pil.save(img_pil_path, quality=70, optimize=True)

            file_size = os.path.getsize(img_pil_path)
            print(f"[DEBUG] 图片已保存: {img_pil_path}, 大小: {file_size/1024:.1f}KB")
        return img_pil_path

    def save_image(self, timestep=None):
        """Public alias for _save_image (backward compatibility)."""
        return self._save_image(timestep)

    @property
    def provider(self) -> Provider:
        return self._provider


# ── Factory function ───────────────────────────────────────────────────────────

def create_agent(model_name: str = "gpt-4o-2024-05-13", seed: int = 42,
                 port: int = 5554, config: dict = None):
    """
    Factory function to create the appropriate agent based on model name.

    Supports:
      - OpenAI models (gpt-4o, gpt-4-turbo, etc.)
      - Anthropic Claude models (claude-3-5-sonnet, etc.)
      - Google Gemini models (gemini-1.5-pro, gemini-2.0-flash, etc.)
      - Qwen/VL models (qwen-vl-max-latest, etc.)
      - DeepSeek models (deepseek-chat, deepseek-coder, etc.)
      - OpenRouter models (any model routed through OpenRouter)
      - o1 models (o1-preview, o1-mini, o1-pro, etc.)

    Example:
        agent = create_agent(model_name="claude-3-5-sonnet-20240620")
        agent = create_agent(model_name="gemini-2.0-flash")
        agent = create_agent(model_name="deepseek-chat")
        agent = create_agent(model_name="openrouter/anthropic/claude-3.5-sonnet")
    """
    provider = detect_provider(model_name)
    print(f"[Agent Factory] Model: {model_name} -> Provider: {provider.value}")

    return MultiProviderAgent(
        model_name=model_name,
        seed=seed,
        port=port,
        config=config,
    )


# ── Legacy compatibility: re-export original agents ─────────────────────────────

def GPTAgent(model_name="gpt-4o-2024-05-13", seed=42, port=5554):
    """Backward-compatible factory: creates GPT/Qwen/OpenAI-compatible agent."""
    return create_agent(model_name=model_name, seed=seed, port=port)


def ClaudeAgent(model_name="claude-3-5-sonnet-20240620", seed=42, port=5554):
    """Backward-compatible factory: creates Claude agent."""
    return create_agent(model_name=model_name, seed=seed, port=port)


def GeminiAgent(model_name="gemini-1.5-pro-001", seed=42, port=5554, safety_settings=None):
    """Backward-compatible factory: creates Gemini agent."""
    return create_agent(model_name=model_name, seed=seed, port=port)


def QwenAgent(model_name="qwen-vl-max-latest", seed=42, port=5554):
    """Backward-compatible factory: creates Qwen/VL agent."""
    return create_agent(model_name=model_name, seed=seed, port=port)


def DeepSeekAgent(model_name="deepseek-chat", seed=42, port=5554):
    """Backward-compatible factory: creates DeepSeek agent."""
    return create_agent(model_name=model_name, seed=seed, port=port)


def OpenRouterAgent(model_name="anthropic/claude-3.5-sonnet", seed=42, port=5554):
    """Backward-compatible factory: creates OpenRouter agent (proxies to various models)."""
    return create_agent(model_name=model_name, seed=seed, port=port)


def O1Agent(model_name="o1-preview", seed=42, port=5554):
    """Backward-compatible factory: creates o1 agent (OpenAI o1 family)."""
    return create_agent(model_name=model_name, seed=seed, port=port)
