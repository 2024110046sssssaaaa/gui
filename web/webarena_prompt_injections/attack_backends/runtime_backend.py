# Copyright (c) Meta Platforms, Inc. and affiliates.
from __future__ import annotations

import os

from .base import BackendContext
from unified_schema import UnifiedSample


class RuntimeInjectionBackend:
    """Backend for attacks applied at runtime (e.g., AdInject).

    For now this backend reuses the same content-injection task creation to
    produce a runnable `run_agent.sh`, but leaves runtime hooks to be wired
    in by the caller (next todo).
    """

    name = "runtime_injection"

    def prepare(self, sample: UnifiedSample, *, ctx: BackendContext) -> tuple[str, str]:
        # Create tasks and runner script the same way; the difference is that
        # caller will wrap the runner with runtime hook calls.
        agent_script, instantiated_cfg = ctx.injector.inject_in_environment(
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
        runtime_hook = sample.attack.runtime_hook or {}
        if sample.attack.attack_type == "adinject" or runtime_hook.get("type") == "adinject":
            tag = runtime_hook.get("tag") or sample.id
            self._wrap_script_with_adinject(agent_script, tag=tag)
        return agent_script, instantiated_cfg

    def _wrap_script_with_adinject(self, agent_script_path: str, *, tag: str) -> None:
        hook_abs = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "runtime_hooks", "adinject_hook.py")
        )
        with open(agent_script_path, "r", encoding="utf-8") as f:
            original = f.read()

        wrapper = "\n".join(
            [
                "#!/bin/bash",
                "set -e",
                "",
                f'python "{hook_abs}" start --tag "{tag}"',
                "cleanup_adinject() {",
                "  set +e",
                f'  python "{hook_abs}" stop',
                "}",
                "trap cleanup_adinject EXIT",
                "",
                "# ---- original agent script ----",
                original,
                "",
            ]
        )
        with open(agent_script_path, "w", encoding="utf-8") as f:
            f.write(wrapper)

