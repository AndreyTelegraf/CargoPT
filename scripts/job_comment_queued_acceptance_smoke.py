import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.bot.handlers.job_comment import _submission_status_text


def main() -> None:
    expected_copy = {
        "pt": ("colocado na fila", "enviado a", "não encontrámos"),
        "en": ("queued for", "sent to", "could not find"),
        "ru": ("поставлена в очередь", "отправили её", "нет подходящих"),
    }

    for locale, (queued_copy, sent_copy, no_carriers_copy) in expected_copy.items():
        queued = _submission_status_text(locale, queued_count=2, sent_count=3)
        sent = _submission_status_text(locale, queued_count=0, sent_count=3)
        no_carriers = _submission_status_text(
            locale,
            queued_count=0,
            sent_count=0,
        )

        assert queued_copy in queued
        assert "2" in queued
        assert sent_copy not in queued
        assert sent_copy in sent
        assert "3" in sent
        assert no_carriers_copy in no_carriers

    print("JOB_COMMENT_QUEUED_ACCEPTANCE_SMOKE_OK")


if __name__ == "__main__":
    main()
