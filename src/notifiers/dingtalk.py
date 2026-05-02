from __future__ import annotations

import httpx


def send(webhook_url: str, title: str, body: str, mention_all: bool = False) -> None:
    """向钉钉自定义机器人发送 Markdown 消息。"""
    text = f"### {title}\n\n{body}"
    if mention_all:
        text += "\n\n@所有人"

    payload: dict = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": text},
    }
    if mention_all:
        payload["at"] = {"isAtAll": True}

    resp = httpx.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("errcode", 0) != 0:
        raise RuntimeError(f"钉钉返回错误: {data}")
