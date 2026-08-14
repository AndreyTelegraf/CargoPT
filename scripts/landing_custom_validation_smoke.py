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

assert "let firstInvalidField = null;" in js
assert "function validateField(field, focusField = false)" in js
assert "const isValid = validateField(field);" in js
assert "if (!isValid && firstInvalidField === null) {" in js
assert "firstInvalidField = field;" in js
assert "if (firstInvalidField) {" in js
assert "firstInvalidField.focus({preventScroll: true});" in js
assert "firstInvalidField.scrollIntoView({" in js
assert "validateRequiredField(field, true)" not in js

assert "const SUBMIT_TIMEOUT_MS = 15000;" in js
assert "class RequestSubmissionError extends Error" in js
assert 'if (status === 400 || status === 422) return "validation";' in js
assert 'if (status === 409) return "conflict";' in js
assert 'if (status === 429) return "rateLimit";' in js
assert 'if (status >= 500) return "server";' in js
assert 'error.name === "AbortError"' in js
assert "error instanceof TypeError" in js
assert "signal: controller.signal" in js
assert "messages.failure" not in js
assert 'validationFailure: "Alguns dados do pedido não são válidos.' in js
assert 'serverFailure: "A server error occurred.' in js
assert 'networkFailure: "Не удалось соединиться с сервером.' in js

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
        "/assets/css/landing-designer-review-v1.css"
        in html
    )
    assert (
        "/assets/js/landing.js?v=location-selector-v1"
        in html
    )
    assert "/assets/css/components.css?v=location-selector-v1" in html
    assert html.count('data-location-field') == 2
    assert html.count('data-location-search') == 2
    assert html.count('data-location-confirmation') == 2
    assert html.count('data-location-confirm>') == 2
    assert html.count('openstreetmap.org/copyright') == 2
    assert 'aria-autocomplete="list"' not in html
    assert 'id="requestForm"' in html
    assert "novalidate" in html

assert "LOCATION_SEARCH_DEBOUNCE_MS" not in js
assert 'searchButton.addEventListener("click"' in js

print("LANDING_CUSTOM_VALIDATION_SMOKE_OK")
