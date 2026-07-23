from pathlib import Path

js = Path("app/static/assets/js/track.js").read_text(
    encoding="utf-8"
)

for text in (
    "o pedido ficou guardado em «Meus pedidos» neste navegador",
    'searchingTitle: "Request submitted successfully"',
    "the request is saved under “My requests” in this browser",
    'searchingTitle: "Заявка успешно отправлена"',
    "заявка сохранена в разделе «Мои заявки» в этом браузере",
):
    assert text in js

assert js.count("searchingTitle:") == 3
assert js.count("searchingText:") == 3

print("TRACKING_RETURN_COPY_SMOKE_OK")
