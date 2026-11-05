"""Queue ownership, transport errors, multipart progress and uncertain delivery."""
import asyncio
import json
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reliable_delivery_regression import TransactionalDelivery
from telegram_notification_dispatcher_smoke import make_notification
from app.repositories.telegram_notification import TelegramNotificationRepository
from app.models.telegram_notification import TelegramNotificationOutbox
from app.services.telegram_dispatcher import TelegramNotificationDispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError, TelegramRetryAfter
from aiogram.methods import SendMessage


class FakeBot:
    def __init__(self, failures=None):
        self.calls = []
        self.failures = failures or {}

    def __getattr__(self, method):
        async def call(**kwargs):
            self.calls.append((method, kwargs))
            exc = self.failures.get(len(self.calls))
            if exc:
                raise exc
            result = SimpleNamespace(chat=SimpleNamespace(id=kwargs["chat_id"]), message_id=len(self.calls)+100)
            return [result] if method == "send_media_group" else result
        return call


class QueueReliability(TransactionalDelivery):
    async def notification(self, *, text="message", media=None):
        async with self.sessions() as s:
            n = make_notification(job_id=1, recipient=1001, sequence=1, now=self.now)
            n.payload_json = json.dumps({"text": text, "parse_mode": "HTML"})
            s.add(n)
            await s.commit()
            return n.id

    async def row(self, id=1):
        async with self.sessions() as s:
            return await s.get(TelegramNotificationOutbox, id)

    async def test_atomic_claim_rejects_second_worker_with_cached_snapshot(self):
        id = await self.notification()
        async with self.sessions() as s1, self.sessions() as s2:
            r1, r2 = TelegramNotificationRepository(s1), TelegramNotificationRepository(s2)
            first, second = await r1.get_by_id(id), await r2.get_by_id(id)
            # Force old read-then-write implementation to see concurrent snapshots.
            with patch.object(r1, "get_by_id", AsyncMock(return_value=first)), patch.object(r2, "get_by_id", AsyncMock(return_value=second)):
                self.assertIsNotNone(await r1.claim(notification_id=id, now=self.now, max_attempts=5))
                await s1.commit()
                self.assertIsNone(await r2.claim(notification_id=id, now=self.now, max_attempts=5))

    async def test_future_retry_cannot_be_claimed_early(self):
        id = await self.notification()
        async with self.sessions() as s:
            n = await s.get(TelegramNotificationOutbox, id)
            n.next_attempt_at = self.now + timedelta(hours=1)
            await s.commit()
            self.assertIsNone(await TelegramNotificationRepository(s).claim(notification_id=id, now=self.now, max_attempts=5))

    async def test_crash_after_send_before_db_write_is_not_automatically_resent(self):
        id = await self.notification()
        bot = FakeBot()
        dispatcher = TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot, stale_sending_seconds=0)
        with patch.object(TelegramNotificationRepository, "mark_sent", AsyncMock(side_effect=RuntimeError("database write failed"))):
            try:
                await dispatcher.dispatch_due()
            except RuntimeError:
                pass
        await dispatcher.dispatch_due()
        self.assertEqual(len(bot.calls), 1, "restart resent an ambiguously delivered message")
        self.assertEqual((await self.row(id)).delivery_status, "uncertain")

    async def test_permanent_errors_do_not_retry_and_other_recipients_continue(self):
        id = await self.notification()
        async with self.sessions() as s:
            s.add(make_notification(job_id=1, recipient=1002, sequence=2, now=self.now))
            await s.commit()
        bot = FakeBot({1: TelegramForbiddenError(method=SendMessage(chat_id=1,text="x"), message="blocked")})
        dispatcher = TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot, retry_base_seconds=0)
        await dispatcher.dispatch_due()
        await dispatcher.dispatch_due()
        self.assertEqual((await self.row(id)).delivery_status, "failed")
        self.assertEqual(len(bot.calls), 2)

    async def test_rate_limit_respects_retry_after(self):
        id = await self.notification()
        bot = FakeBot({1: TelegramRetryAfter(method=SendMessage(chat_id=1,text="x"), message="limit", retry_after=120)})
        dispatcher = TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot, retry_base_seconds=1)
        await dispatcher.dispatch_due()
        row = await self.row(id)
        self.assertEqual(row.delivery_status, "retry")
        self.assertGreaterEqual((row.next_attempt_at - row.last_attempt_at).total_seconds(), 120)

    async def test_long_html_unicode_message_is_split_with_valid_entities(self):
        await self.notification(text="<b>" + "😀 &amp; "*1000 + "</b>")
        bot = FakeBot()
        await TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot).dispatch_due()
        self.assertGreater(len(bot.calls), 1, "oversized text not split")
        from html import unescape
        import re
        for method, kwargs in bot.calls:
            text = kwargs["text"]
            plain = unescape(re.sub("<[^>]*>", "", text))
            self.assertLessEqual(len(plain.encode("utf-16-le"))//2, 4096)
            self.assertEqual(text.count("<b>"), text.count("</b>"))


if __name__ == "__main__":
    unittest.main()
