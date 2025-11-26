# RSS → Webhook Notifier

Reads configured RSS/Atom feeds and posts new items to webhooks via **Apprise**, supporting 100+ notification services. Persists state to avoid duplicates across restarts and logs to `/data/app.log`.

## Features

- **Multi-service Support**: Discord, Slack, Telegram, Email, Mattermost, Rocket.Chat, and 90+ more via Apprise
- **No Raw Webhooks**: Uses Apprise service URLs for better security and flexibility
- **Stateful**: Tracks seen entries to avoid duplicates
- **Configurable**: Per-feed and global settings for messages, delays, and update intervals
- **Rate Limiting**: Built-in delays and max items per cycle to prevent throttling

## Supported Services

Apprise supports notifications to:
- **Chat**: Discord, Slack, Telegram, Mattermost, Rocket.Chat, Teams, Matrix
- **Email**: SMTP, SendGrid, Mailgun, SparkPost
- **Monitoring**: Gotify, Ntfy, PushBullet, PushDeer
- **Other**: Webhook, IRC, XMPP, and many more

See [Apprise documentation](https://github.com/caronc/apprise) for complete list of supported services.

## Quick start
```bash
# 1) Clone the project folder and cd into it
# 2) Copy example-config.yaml to config.yaml and put your Apprise service URLs into config.yaml
# 3) Build & run
docker build -t rss-to-webhook .
docker run -d \
--name rssbot \
-e TZ=Europe/Amsterdam \
-v $(pwd)/data:/data \
rss-to-webhook
```

Rebuilding the image is not needed for config.yaml changes, restarting the container should be sufficient.

## Configuration Examples

### Discord via Apprise
```yaml
webhooks:
  - url: "discord://<webhook_id>/<webhook_token>"
    feeds:
      - url: "https://example.com/feed.xml"
        name: "Example Feed"
```

### Slack
```yaml
webhooks:
  - url: "slack://token_a/token_b/token_c"
    feeds:
      - url: "https://example.com/feed.xml"
```

### Telegram
```yaml
webhooks:
  - url: "tgram://<bot_token>/<chat_id>"
    feeds:
      - url: "https://example.com/feed.xml"
```

### Email (SMTP)
```yaml
webhooks:
  - url: "mailtos://user:password@smtp.gmail.com/?to=recipient@example.com"
    feeds:
      - url: "https://example.com/feed.xml"
```

See the `example-config.yaml` file for more configuration options. 