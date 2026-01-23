#!/usr/bin/env python3
"""
Shared Slack Notification Library for Auto-Infrastructure
Adapted from ads-ai-staff infrastructure monitoring

Usage:
    from shared.slack_notifier import notify_slack

    await notify_slack(
        message="Auto-scale event triggered",
        severity="INFO",
        webhook_url=SLACK_WEBHOOK_URL
    )
"""

import httpx
from datetime import datetime
from typing import Optional


async def notify_slack(
    message: str,
    severity: str = "INFO",
    webhook_url: Optional[str] = None,
    title: Optional[str] = None,
    timeout: int = 30
) -> bool:
    """
    Send notification to Slack.

    Args:
        message: The message to send
        severity: One of: CRITICAL, WARNING, INFO, OK
        webhook_url: Slack incoming webhook URL
        title: Optional custom title (defaults to severity-based)
        timeout: Request timeout in seconds

    Returns:
        True if notification was sent successfully
    """
    if not webhook_url or webhook_url.startswith("$"):
        return False

    # Color mapping
    color = {
        "CRITICAL": "#ff0000",  # Red
        "WARNING": "#ffaa00",   # Orange
        "INFO": "#0088ff",      # Blue
        "OK": "#00ff00",        # Green
        "SCALE_UP": "#9b59b6",  # Purple
        "SCALE_DOWN": "#3498db" # Light blue
    }.get(severity, "#808080")

    # Icon mapping
    icon = {
        "CRITICAL": "🚨",
        "WARNING": "⚠️",
        "INFO": "ℹ️",
        "OK": "✅",
        "SCALE_UP": "🚀",
        "SCALE_DOWN": "📉"
    }.get(severity, "📢")

    # Title
    if not title:
        title = f"{icon} [{severity}] Infrastructure Alert"

    payload = {
        "attachments": [{
            "color": color,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message[:2900]  # Slack has 3000 char limit
                    }
                },
                {
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }]
                }
            ]
        }]
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(webhook_url, json=payload)
            return response.status_code == 200
        except Exception:
            return False


def notify_slack_sync(
    message: str,
    severity: str = "INFO",
    webhook_url: Optional[str] = None,
    title: Optional[str] = None,
    timeout: int = 30
) -> bool:
    """Synchronous version of notify_slack for non-async contexts."""
    import httpx

    if not webhook_url or webhook_url.startswith("$"):
        return False

    color = {
        "CRITICAL": "#ff0000",
        "WARNING": "#ffaa00",
        "INFO": "#0088ff",
        "OK": "#00ff00",
        "SCALE_UP": "#9b59b6",
        "SCALE_DOWN": "#3498db"
    }.get(severity, "#808080")

    icon = {
        "CRITICAL": "🚨",
        "WARNING": "⚠️",
        "INFO": "ℹ️",
        "OK": "✅",
        "SCALE_UP": "🚀",
        "SCALE_DOWN": "📉"
    }.get(severity, "📢")

    if not title:
        title = f"{icon} [{severity}] Infrastructure Alert"

    payload = {
        "attachments": [{
            "color": color,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message[:2900]
                    }
                },
                {
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }]
                }
            ]
        }]
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(webhook_url, json=payload)
            return response.status_code == 200
    except Exception:
        return False
