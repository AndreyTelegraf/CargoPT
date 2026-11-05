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

    async def test_two_dispatchers_deliver_same_notification_once(self):
        await self.notification()
        bot = FakeBot()
        workers = [TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot) for _ in range(2)]
        await asyncio.gather(*(worker.dispatch_due() for worker in workers))
        self.assertEqual(len(bot.calls), 1)

    async def test_temporary_failure_is_bounded(self):
        await self.notification()
        error = TelegramNetworkError(method=SendMessage(chat_id=1, text="x"), message="network")
        bot = FakeBot({i: error for i in range(1, 10)})
        worker = TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot, max_attempts=3, retry_base_seconds=0)
        for _ in range(5):
            await worker.dispatch_due()
        self.assertEqual((await self.row()).delivery_status, "failed")
        self.assertEqual(len(bot.calls), 3)

    async def test_checkpoint_failure_after_success_quarantines_without_replay(self):
        await self.notification()
        bot = FakeBot()
        worker = TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot, stale_sending_seconds=0)
        original = TelegramNotificationRepository.checkpoint
        async def checkpoint(repo, **kwargs):
            if json.loads(kwargs["payload_json"])["_delivery"]["completed"]:
                raise RuntimeError("write interrupted")
            return await original(repo, **kwargs)
        with patch.object(TelegramNotificationRepository, "checkpoint", checkpoint):
            await worker.dispatch_due()
        await worker.dispatch_due()
        self.assertEqual(len(bot.calls), 1)
        self.assertEqual((await self.row()).delivery_status, "uncertain")

    async def test_media_limits_and_anchor_message(self):
        from app.services.telegram_delivery_plan import build_delivery_plan, split_text
        for kinds in ([], ["photo"], ["video"], ["photo", "video"], ["photo"]*11):
            for text in ("<b>short &amp; 😀</b>", "<b>"+"😀 &amp; "*1200+"</b>"):
                snapshot = dict(notification_type="carrier_offer", job_id=1, offer_id=1,
                    payload={"text": text, "locale": "pt-BR"},
                    media=[{"media_type": kind, "telegram_file_id": f"file-{i}"} for i, kind in enumerate(kinds)])
                plan = build_delivery_plan(snapshot)
                self.assertTrue(plan[-1]["kwargs"].get("reply_markup"))
                media_count = sum(len(step["kwargs"]["media"]) if step["method"] == "send_media_group" else int(step["method"] in {"send_photo", "send_video"}) for step in plan)
                self.assertEqual(media_count, len(kinds))
                for step in plan:
                    kwargs = step["kwargs"]
                    if "caption" in kwargs:
                        self.assertEqual(len(split_text(kwargs["caption"], parse_mode="HTML", limit=1024)), 1)
                    if "text" in kwargs:
                        self.assertEqual(len(split_text(kwargs["text"], parse_mode="HTML")), 1)

    async def test_partial_video_then_text_retry_does_not_repeat_video(self):
        from app.models.job import JobMedia, JobOffer
        id = await self.notification(text="<b>"+"длинный текст "*200+"</b>")
        async with self.sessions() as s:
            n = await s.get(TelegramNotificationOutbox, id)
            n.notification_type, n.offer_id = "carrier_offer", 1
            (await s.get(JobOffer, 1)).expires_at = self.now + timedelta(hours=1)
            s.add(JobMedia(job_id=1, media_type="video", telegram_file_id="video-file", created_at=self.now))
            await s.commit()
        bot = FakeBot({2: TelegramNetworkError(method=SendMessage(chat_id=1,text="x"), message="network")})
        worker = TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot, retry_base_seconds=0)
        await worker.dispatch_due()
        self.assertEqual((await self.row()).delivery_status, "retry")
        await TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot, retry_base_seconds=0).dispatch_due()
        self.assertEqual([name for name, _ in bot.calls], ["send_video", "send_message", "send_message"])
        async with self.sessions() as s:
            offer = await s.get(JobOffer, 1)
            self.assertEqual(offer.carrier_message_id, 103)
        self.assertEqual((await self.row()).delivery_status, "sent")

    async def test_delayed_offer_for_past_date_is_not_sent(self):
        from app.models.job import Job
        id = await self.notification()
        async with self.sessions() as s:
            n = await s.get(TelegramNotificationOutbox, id)
            n.notification_type, n.offer_id = "carrier_offer", 1
            (await s.get(Job, 1)).requested_date = self.now - timedelta(days=1)
            await s.commit()
        bot = FakeBot()
        await TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot).dispatch_due()
        self.assertEqual(len(bot.calls), 0, "delayed queue sent an obsolete offer")
        self.assertEqual((await self.row()).delivery_status, "failed")

    async def test_invalid_file_id_is_terminal(self):
        await self.notification()
        bot = FakeBot({1: TelegramBadRequest(method=SendMessage(chat_id=1,text="x"), message="wrong file identifier")})
        worker = TelegramNotificationDispatcher(session_maker=self.sessions, bot=bot)
        await worker.dispatch_due()
        await worker.dispatch_due()
        self.assertEqual(len(bot.calls), 1)
        self.assertEqual((await self.row()).delivery_status, "failed")


if __name__ == "__main__":
    unittest.main()
