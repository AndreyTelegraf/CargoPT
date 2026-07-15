from pathlib import Path

source = Path("app/bot/handlers/job_assignment_confirmation.py").read_text(encoding="utf-8")
handler = source[source.index("async def handle_assignment_confirmation"):]

assert "await callback.message.edit_text(" in handler
assert "_build_assignment_confirmation_final_text(" in handler
assert 'parse_mode="HTML"' in handler
assert "await callback.message.edit_reply_markup(reply_markup=None)" in handler
assert "await callback.answer(alert_text, show_alert=True)" in handler

print("ASSIGNMENT_CONFIRMATION_MESSAGE_CLEANUP_SMOKE_OK")
