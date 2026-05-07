# Copyright (c) Meta Platforms, Inc. and affiliates.
from __future__ import annotations

from .base import BackendContext
from unified_schema import UnifiedSample


class ContentInjectionBackend:
    name = "content_injection"

    def prepare(self, sample: UnifiedSample, *, ctx: BackendContext) -> tuple[str, str]:
        return ctx.injector.inject_in_environment(
            injection_format=sample.attack.injection_format,
            skip_environment=ctx.skip_environment,
            output_dir=ctx.output_dir,
            output_format=ctx.output_format,
            system_prompt=ctx.system_prompt_abs,
            user_goal_idx=0,
            model=ctx.model,
            benign_task_override={
                "intent": sample.benign_task.intent,
                "eval": sample.benign_task.eval,
            },
        )

