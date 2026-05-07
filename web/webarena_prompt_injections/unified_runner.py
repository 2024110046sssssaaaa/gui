# Copyright (c) Meta Platforms, Inc. and affiliates.
import json
import os
import subprocess
from datetime import datetime

import click

from environment_editors.gitlab_editor import GitlabEditor
from environment_editors.reddit_editor import RedditEditor
from prompt_injection_core import WebArenaPromptInjector
from attack_backends.base import BackendContext, get_backend
from unified_schema import load_unified_benchmark, sample_to_wasp_experiment_config


def _safe_dirname(s: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in ("-", "_", ".")) else "_" for ch in s)


@click.command()
@click.option("--unified-config", type=str, required=True, help="Path to unified benchmark JSON list.")
@click.option("--output-root", type=str, default="/tmp/wasp-unified", show_default=True)
@click.option("--model", type=str, default="gpt-4o", show_default=True,
              help="backbone LLM: gpt-4o, gpt-4o-mini, claude-35, claude-37, qwen")
@click.option(
    "--system-prompt",
    type=str,
    default="configs/system_prompts/wa_p_som_cot_id_actree_3s.json",
    show_default=True,
)
@click.option("--output-format", type=str, default="webarena", show_default=True)
@click.option("--gitlab-domain", default="none", show_default=True)
@click.option("--reddit-domain", default="none", show_default=True)
@click.option("--skip-environment", is_flag=True, default=False)
@click.option("--run-agents", is_flag=True, default=False, help="Also execute generated run_agent.sh scripts.")
def main(
    unified_config: str,
    output_root: str,
    model: str,
    system_prompt: str,
    output_format: str,
    gitlab_domain: str,
    reddit_domain: str,
    skip_environment: bool,
    run_agents: bool,
):
    if gitlab_domain == "none":
        gitlab_domain = os.environ.get("GITLAB")
    if reddit_domain == "none":
        reddit_domain = os.environ.get("REDDIT")

    samples = load_unified_benchmark(unified_config)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = os.path.join(output_root, ts)
    os.makedirs(out_root, exist_ok=True)

    system_prompt_abs = os.path.join(os.getcwd(), system_prompt)

    editor_list = [GitlabEditor(gitlab_domain), RedditEditor(reddit_domain)]

    for i, sample in enumerate(samples):
        sample_dir = os.path.join(out_root, f"{i:04d}_{_safe_dirname(sample.id)}")
        os.makedirs(sample_dir, exist_ok=True)

        experiment_config = sample_to_wasp_experiment_config(sample)
        exp_path = os.path.join(sample_dir, "experiment_config.json")
        with open(exp_path, "w", encoding="utf-8") as f:
            json.dump(experiment_config, f, indent=2)

        injector = WebArenaPromptInjector(
            editor_list, experiment_config["prompt_injections_setup_config"]
        )
        backend = get_backend(sample)
        ctx = BackendContext(
            injector=injector,
            output_dir=sample_dir + ("/" if not sample_dir.endswith("/") else ""),
            output_format=output_format,
            model=model,
            system_prompt_abs=system_prompt_abs,
            skip_environment=skip_environment,
        )
        agent_script, instantiated_cfg = backend.prepare(sample, ctx=ctx)

        click.echo(f"[{sample.id}] agent_script={agent_script}")
        click.echo(f"[{sample.id}] instantiated_cfg={instantiated_cfg}")

        if run_agents:
            subprocess.run(["bash", agent_script], check=True)


if __name__ == "__main__":
    main()

