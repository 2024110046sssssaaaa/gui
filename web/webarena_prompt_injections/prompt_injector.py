# Copyright (c) Meta Platforms, Inc. and affiliates.
import json
import os

import click

from constants import OutputFormat
from environment_editors.gitlab_editor import GitlabEditor
from environment_editors.reddit_editor import RedditEditor
from prompt_injection_core import WebArenaPromptInjector
from utils import load_prompt_injection_config


@click.command()
@click.option(
    "--config",
    type=str,
    default="configs/experiment_config.raw.json",
    help="Where to find the config for prompt injections",
)
@click.option(
    "--gitlab-domain",
    default="none",
    show_default=True,
    help="GitLab domain URL (e.g., http://example.com:port)",
)
@click.option(
    "--reddit-domain",
    default="none",
    show_default=True,
    help="Reddit domain URL (e.g., http://example.com:port)",
)
@click.option(
    "--model",
    type=click.Choice(
        ["gpt-4o", "gpt-4o-mini", "claude-35", "claude-37", "qwen"], case_sensitive=False
    ),
    default="gpt-4o",
    help="backbone LLM. Available options: gpt-4o, gpt-4o-mini, claude-35, claude-37, qwen",
)
@click.option(
    "--system_prompt",
    type=str,
    default="configs/system_prompts/wa_p_som_cot_id_actree_3s.json",
    help="system_prompt for the backbone LLM. Default = VWA's SOM system prompt for GPT scaffolding",
)
@click.option(
    "--user_goal_idx",
    type=int,
    default=0,
    help="which benign user goal to set (default=0)",
)
@click.option(
    "--injection_format",
    type=str,
    default="generic_plain_text",
    help="prompt injection format, currently available: "
    "goal_hijacking_url_injection, goal_hijacking_plain_text, generic_url_injection, generic_plain_text (default)",
)
@click.option(
    "--output-dir",
    type=str,
    default="/tmp",
    help="Folder to store the output configs and commands to run the agent",
)
@click.option(
    "--output-format",
    type=str,
    default="webarena",
    help="Agentic scaffolding to use. Options: webrena (default), gpt_web_tools, claude.",
)
@click.option(
    "--skip-environment",
    is_flag=True,
    default=False,
    help="Whether to do a dry run and skip injecting into the environment (for testing purposes). Default is False.",
)
def main(
    config,
    gitlab_domain,
    reddit_domain,
    model,
    system_prompt,
    user_goal_idx,
    injection_format,
    output_dir,
    output_format,
    skip_environment,
):

    if gitlab_domain == "none":  # try to get it from env var
        gitlab_domain = os.environ.get("GITLAB")
    if reddit_domain == "none":
        reddit_domain = os.environ.get("REDDIT")

    experiment_config = load_prompt_injection_config(config)

    system_prompt = os.path.join(os.getcwd(), system_prompt)
    if output_format == "gpt_web_tools":
        print(
            f"No custom system_prompt support for {output_format}, setting it to empty."
        )
        system_prompt = ""
    elif "claude" in model.lower():
        output_format = "claude"
        with open(system_prompt, "r") as claude_agent_config_file:
            claude_agent_configs = json.load(claude_agent_config_file)
            model = claude_agent_configs["model"]
            system_prompt = claude_agent_configs["system_prompt"]

    gitlab_editor = GitlabEditor(gitlab_domain)
    reddit_editor = RedditEditor(reddit_domain)
    editor_list = [gitlab_editor, reddit_editor]

    web_arena_prompt_injector = WebArenaPromptInjector(
        editor_list, experiment_config["prompt_injections_setup_config"]
    )

    path_to_agent_script, path_to_instantiated_prompt_injection_config = (
        web_arena_prompt_injector.inject_in_environment(
            output_dir=output_dir,
            output_format=output_format,
            injection_format=injection_format,
            skip_environment=skip_environment,
            system_prompt=system_prompt,
            user_goal_idx=user_goal_idx,
            model=model,
        )
    )

    print(f"The agent script was written out to: {path_to_agent_script}")
    print(
        f"The prompt injection config was written out to: {path_to_instantiated_prompt_injection_config}"
    )


if __name__ == "__main__":
    main()
