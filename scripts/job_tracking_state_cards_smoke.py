from pathlib import Path


def main() -> None:
    html = Path("app/static/track/index.html").read_text()
    js = Path("app/static/assets/js/track.js").read_text()
    css = Path("app/static/assets/css/track.css").read_text()

    assert "id=\"stateCard\"" in html
    assert "id=\"stateIcon\"" in html
    assert "id=\"stateEyebrow\"" in html

    for text in (
        "Pedido recebido",
        "À procura",
        "Propostas recebidas",
        "Transportador escolhido",
        "Negócio confirmado",
        "Concluído",
    ):
        assert text in js

    for tone in (
        "waiting",
        "searching",
        "action",
        "success",
        "warning",
        "closed",
    ):
        assert f"tone: \"{tone}\"" in js

    assert "state-card-${copy.tone}" in js

    assert ".state-card" in css
    assert ".state-icon" in css
    assert ".state-card-action" in css
    assert ".state-card-success" in css
    assert ".state-card-warning" in css

    print("job_tracking_state_cards_ok")


if __name__ == "__main__":
    main()
