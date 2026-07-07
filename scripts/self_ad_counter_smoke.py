import asyncio
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.services import self_ad_counter


class FakeMessage:
    def __init__(
        self,
        *,
        text="hello",
        caption=None,
        topic_id=429,
        username="baraholka_pt",
    ):
        self.text = text
        self.caption = caption
        self.message_thread_id = topic_id
        self.chat = SimpleNamespace(username=username)
        self.from_user = SimpleNamespace(is_bot=False)
        self.sent = []

    async def answer(self, text, **kwargs):
        self.sent.append((text, kwargs))


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        old_path = settings.self_ad_state_path
        settings.self_ad_state_path = str(Path(tmp) / "self_ad_counter.json")
        try:
            for _ in range(8):
                msg = FakeMessage()
                posted = await self_ad_counter.process_self_ad_message(msg)
                assert posted is False
                assert msg.sent == []

            msg = FakeMessage()
            posted = await self_ad_counter.process_self_ad_message(msg)
            assert posted is True
            assert len(msg.sent) == 1
            assert msg.sent[0][1].get("parse_mode") == "HTML"
            link_preview = msg.sent[0][1].get("link_preview_options")
            assert link_preview is not None
            assert link_preview.url == "https://t.me/CargoPT_bot"
            assert link_preview.is_disabled is False

            for _ in range(8):
                msg = FakeMessage(username="proflistpt", topic_id=8490)
                posted = await self_ad_counter.process_self_ad_message(msg)
                assert posted is False
                assert msg.sent == []

            msg = FakeMessage(username="proflistpt", topic_id=8490)
            posted = await self_ad_counter.process_self_ad_message(msg)
            assert posted is True
            assert len(msg.sent) == 1

            for _ in range(8):
                msg = FakeMessage(text=None, caption="captioned media")
                posted = await self_ad_counter.process_self_ad_message(msg)
                assert posted is False
                assert msg.sent == []

            msg = FakeMessage(text=None, caption="captioned media")
            posted = await self_ad_counter.process_self_ad_message(msg)
            assert posted is True
            assert len(msg.sent) == 1


            wrong_topic = FakeMessage(topic_id=430)
            posted = await self_ad_counter.process_self_ad_message(wrong_topic)
            assert posted is False
            assert wrong_topic.sent == []

            wrong_chat = FakeMessage(username="other_chat", topic_id=8490)
            posted = await self_ad_counter.process_self_ad_message(wrong_chat)
            assert posted is False
            assert wrong_chat.sent == []

            own_ad_message = FakeMessage(text=self_ad_counter.SELF_AD_TEXT)
            posted = await self_ad_counter.process_self_ad_message(own_ad_message)
            assert posted is False
            assert own_ad_message.sent == []
        finally:
            settings.self_ad_state_path = old_path

    print("SELF_AD_COUNTER_SMOKE_OK")


asyncio.run(main())
