import os
import re
import time
import yaml
import feedparser
import logging
from apprise import Apprise
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, timezone


class RSSDiscordBot:
    def __init__(self, config_path="config.yaml", data_path="/data"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config(config_path)
        self.feeds = self._flatten_feeds()
        self._setup_logging()
        self.logger.info("RSS Discord Bot initialized")

    def _load_config(self, config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def _setup_logging(self):
        log_path = self.data_path / "app.log"
        log_format = "%(asctime)s [%(levelname)s] %(message)s"

        self.logger = logging.getLogger("RSSDiscordBot")
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(console_handler)

        # Rotating file handler
        file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
        file_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(file_handler)

    def _sanitize_filename(self, name: str) -> str:
        """Replace unsafe characters for filenames with underscores"""
        return re.sub(r"[^A-Za-z0-9._-]", "_", name)

    def _seen_file_path(self, feed_url: str) -> Path:
        safe_name = self._sanitize_filename(feed_url)
        return self.data_path / f"seen_{safe_name}.txt"

    def _flatten_feeds(self):
        """Flatten webhooks + feeds from config into a unified list with overrides applied"""
        flattened = []

        global_defaults = {
            "username": self.config.get("username", "RSS Bot"),
            "avatar_url": self.config.get("avatar_url", ""),  # globale avatar
            "interval": self.config.get("interval", 300),
            "message_template": self.config.get(
                "message_template", "**[{source}]** {title}\n{link}"
            ),
            "disable_preview": self.config.get("disable_preview", False),
            "delay": self.config.get("delay", 0),
            "max_per_cycle": self.config.get("max_per_cycle", 0),
            "max_age_days": self.config.get("max_age_days", 0),  # nieuw
        }

        for webhook in self.config.get("webhooks", []):
            webhook_defaults = global_defaults.copy()
            webhook_defaults.update(
                {k: webhook[k] for k in webhook if k in webhook_defaults}
            )
            webhook_url = webhook["url"]

            for feed in webhook.get("feeds", []):
                feed_config = webhook_defaults.copy()
                feed_config.update(feed)
                feed_config["webhook_url"] = webhook_url
                flattened.append(feed_config)

        return flattened

    def _load_seen(self, feed_url: str):
        seen_file = self._seen_file_path(feed_url)
        if seen_file.exists():
            with open(seen_file, "r") as f:
                return set(line.strip() for line in f)
        return set()

    def _save_seen(self, feed_url: str, seen_ids):
        seen_file = self._seen_file_path(feed_url)
        with open(seen_file, "w") as f:
            for entry_id in seen_ids:
                f.write(f"{entry_id}\n")

    def _format_message(self, feed, entry):
        template = feed.get("message_template", "**[{source}]** {title}\n{link}")
        link = entry.get("link", "")
        if feed.get("disable_preview", False):
            link = f"<{link}>"

        return template.format(
            source=feed.get("name", feed.get("url")),
            title=entry.get("title", "No title"),
            link=link,
        )

    def _post_to_discord(self, webhook_url, content, username, avatar_url):
        try:
            # Reject raw Discord webhook HTTP URLs. Require Apprise service URLs
            # (e.g. discord://{id}/{token}) so callers explicitly configure the
            # desired Apprise target.
            if (
                webhook_url.startswith("https://discord.com/api/webhooks/")
                or "discordapp.com/api/webhooks" in webhook_url
            ):
                self.logger.error(
                    "Raw Discord webhook URLs are not supported. "
                    "Please use an Apprise service URL like: discord://<id>/<token>"
                )
                return

            # Use Apprise to send the notification. The `webhook_url` must be
            # an Apprise-compatible service URL (e.g. discord://..., slack://...)
            a = Apprise()
            a.add(webhook_url)

            ok = a.notify(title=username or "RSS Bot", body=content)
            if not ok:
                self.logger.error(f"Apprise notification failed for {webhook_url}")
        except Exception as e:
            self.logger.error(f"Error posting via Apprise: {e}")

    def run(self):
        last_run = {feed["url"]: 0 for feed in self.feeds}

        while True:
            now = time.time()

            for feed in self.feeds:
                url = feed["url"]
                interval = int(feed.get("interval", 300))
                delay = int(feed.get("delay", 0))
                max_per_cycle = int(feed.get("max_per_cycle", 0))
                max_age_days = int(feed.get("max_age_days", 0))

                if now - last_run[url] < interval:
                    continue

                self.logger.info(f"Fetching {url}")
                last_run[url] = now

                try:
                    parsed = feedparser.parse(url)
                except Exception as e:
                    self.logger.error(f"Failed to parse {url}: {e}")
                    continue

                seen_ids = self._load_seen(url)
                new_seen = set(seen_ids)

                posted_count = 0

                # calculate cutoff
                cutoff_time = None
                if max_age_days > 0:
                    cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)

                for entry in reversed(parsed.entries):
                    if max_per_cycle and posted_count >= max_per_cycle:
                        break

                    entry_id = entry.get("id") or entry.get("link")
                    if not entry_id or entry_id in seen_ids:
                        continue

                    # age check
                    if cutoff_time:
                        published = None
                        if "published_parsed" in entry and entry.published_parsed:
                            published = datetime.fromtimestamp(
                                time.mktime(entry.published_parsed), tz=timezone.utc
                            )
                        elif "updated_parsed" in entry and entry.updated_parsed:
                            published = datetime.fromtimestamp(
                                time.mktime(entry.updated_parsed), tz=timezone.utc
                            )

                        if published and published < cutoff_time:
                            continue  # te old = skip post

                    content = self._format_message(feed, entry)
                    self._post_to_discord(
                        feed["webhook_url"],
                        content,
                        feed.get("username", "RSS Bot"),
                        feed.get("avatar_url", ""),
                    )

                    new_seen.add(entry_id)
                    posted_count += 1
                    self.logger.info(
                        f"Posted new entry from {url}: {entry.get('title')}"
                    )

                    if delay > 0:
                        time.sleep(delay)  # buildin delay per post

                self._save_seen(url, new_seen)

            time.sleep(10)


if __name__ == "__main__":
    bot = RSSDiscordBot()
    bot.run()
