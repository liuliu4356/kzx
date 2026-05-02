from __future__ import annotations

import httpx


def send(webhook_url: str, title: str, body: str) -> None:
    """向飞书自定义机器人发送富文本消息。"""
    # 将 body 按行拆分为段落列表
    paragraphs = [
        [{"tag": "text", "text": line}]
        for line in body.splitlines()
        if line.strip()
    ]

    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": paragraphs or [[{"tag": "text", "text": body}]],
                }
            }
        },
    }

    resp = httpx.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("StatusCode", 0) != 0 or data.get("code", 0) != 0:
        raise RuntimeError(f"飞书返回错误: {data}")
