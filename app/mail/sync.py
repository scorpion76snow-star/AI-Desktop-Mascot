# -*- coding: utf-8 -*-
"""Poll configured mail provider, dedupe, store, and notify."""

import re
from datetime import datetime, timedelta

from app.mail.provider import MailProvider


def has_chinese(text):
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def notification_text(sender, subject, lang="zh", include_subject=True):
    if lang == "zh":
        base = f"老板，收到一封来自 {sender or '未知发件人'} 的邮件"
        return base + (f"，主题是 {subject}。" if include_subject and subject else "。")
    base = f"Boss, you have a new email from {sender or 'an unknown sender'}"
    return base + (f", subject: {subject}." if include_subject and subject else ".")


class MailSync:
    def __init__(self, storage, provider: MailProvider = None, settings=None, providers=None):
        self.storage = storage
        if providers is not None:
            self.providers = list(providers)
        else:
            self.providers = [provider] if provider is not None else []
        self.settings = settings
        self.last_poll = None

    def poll(self, limit=20):
        """Return list of new MailMessage rows across all accounts. Never raises."""
        since = self.last_poll
        self.last_poll = datetime.now()
        out = []
        for provider in list(self.providers):
            account = getattr(provider, "account_id", None) or getattr(provider, "name", "mail")
            try:
                messages = provider.list_messages(since=since, limit=limit)
            except Exception:
                continue
            for msg in messages:
                row, is_new = self.storage.add_message(
                    provider=account,
                    external_id=msg.external_id,
                    sender=msg.sender,
                    subject=msg.subject,
                    snippet=msg.snippet or (msg.body or "")[:120],
                    received_at=(msg.received_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
                )
                if is_new and row:
                    out.append(row)
        return out

    def mark_notified(self, message_id):
        self.storage.mark_message_notified(message_id)


def unread_cutoff(seconds):
    return datetime.now() - timedelta(seconds=max(0, seconds))
