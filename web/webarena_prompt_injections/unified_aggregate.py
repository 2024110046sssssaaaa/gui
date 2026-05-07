# Copyright (c) Meta Platforms, Inc. and affiliates.
import json
import os
import subprocess
from pathlib import Path

import click


def _is_sample_dir(p: Path) -> bool:
    return (p / "agent_logs").exists() and (p / "webarena_tasks").exists()


def _run_eval(final_step_py: str, *, log_folder: str, task_folder: str, fmt: str) -> dict:
    # evaluator_final_step.py writes to /tmp/run_{user,attacker}_utility.json
    subprocess.run(
        ["python", final_step_py, "--log-folder", log_folder, "--task-folder", task_folder, "--format", fmt],
        check=True,
    )
    attacker_path = Path("/tmp/run_attacker_utility.json")
    user_path = Path("/tmp/run_user_utility.json")
    if attacker_path.exists():
        return json.loads(attacker_path.read_text(encoding="utf-8"))
    if user_path.exists():
        return json.loads(user_path.read_text(encoding="utf-8"))
    return {"total_scores": 0.0, "cnt_tasks": 0.0}


@click.command()
@click.option("--run-dir", type=str, required=True, help="Timestamped output dir produced by unified_runner.")
@click.option("--format", "fmt", type=str, default="webarena", show_default=True)
def main(run_dir: str, fmt: str):
    run_path = Path(run_dir)
    if not run_path.exists():
        raise click.ClickException(f"run-dir does not exist: {run_dir}")

    final_step_py = str((Path(__file__).resolve().parent.parent / "visualwebarena" / "evaluator_final_step.py").resolve())

    all_summaries = []
    for child in sorted(run_path.iterdir()):
        if not child.is_dir() or not _is_sample_dir(child):
            continue

        log_folder = str((child / "agent_logs").resolve()) + "/"
        user_task_folder = str((child / "webarena_tasks").resolve()) + "/"
        attacker_task_folder = str((child / "webarena_tasks_attacker").resolve()) + "/"

        attacker_res = _run_eval(final_step_py, log_folder=log_folder, task_folder=attacker_task_folder, fmt=fmt)
        user_res = _run_eval(final_step_py, log_folder=log_folder, task_folder=user_task_folder, fmt=fmt)

        summary = {
            "sample_dir": str(child),
            "attacker_utility": attacker_res,
            "user_utility": user_res,
        }
        (child / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        all_summaries.append(summary)

    (run_path / "aggregate.json").write_text(json.dumps(all_summaries, indent=2), encoding="utf-8")
    click.echo(f"Aggregated {len(all_summaries)} samples into {run_path/'aggregate.json'}")


if __name__ == "__main__":
    main()

