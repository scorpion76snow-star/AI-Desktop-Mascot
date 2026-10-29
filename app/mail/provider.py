# -*- coding: utf-8 -*-
"""Mail provider interfaces.  Gmail/Outlook are intentionally not implemented."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class MailMessage:
    provider: str
    external_id: str
    sender: str
    subject: str
    body: str = ""
    snippet: str = ""
    received_at: Optional[datetime] = None
    raw: dict = field(default_factory=dict)


@dataclass
class MailDraft:
    provider: str
    to: str
    subject: str
    body: str
    draft_id: Optional[str] = None


class MailProviderError(RuntimeError):
    pass


class MailProvider:
    name = "base"
    account_id = "base"

    def connect(self, config: dict) -> None:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError

    def list_messages(self, since=None, limit: int = 50) -> List[MailMessage]:
        raise NotImplementedError

    def get_message(self, message_id: str) -> MailMessage:
        raise NotImplementedError

    def create_draft(self, draft: MailDraft) -> str:
        raise NotImplementedError

    def send_draft(self, draft_id: str) -> None:
        raise NotImplementedError

    def mark_read(self, message_id: str) -> None:
        raise NotImplementedError


class GmailProvider(MailProvider):
    """Fill in with google-api-python-client + OAuth.  Read-only by default."""

    name = "gmail"

    def connect(self, config: dict) -> None:
        raise MailProviderError("Gmail provider is not configured yet.")

    def disconnect(self) -> None:
        return None

    def list_messages(self, since=None, limit: int = 50) -> List[MailMessage]:
        raise MailProviderError("Gmail provider is not configured yet.")

    def get_message(self, message_id: str) -> MailMessage:
        raise MailProviderError("Gmail provider is not configured yet.")

    def create_draft(self, draft: MailDraft) -> str:
        raise MailProviderError("Gmail send is disabled until you approve a draft.")

    def send_draft(self, draft_id: str) -> None:
        raise MailProviderError("Gmail send is disabled until you approve a draft.")

    def mark_read(self, message_id: str) -> None:
        return None


class OutlookProvider(MailProvider):
    """Fill in with Microsoft Graph / MSAL.  Read-only by default."""

    name = "outlook"

    def connect(self, config: dict) -> None:
        raise MailProviderError("Outlook provider is not configured yet.")

    def disconnect(self) -> None:
        return None

    def list_messages(self, since=None, limit: int = 50) -> List[MailMessage]:
        raise MailProviderError("Outlook provider is not configured yet.")

    def get_message(self, message_id: str) -> MailMessage:
        raise MailProviderError("Outlook provider is not configured yet.")

    def create_draft(self, draft: MailDraft) -> str:
        raise MailProviderError("Outlook send is disabled until you approve a draft.")

    def send_draft(self, draft_id: str) -> None:
        raise MailProviderError("Outlook send is disabled until you approve a draft.")

    def mark_read(self, message_id: str) -> None:
        return None


def build_provider(name: str, account_id: str = None) -> MailProvider:
    if name == "gmail":
        p = GmailProvider()
    elif name == "outlook":
        p = OutlookProvider()
    else:
        raise MailProviderError(f"unknown provider: {name}")
    p.account_id = account_id or name
    return p
