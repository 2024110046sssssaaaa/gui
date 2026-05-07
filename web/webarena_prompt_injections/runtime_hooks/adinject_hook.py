# Copyright (c) Meta Platforms, Inc. and affiliates.
import json
import os

import click
import requests


def _load_ad_content(ad_path: str) -> dict:
    with open(ad_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _default_ad_config() -> dict:
    ad_server = os.environ.get("AD_SERVER", "localhost")
    ad_server_port = os.environ.get("AD_SERVER_PORT", "61234")
    ad_path = os.environ.get("AD_PATH", "ad.json")
    ad_id = os.environ.get("AD_ID", "01")
    ad_style = os.environ.get("AD_STYLE", "popup")
    ad_scale = float(os.environ.get("AD_SCALE", 1.0))
    ad_enhance = os.environ.get("AD_ENHANCE", None)

    ad_content = _load_ad_content(ad_path)
    cfg = {
        "link": f"http://{ad_server}:{ad_server_port}/close_ad",
        "site": "",
        "title": ad_content.get("title", ""),
        "subtitle": "",
        "content": ad_content.get("content", ""),
        "btntext": ad_content.get("button_text", ""),
        "imgalt": "",
        "imgpath": "",
        "server": ad_server,
        "port": ad_server_port,
        "style": ad_style,
        "scale": ad_scale,
        "ad_id": ad_id,
    }
    if ad_enhance is not None:
        cfg["enhance"] = "true"
    return cfg


def start_injection(tag: str, *, extra_params: dict | None = None) -> None:
    cfg = _default_ad_config()
    if extra_params:
        cfg.update(extra_params)

    ad_server = cfg["server"]
    ad_server_port = cfg["port"]
    ad_id = cfg["ad_id"]

    url = f"http://{ad_server}:{ad_server_port}/start_cdp_injection/{tag}/{ad_id}"
    resp = requests.get(url, params=cfg, timeout=30)
    resp.raise_for_status()


def stop_injection() -> None:
    cfg = _default_ad_config()
    url = f"http://{cfg['server']}:{cfg['port']}/close_ad?finished=true"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()


@click.group()
def cli():
    pass


@cli.command("start")
@click.option("--tag", type=str, required=True)
def cli_start(tag: str):
    start_injection(tag)
    click.echo("ok")


@cli.command("stop")
def cli_stop():
    stop_injection()
    click.echo("ok")


if __name__ == "__main__":
    cli()

