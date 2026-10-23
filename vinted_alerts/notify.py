"""Alert channels: console, Telegram bot, Discord webhook."""

from __future__ import annotations

import logging

import requests

from .deals import Deal

log = logging.getLogger(__name__)


def format_deal(watch_name: str, deal: Deal) -> str:
    item = deal.item
    lines = [
        f"🔥 [{watch_name}] {item.title}",
        f"💶 {deal.price:.2f} {item.currency}"
        + (f" (articolo {item.price:.2f})" if item.total_price != item.price else ""),
        "✅ " + "; ".join(deal.reasons),
    ]
    details = " · ".join(x for x in (item.brand, item.size, item.condition) if x)
    if details:
        lines.append(details)
    lines.append(item.url)
    return "\n".join(lines)


class ConsoleNotifier:
    def send(self, watch_name: str, deal: Deal) -> None:
        print("\n" + format_deal(watch_name, deal) + "\n", flush=True)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str | int):
        self.api = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id

    def send(self, watch_name: str, deal: Deal) -> None:
        text = format_deal(watch_name, deal)
        if deal.item.photo_url:
            resp = requests.post(f"{self.api}/sendPhoto", timeout=15, data={
                "chat_id": self.chat_id, "photo": deal.item.photo_url, "caption": text[:1024]})
            if resp.ok:
                return
        resp = requests.post(f"{self.api}/sendMessage", timeout=15, data={
            "chat_id": self.chat_id, "text": text})
        if not resp.ok:
            log.error("Telegram: invio fallito (HTTP %s) %s", resp.status_code, resp.text[:200])


class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, watch_name: str, deal: Deal) -> None:
        embed = {
            "title": deal.item.title[:256],
            "url": deal.item.url,
            "description": format_deal(watch_name, deal)[:4000],
        }
        if deal.item.photo_url:
            embed["thumbnail"] = {"url": deal.item.photo_url}
        resp = requests.post(self.webhook_url, json={"embeds": [embed]}, timeout=15)
        if not resp.ok:
            log.error("Discord: invio fallito (HTTP %s) %s", resp.status_code, resp.text[:200])


def build_notifiers(telegram: dict | None, discord: dict | None) -> list:
    notifiers: list = [ConsoleNotifier()]
    if telegram and telegram.get("bot_token") and telegram.get("chat_id"):
        notifiers.append(TelegramNotifier(telegram["bot_token"], telegram["chat_id"]))
    if discord and discord.get("webhook_url"):
        notifiers.append(DiscordNotifier(discord["webhook_url"]))
    return notifiers
