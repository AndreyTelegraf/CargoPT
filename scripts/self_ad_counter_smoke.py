import asyncio
import json
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


async def trigger_next_ad(
    *,
    username="baraholka_pt",
    topic_id=429,
    every_n=20,
    text="hello",
    caption=None,
):
    messages = []

    for _ in range(every_n - 1):
        msg = FakeMessage(
            text=text,
            caption=caption,
            username=username,
            topic_id=topic_id,
        )
        posted = await self_ad_counter.process_self_ad_message(msg)
        assert posted is False
        assert msg.sent == []

    msg = FakeMessage(
        text=text,
        caption=caption,
        username=username,
        topic_id=topic_id,
    )
    posted = await self_ad_counter.process_self_ad_message(msg)
    assert posted is True
    assert len(msg.sent) == 1

    messages.append(msg.sent[0])
    return messages[0]


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        old_path = settings.self_ad_state_path

        try:
            state_path = Path(tmp) / "rotation.json"
            settings.self_ad_state_path = str(state_path)

            published = []
            for expected_text in self_ad_counter.SELF_AD_TEXTS:
                sent_text, kwargs = await trigger_next_ad()
                published.append(sent_text)

                assert sent_text == expected_text
                assert kwargs.get("parse_mode") == "HTML"

                preview = kwargs.get("link_preview_options")
                assert preview is not None
                assert preview.url == "https://cargopt.pt"
                assert preview.is_disabled is False

            sent_text, _ = await trigger_next_ad()
            assert sent_text == self_ad_counter.SELF_AD_TEXTS[0]
            assert published == list(self_ad_counter.SELF_AD_TEXTS)

            state = json.loads(state_path.read_text())
            assert state["text_counts"]["baraholka_pt:429"] == 160
            assert state["variant_indexes"]["baraholka_pt:429"] == 1

            proflist_text, _ = await trigger_next_ad(
                username="proflistpt",
                topic_id=8490,
                every_n=9,
            )
            assert proflist_text == self_ad_counter.SELF_AD_TEXTS[0]

            state = json.loads(state_path.read_text())
            assert state["variant_indexes"]["baraholka_pt:429"] == 1
            assert state["variant_indexes"]["proflistpt:8490"] == 1

            caption_path = Path(tmp) / "captions.json"
            settings.self_ad_state_path = str(caption_path)

            caption_text, _ = await trigger_next_ad(
                text=None,
                caption="Медиа с подписью",
            )
            assert caption_text == self_ad_counter.SELF_AD_TEXTS[0]

            for own_ad in self_ad_counter.SELF_AD_TEXTS:
                msg = FakeMessage(text=own_ad)
                posted = await self_ad_counter.process_self_ad_message(msg)
                assert posted is False
                assert msg.sent == []

            wrong_topic = FakeMessage(topic_id=430)
            assert await self_ad_counter.process_self_ad_message(
                wrong_topic
            ) is False

            wrong_chat = FakeMessage(
                username="other_chat",
                topic_id=8490,
            )
            assert await self_ad_counter.process_self_ad_message(
                wrong_chat
            ) is False

        finally:
            settings.self_ad_state_path = old_path

    print("SELF_AD_COUNTER_SMOKE_OK")


asyncio.run(main())
