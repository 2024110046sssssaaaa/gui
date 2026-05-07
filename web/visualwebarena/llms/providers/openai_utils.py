# Copyright (c) Meta Platforms, Inc. and affiliates.
"""Tools to generate from OpenAI prompts.
Adopted from https://github.com/zeno-ml/zeno-build/"""

import asyncio
import logging
import os
import random
import time
from typing import Any

import aiolimiter
import requests
from openai import AsyncAzureOpenAI, AzureOpenAI
from openai import AsyncOpenAI, OpenAI


if "AZURE_API_ENDPOINT" in os.environ and "AZURE_API_KEY" in os.environ:
    api_version = "2024-10-21" if "AZURE_API_VERSION" not in os.environ else os.environ["AZURE_API_VERSION"]
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_API_ENDPOINT"],
        api_key=os.environ["AZURE_API_KEY"],
        api_version=api_version,
    )

    aclient = AsyncAzureOpenAI(
        azure_endpoint=os.environ["AZURE_API_ENDPOINT"],
        api_key=os.environ["AZURE_API_KEY"],
        api_version=api_version,
    )
else:
    if "OPENAI_API_BASE" not in os.environ:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        aclient = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    else:
        # Used for running vllm models or compatible APIs like DASHSCOPE
        api_key = os.environ.get("OPENAI_API_KEY", "EMPTY")
        base_url = os.environ.get("OPENAI_API_BASE", "")
        if "dashscope" in base_url.lower() or "aaaapi" in base_url.lower():
            api_key = os.environ["OPENAI_API_KEY"]  # Use real key for compatible APIs
            print(f"Using compatible API with base: {base_url}")
        else:
            print("WARNING: Using OPENAI_API_KEY=EMPTY")
        client = OpenAI(
            api_key=api_key, base_url=base_url
        )
        aclient = AsyncOpenAI(
            api_key=api_key, base_url=base_url
        )


from tqdm.asyncio import tqdm_asyncio


def retry_with_exponential_backoff(  # type: ignore
    func,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 3,
    errors: tuple[Any] = (
        requests.exceptions.ReadTimeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ),
):
    """Retry a function with exponential backoff."""

    def wrapper(*args, **kwargs):  # type: ignore
        # Initialize variables
        num_retries = 0
        delay = initial_delay

        # Loop until a successful response or max_retries is hit or an exception is raised
        while True:
            try:

                return func(*args, **kwargs)

            # Retry on specified errors
            except errors as e:
                # Increment retries
                num_retries += 1
                print("Error while calling OpenAI API: ", e)
                # Check if max retries has been reached
                if num_retries > max_retries:
                    raise Exception(
                        f"Maximum number of retries ({max_retries}) exceeded."
                    )

                # Increment the delay
                delay *= exponential_base * (1 + jitter * random.random())

                # Sleep for the delay
                time.sleep(delay)

            # Raise exceptions for any errors not specified
            except Exception as e:
                raise e

    return wrapper


async def _throttled_openai_completion_acreate(
    engine: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    limiter: aiolimiter.AsyncLimiter,
) -> dict[str, Any]:
    async with limiter:
        for _ in range(3):
            try:
                return await aclient.completions.create(
                    engine=engine,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                )
            except openai.RateLimitError:
                logging.warning(
                    "OpenAI API rate limit exceeded. Sleeping for 10 seconds."
                )
                await asyncio.sleep(10)
            except openai.APIError as e:
                logging.warning(f"OpenAI API error: {e}")
                break
        return {"choices": [{"message": {"content": ""}}]}


async def agenerate_from_openai_completion(
    prompts: list[str],
    engine: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    requests_per_minute: int = 300,
) -> list[str]:
    """Generate from OpenAI Completion API.

    Args:
        prompts: list of prompts
        temperature: Temperature to use.
        max_tokens: Maximum number of tokens to generate.
        top_p: Top p to use.
        context_length: Length of context to use.
        requests_per_minute: Number of requests per minute to allow.

    Returns:
        List of generated responses.
    """
    # Check if using DashScope compatible API - skip Azure check
    is_dashscope = "dashscope" in os.environ.get("OPENAI_API_BASE", "").lower()
    
    # Check if using Azure - both vars must be set together
    using_azure = "AZURE_API_ENDPOINT" in os.environ and "AZURE_API_KEY" in os.environ
    
    if using_azure:
        pass  # Azure client already initialized at module level
    elif is_dashscope or "OPENAI_API_BASE" in os.environ:
        # Using compatible API - no additional checks needed
        pass
    elif "OPENAI_API_KEY" not in os.environ:
        raise ValueError("OPENAI_API_KEY environment variable must be set when using OpenAI API.")

    limiter = aiolimiter.AsyncLimiter(requests_per_minute)
    async_responses = [
        _throttled_openai_completion_acreate(
            engine=engine,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            limiter=limiter,
        )
        for prompt in prompts
    ]
    responses = await tqdm_asyncio.gather(*async_responses)
    return [x["choices"][0]["text"] for x in responses]


@retry_with_exponential_backoff
def generate_from_openai_completion(
    prompt: str,
    engine: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    stop_token: str | None = None,
) -> str:
    # Check if using DashScope compatible API - skip Azure check
    is_dashscope = "dashscope" in os.environ.get("OPENAI_API_BASE", "").lower()
    
    # Check if using Azure - both vars must be set together
    using_azure = "AZURE_API_ENDPOINT" in os.environ and "AZURE_API_KEY" in os.environ
    
    if using_azure:
        pass  # Azure client already initialized at module level
    elif is_dashscope or "OPENAI_API_BASE" in os.environ:
        # Using compatible API - no additional checks needed
        pass
    elif "OPENAI_API_KEY" not in os.environ:
        raise ValueError("OPENAI_API_KEY environment variable must be set when using OpenAI API.")

    response = client.completions.create(
        prompt=prompt,
        engine=engine,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        stop=[stop_token],
    )
    answer: str = response["choices"][0]["text"]
    return answer


async def _throttled_openai_chat_completion_acreate(
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    top_p: float,
    limiter: aiolimiter.AsyncLimiter,
) -> dict[str, Any]:
    async with limiter:
        for _ in range(3):
            try:
                return await aclient.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                )
            except openai.RateLimitError:
                logging.warning(
                    "OpenAI API rate limit exceeded. Sleeping for 10 seconds."
                )
                await asyncio.sleep(10)
            except asyncio.exceptions.TimeoutError:
                logging.warning("OpenAI API timeout. Sleeping for 10 seconds.")
                await asyncio.sleep(10)
            except openai.APIError as e:
                logging.warning(f"OpenAI API error: {e}")
                break
        return {"choices": [{"message": {"content": ""}}]}


async def agenerate_from_openai_chat_completion(
    messages_list: list[list[dict[str, str]]],
    engine: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    requests_per_minute: int = 300,
) -> list[str]:
    """Generate from OpenAI Chat Completion API.

    Args:
        messages_list: list of message list
        temperature: Temperature to use.
        max_tokens: Maximum number of tokens to generate.
        top_p: Top p to use.
        context_length: Length of context to use.
        requests_per_minute: Number of requests per minute to allow.

    Returns:
        List of generated responses.
    """
    # Check if using DashScope compatible API - skip Azure check
    is_dashscope = "dashscope" in os.environ.get("OPENAI_API_BASE", "").lower()
    
    # Check if using Azure - both vars must be set together
    using_azure = "AZURE_API_ENDPOINT" in os.environ and "AZURE_API_KEY" in os.environ
    
    if using_azure:
        pass  # Azure client already initialized at module level
    elif is_dashscope or "OPENAI_API_BASE" in os.environ:
        # Using compatible API - no additional checks needed
        pass
    elif "OPENAI_API_KEY" not in os.environ:
        raise ValueError("OPENAI_API_KEY environment variable must be set when using OpenAI API.")

    limiter = aiolimiter.AsyncLimiter(requests_per_minute)
    async_responses = [
        _throttled_openai_chat_completion_acreate(
            model=engine,
            messages=message,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            limiter=limiter,
        )
        for message in messages_list
    ]
    responses = await tqdm_asyncio.gather(*async_responses)
    return [x["choices"][0]["message"]["content"] for x in responses]


@retry_with_exponential_backoff
def generate_from_openai_chat_completion(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    stop_token: str | None = None,
) -> str:
    # Check if using DashScope compatible API - skip Azure check
    is_dashscope = "dashscope" in os.environ.get("OPENAI_API_BASE", "").lower()
    
    # Check if using Azure - both vars must be set together
    using_azure = "AZURE_API_ENDPOINT" in os.environ and "AZURE_API_KEY" in os.environ
    
    if using_azure:
        pass  # Azure client already initialized at module level
    elif is_dashscope or "OPENAI_API_BASE" in os.environ:
        # Using compatible API - no additional checks needed
        pass
    elif "OPENAI_API_KEY" not in os.environ:
        raise ValueError("OPENAI_API_KEY environment variable must be set when using OpenAI API.")
    
    # Debug logging for troubleshooting API issues
    print(f"[DEBUG] Calling API: model={model}, base_url={os.environ.get('OPENAI_API_BASE', 'default')}")

    base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com").rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    api_url = base + "/v1/chat/completions"
    api_key = os.environ.get("OPENAI_API_KEY", "")

    # Check if using aaaapi.com - it doesn't need "Bearer" prefix
    is_aaaapi = "aaaapi" in os.environ.get("OPENAI_API_BASE", "").lower()
    
    # Debug: print full API key info
    print(f"[DEBUG] is_aaaapi={is_aaaapi}, api_key length={len(api_key)}, api_key[:10]={api_key[:10] if api_key else 'EMPTY'}")
    
    # payload for compatible APIs like aaaapi.com
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
    }
    
    # aaaapi.com uses direct API key without "Bearer" prefix
    if is_aaaapi:
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }
    else:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    resp = requests.post(api_url, json=payload, headers=headers, timeout=300)
    if resp.status_code != 200:
        print(f"[DEBUG] HTTP Error Response: {resp.status_code} - {resp.text[:500]}")
    resp.raise_for_status()
    data = resp.json()

    # Debug logging for response
    print(f"[DEBUG] Response received: choices={data.get('choices')}, model={data.get('model')}")

    choices = data.get("choices", [])
    if not choices or choices[0].get("message") is None:
        raise RuntimeError(f"API returned no choices. Response: {data}")

    answer: str = choices[0]["message"]["content"]
    return answer


@retry_with_exponential_backoff
# debug only
def fake_generate_from_openai_chat_completion(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    stop_token: str | None = None,
) -> str:
    # Check if using DashScope compatible API - skip Azure check
    is_dashscope = "dashscope" in os.environ.get("OPENAI_API_BASE", "").lower()
    
    # Check if using Azure - both vars must be set together
    using_azure = "AZURE_API_ENDPOINT" in os.environ and "AZURE_API_KEY" in os.environ
    
    if using_azure:
        pass  # Azure client already initialized at module level
    elif is_dashscope or "OPENAI_API_BASE" in os.environ:
        # Using compatible API - no additional checks needed
        pass
    elif "OPENAI_API_KEY" not in os.environ:
        raise ValueError("OPENAI_API_KEY environment variable must be set when using OpenAI API.")

    answer = "Let's think step-by-step. This page shows a list of links and buttons. There is a search box with the label 'Search query'. I will click on the search box to type the query. So the action I will perform is \"click [60]\"."
    return answer