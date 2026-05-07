# Copyright (c) Meta Platforms, Inc. and affiliates.
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, Literal


Environment = str
AttackType = Literal["content_injection", "adinject"]


@dataclass(frozen=True)
class BenignTask:
    intent: str
    eval: dict[str, Any]


@dataclass(frozen=True)
class AttackSpec:
    attack_type: AttackType
    environment: Environment
    action_url: str
    instruction: str
    eval: dict[str, Any]
    parameters: dict[str, Any]
    setup_fn: str = ""
    cleanup_fn: str = ""
    injection_format: str = "raw"
    runtime_hook: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class UnifiedSample:
    id: str
    environment: Environment
    benign_task: BenignTask
    attack: AttackSpec
    policies: Optional[list[dict[str, Any]]] = None


def load_unified_benchmark(path: str) -> list[UnifiedSample]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError("Unified benchmark must be a JSON list.")

    samples: list[UnifiedSample] = []
    for obj in raw:
        if not isinstance(obj, dict):
            raise ValueError("Each unified sample must be a JSON object.")

        benign = obj.get("benign_task", {})
        attack = obj.get("attack", {})

        sample = UnifiedSample(
            id=str(obj["id"]),
            environment=obj["environment"],
            benign_task=BenignTask(
                intent=str(benign["intent"]),
                eval=benign.get("eval", {}),
            ),
            attack=AttackSpec(
                attack_type=attack.get("attack_type", "content_injection"),
                environment=attack.get("environment", obj["environment"]),
                action_url=str(attack["action_url"]),
                instruction=str(attack["instruction"]),
                eval=attack.get("eval", {}),
                parameters=attack.get("parameters", {}),
                setup_fn=str(attack.get("setup_fn", "")),
                cleanup_fn=str(attack.get("cleanup_fn", "")),
                injection_format=str(attack.get("injection_format", "raw")),
                runtime_hook=attack.get("runtime_hook"),
            ),
            policies=obj.get("policies"),
        )
        samples.append(sample)

    return samples


def sample_to_wasp_experiment_config(sample: UnifiedSample) -> dict[str, Any]:
    """Convert a unified sample into WASP's existing experiment_config.raw.json structure."""
    return {
        "prompt_injections_setup_config": [
            {
                "free_form_name": sample.id,
                "environment": sample.attack.environment,
                "setup_fn": sample.attack.setup_fn,
                "parameters": sample.attack.parameters,
                "action_url": sample.attack.action_url,
                "instruction": sample.attack.instruction,
                "exfil": "exfil" in (sample.attack.eval or {}).get("eval_types", []),
                "eval": sample.attack.eval,
                "cleanup_fn": sample.attack.cleanup_fn,
                "notes": "",
            }
        ]
    }

