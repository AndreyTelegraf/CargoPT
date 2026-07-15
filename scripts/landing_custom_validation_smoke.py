from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"

js = (STATIC / "assets/js/landing.js").read_text(encoding="utf-8")
css = (STATIC / "assets/css/landing.css").read_text(encoding="utf-8")
ru = (STATIC / "ru/carriers/index.html").read_text(encoding="utf-8")

assert "Для начала<br>работы с нами" in ru
assert "Всё готово чтобы начать" in ru
assert "Чтобы войти<br>в нашу систему" not in ru
assert "Всё готово для начала работы" not in ru

assert (
    'required: "Preencha os campos obrigatórios para continuar.",'
    in js
)
assert (
    'required: "Fill in the required fields to continue.",'
    in js
)
assert (
    'required: "Заполните обязательные поля, чтобы продолжить.",'
    in js
)

assert "field.reportValidity();" not in js
assert 'messageNode.className = "field-validation-message"' in js
assert 'messageNode.setAttribute("role", "alert")' in js
assert 'field.setAttribute("aria-invalid", "true")' in js
assert 'field.setAttribute("aria-describedby", messageId)' in js
assert 'form.addEventListener("input", clearEditedFieldValidity)' in js
assert 'form.addEventListener("change", clearEditedFieldValidity)' in js

assert ".field-validation-message {" in css
assert ".field-validation-message::before {" in css
assert ".field-validation-icon {" in css
assert '[aria-invalid="true"]' in css

for relative in (
    "index.html",
    "en/index.html",
    "ru/index.html",
):
    html = (STATIC / relative).read_text(encoding="utf-8")

    assert (
        "/assets/css/landing.css?v="
        in html
    )
    assert (
        "/assets/js/landing.js?v=custom-validation-v1"
        in html
    )
    assert 'id="requestForm"' in html
    assert "novalidate" in html

print("LANDING_CUSTOM_VALIDATION_SMOKE_OK")
