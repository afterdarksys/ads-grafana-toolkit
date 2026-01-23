# Slack Notifier

Shared Slack notification library for auto-infrastructure alerts.

## Usage in Python

```python
from shared.slack_notifier.notify import notify_slack_sync

# Send notification
success = notify_slack_sync(
    message="🚀 Auto-scale complete: Added 2 instances (+$100/month)",
    severity="SCALE_UP",
    webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
    title="Auto-Scale Event"
)
```

## Usage in n8n

Set environment variable:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Use in n8n HTTP Request node:
```json
{
  "url": "={{$env.SLACK_WEBHOOK_URL}}",
  "method": "POST",
  "body": {
    "attachments": [{
      "color": "#9b59b6",
      "blocks": [...]
    }]
  }
}
```

## Severity Levels

- `CRITICAL` - Red, 🚨 (system failures)
- `WARNING` - Orange, ⚠️ (degraded performance)
- `INFO` - Blue, ℹ️ (informational)
- `OK` - Green, ✅ (healthy status)
- `SCALE_UP` - Purple, 🚀 (capacity increased)
- `SCALE_DOWN` - Light blue, 📉 (capacity reduced)

## Environment Variables

- `SLACK_WEBHOOK_URL` - Incoming webhook URL from Slack
