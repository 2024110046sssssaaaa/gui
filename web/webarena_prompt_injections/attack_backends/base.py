# Copyright (c) Meta Platforms, Inc. and affiliates.
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from prompt_injection_core import WebArenaPromptInjector
from unified_schema import UnifiedSample


@dataclass(frozen=True)
class BackendContext:
    injector: WebArenaPromptInjector
    output_dir: str
    output_format: str
    model: str
    system_prompt_abs: str
    skip_environment: bool


class AttackBackend(Protocol):
    name: str

    def prepare(self, sample: UnifiedSample, *, ctx: BackendContext) -> tuple[str, str]:
        """Prepare environment/tasks and return (agent_script, instantiated_cfg_path)."""


def get_backend(sample: UnifiedSample):
    from .content_backend import ContentInjectionBackend
    from .runtime_backend import RuntimeInjectionBackend

    if sample.attack.attack_type == "content_injection":
        return ContentInjectionBackend()
    if sample.attack.attack_type == "adinject":
        return RuntimeInjectionBackend()
    raise ValueError(f"Unknown attack_type: {sample.attack.attack_type}")

