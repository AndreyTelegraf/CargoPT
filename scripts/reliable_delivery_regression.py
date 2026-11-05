"""Transactional delivery regressions, temporary SQLite and a fake Telegram."""
import asyncio
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
import app.models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base
from app.models.job import Job, JobOffer, JobAddress
from app.models.telegram_notification import TelegramNotificationOutbox
from app.repositories.job import JobRepository
from app.repositories.carrier import CarrierRepository
from app.services.offer_notification import send_job_offers_to_carriers
from app.services.offer_expiry import process_expired_pending_offers
from app.services.assignment_timeout import process_stale_assignment_confirmations
from manual_offer_redispatch_smoke import make_carrier, make_vehicle


class NoNetwork:
    def __getattr__(self, name):
        async def fail(**kwargs):
            raise AssertionError(f"Telegram {name} called before business commit")
        return fail


class TransactionalDelivery(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.tmp.name}/test.db")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.now = datetime.now(UTC)
        async with self.sessions() as s:
            s.add_all([make_carrier(i, now=self.now) for i in (1, 2)])
            s.add_all([make_vehicle(i, now=self.now) for i in (1, 2)])
            self.job = Job(id=1, tracking_token="test", status="offered", requested_date=self.now + timedelta(days=1),
                client_telegram_user_id=9001, needs_assembly=False, needs_packing=False,
                needs_tail_lift=False, needs_crane=False, needs_mobile_lift=False,
                created_at=self.now, updated_at=self.now)
            s.add(self.job)
            s.add(JobAddress(job_id=1, kind="pickup", raw_text="Lisboa", latitude=38.72, longitude=-9.14, created_at=self.now))
            s.add(JobOffer(id=1, job_id=1, carrier_id=1, vehicle_id=1, status="pending", offered_at=self.now-timedelta(hours=2),
                expires_at=self.now-timedelta(hours=1), created_at=self.now, updated_at=self.now))
            await s.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        self.tmp.cleanup()

    async def test_offer_enqueue_is_transactional_and_deduplicated(self):
        async with self.sessions() as s:
            jobs, carriers = JobRepository(s), CarrierRepository(s)
            job, offer = await jobs.get_job_by_id(1), await jobs.get_offer_by_id(1)
            for _ in range(2):
                await send_job_offers_to_carriers(bot=NoNetwork(), job=job, offers=[offer], job_repository=jobs, carrier_repository=carriers)
            await s.commit()
        async with self.sessions() as s:
            rows = list((await s.scalars(select(TelegramNotificationOutbox))).all())
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].delivery_status, "pending")

    async def test_enqueue_without_previous_write_obeys_outer_rollback(self):
        async with self.sessions() as s:
            jobs, carriers = JobRepository(s), CarrierRepository(s)
            job, offer = await s.get(Job, 1), await s.get(JobOffer, 1)
            await send_job_offers_to_carriers(bot=NoNetwork(), job=job, offers=[offer], job_repository=jobs, carrier_repository=carriers)
            await s.rollback()
        async with self.sessions() as s:
            self.assertEqual(len(list(await s.scalars(select(TelegramNotificationOutbox)))), 0,
                "SQLite SAVEPOINT released before a real outer BEGIN committed the notification")

    async def test_expiry_commits_and_repeated_cycle_creates_no_duplicates(self):
        async with self.sessions() as s:
            self.assertEqual(await process_expired_pending_offers(bot=NoNetwork(), session=s), 1)
            await s.commit()
        async with self.sessions() as s:
            self.assertEqual(await process_expired_pending_offers(bot=NoNetwork(), session=s), 0)
            offers = list((await s.scalars(select(JobOffer))).all())
            self.assertEqual([o.status for o in offers], ["expired", "pending"])
            self.assertEqual(len(list(await s.scalars(select(TelegramNotificationOutbox)))), 1)

    async def test_timeout_state_does_not_depend_on_telegram(self):
        async with self.sessions() as s:
            j, o = await s.get(Job, 1), await s.get(JobOffer, 1)
            j.status = "assigned_pending_confirmation"
            j.assigned_at = self.now - timedelta(hours=25)
            o.status = "accepted"
            await s.commit()
        async with self.sessions() as s:
            self.assertEqual(await process_stale_assignment_confirmations(bot=NoNetwork(), session=s), 1)
            await s.commit()
        async with self.sessions() as s:
            self.assertEqual((await s.get(JobOffer, 1)).status, "cancelled")
            self.assertNotEqual((await s.get(Job, 1)).status, "assigned_pending_confirmation")
            self.assertEqual(await process_stale_assignment_confirmations(bot=NoNetwork(), session=s), 0)
            self.assertGreaterEqual(len(list(await s.scalars(select(TelegramNotificationOutbox)))), 3)

    async def test_client_accepted_selection_and_assignment_messages_are_queued(self):
        from app.bot.handlers.job_offer_response import send_client_offer_selection_message
        from app.services.assignment_notifications import send_assignment_confirmation_requests, send_assignment_final_notifications
        from app.services.telegram_notifications import notification_service_for
        async with self.sessions() as s:
            job, offer = await s.get(Job, 1), await s.get(JobOffer, 1)
            offer.status = "accepted"
            jobs, carriers = JobRepository(s), CarrierRepository(s)
            for _ in range(2):
                await send_client_offer_selection_message(bot=NoNetwork(), job=job, job_repository=jobs, carrier_repository=carriers)
            await send_assignment_confirmation_requests(bot=NoNetwork(), job=job, carrier_telegram_user_id=1001,
                notification_service=notification_service_for(jobs, carriers), offer_id=1)
            job.status = "assigned"
            await send_assignment_final_notifications(bot=NoNetwork(), job=job, accepted_offer=offer, carrier_repository=carriers)
            await s.commit()
        async with self.sessions() as s:
            self.assertEqual((await s.get(JobOffer, 1)).status, "accepted")
            self.assertEqual((await s.get(Job, 1)).status, "assigned")
            rows = list(await s.scalars(select(TelegramNotificationOutbox)))
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(r.delivery_status == "pending" for r in rows))

    async def test_past_date_expiry_and_assignment_timeout_do_not_create_offers(self):
        for action in ("expiry", "timeout"):
            async with self.sessions() as s:
                job, offer = await s.get(Job, 1), await s.get(JobOffer, 1)
                job.requested_date = self.now - timedelta(days=365)
                job.status = "offered" if action == "expiry" else "assigned_pending_confirmation"
                job.assigned_at = self.now - timedelta(hours=25)
                offer.status = "pending" if action == "expiry" else "accepted"
                await s.commit()
            async with self.sessions() as s:
                process = process_expired_pending_offers if action == "expiry" else process_stale_assignment_confirmations
                await process(bot=NoNetwork(), session=s)
                await s.commit()
                self.assertEqual(len(list(await s.scalars(select(JobOffer)))), 1)
                self.assertEqual((await s.get(Job, 1)).status, "manual_review_required")

    async def test_past_date_submission_is_committed_for_manual_review(self):
        from app.services.request_submission import RequestSubmissionService
        from app.services.telegram_notifications import notification_service_for
        async with self.sessions() as s:
            job = await s.get(Job, 1)
            job.requested_date = self.now - timedelta(days=1)
            await s.commit()
            jobs, carriers = JobRepository(s), CarrierRepository(s)
            result = await RequestSubmissionService(job_repository=jobs, carrier_repository=carriers,
                bot=NoNetwork(), telegram_notification_service=notification_service_for(jobs, carriers)
            ).submit_existing_job(job_id=1, comment="expired submission")
            self.assertEqual(result.offers_count, 0)
        async with self.sessions() as s:
            self.assertEqual((await s.get(Job, 1)).status, "manual_review_required")
            self.assertEqual(len(list(await s.scalars(select(JobOffer)))), 1)

    async def test_past_date_admin_retry_and_single_send_are_rejected(self):
        from app.bot.handlers import dispatcher_jobs_admin as handler
        async with self.sessions() as s:
            job = await s.get(Job, 1)
            job.requested_date = self.now - timedelta(days=1)
            await s.commit()
        for action in ("retry", "send:2"):
            callback = SimpleNamespace(data=f"job:1:{action}", from_user=SimpleNamespace(id=336224597),
                answer=AsyncMock(), bot=NoNetwork(), message=None)
            with patch.object(handler, "async_session_maker", self.sessions):
                await handler.dispatcher_job_admin_action(callback)
            self.assertIn("Дата перевозки прошла", callback.answer.await_args.args[0])
        async with self.sessions() as s:
            self.assertEqual(len(list(await s.scalars(select(JobOffer)))), 1)
            self.assertEqual((await s.get(Job, 1)).status, "offered")

    async def test_past_date_decline_commits_without_redispatch(self):
        from app.bot.handlers import job_offer_response as handler
        async with self.sessions() as s:
            job, offer = await s.get(Job, 1), await s.get(JobOffer, 1)
            job.requested_date = self.now - timedelta(days=1)
            offer.expires_at = self.now + timedelta(hours=1)
            await s.commit()
        from app.domain.job_decline_reason import DECLINE_REASONS
        reason = DECLINE_REASONS[0].code
        callback = SimpleNamespace(data=f"offer_decline_reason:1:{reason}", from_user=SimpleNamespace(id=1001, language_code="ru"),
            answer=AsyncMock(), bot=NoNetwork(), message=None)
        # Match the actual callback prefix accepted by the decline handler.
        with patch.object(handler, "async_session_maker", self.sessions):
            await handler.handle_offer_decline_reason(callback)
        async with self.sessions() as s:
            self.assertEqual((await s.get(JobOffer, 1)).status, "declined")
            self.assertEqual(len(list(await s.scalars(select(JobOffer)))), 1)
            self.assertEqual((await s.get(Job, 1)).status, "manual_review_required")


if __name__ == "__main__":
    unittest.main()
