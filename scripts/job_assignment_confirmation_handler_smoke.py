from pathlib import Path

source = Path("app/bot/handlers/job_assignment_confirmation.py").read_text(encoding="utf-8")

assert "except TelegramBadRequest:" in source
assert "await callback.message.edit_text(" in source
assert "_build_assignment_confirmation_final_text(" in source
assert 'parse_mode="HTML"' in source
assert "await callback.message.edit_reply_markup(reply_markup=None)" in source
assert "build_assignment_failure_reason_keyboard" in source
assert "assignment:fail_reason:" in source
assert "is_valid_decline_reason" in source
assert "accepted_offer.decline_reason = failure_reason" in source
assert "Укажите причину, почему сделка не состоялась." in source
assert "Причина выбрана. Следующий слой сохранит её в заявке." not in source
assert "pass" in source

print("JOB_ASSIGNMENT_CONFIRMATION_HANDLER_SMOKE_OK")
