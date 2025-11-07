# RSS → Discord Webhook Bot


Reads configured RSS/Atom feeds and posts new items to a Discord channel via webhook. Persists state to avoid duplicates across restarts and logs to `/data/app.log`.


## Quick start
```bash
# 1) Clone the project folder and cd into it
# 2) Copy example-config.yaml to config.yaml and put your webhook and feeds into config.yaml
# 3) Build & run
docker build -t rss-to-discord .
docker run -d \
--name rssbot \
-e TZ=Europe/Amsterdam \
-v $(pwd)/data:/data \
rss-to-discord

```
Rebuilding the image is not needed for config.yaml changes, restarting the container should sufficient. 