import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree

from scripts.atomic_write import atomic_write_text


ROOT = Path(__file__).resolve().parents[1]
SITEMAP = ROOT / "app/static/sitemap.xml"
DATE = "2026-09-19"

REMOVE = {
    "https://cargopt.pt/mudancas-porto-lisboa/",
    "https://cargopt.pt/guias/precos/fatores-preco-mudanca/",
}

TOUCH = {
    "https://cargopt.pt/",
    "https://cargopt.pt/en/",
    "https://cargopt.pt/ru/",
    "https://cargopt.pt/mudancas-escritorio-lisboa/",
    "https://cargopt.pt/transportadora-porto/",
    "https://cargopt.pt/transporte-cama-lisboa/",
    "https://cargopt.pt/transporte-sofa-lisboa/",
    "https://cargopt.pt/transporte-frigorifico-lisboa/",
    "https://cargopt.pt/transporte-eletrodomesticos-lisboa/",
    "https://cargopt.pt/transportadores/",
    "https://cargopt.pt/en/carriers/",
    "https://cargopt.pt/ru/carriers/",
    "https://cargopt.pt/guias/objetos/como-transportar-frigorifico/",
    "https://cargopt.pt/guias/objetos/preparar-frigorifico-transporte/",
    "https://cargopt.pt/guias/objetos/como-transportar-maquina-lavar/",
    "https://cargopt.pt/guias/objetos/como-transportar-sofa/",
    "https://cargopt.pt/guias/embalamento/como-embalar-louca/",
    "https://cargopt.pt/guias/embalamento/como-embalar-televisao/",
    "https://cargopt.pt/guias/precos/quanto-custa-uma-mudanca/",
    "https://cargopt.pt/en/guides/how-much-does-a-move-cost/",
    "https://cargopt.pt/ru/guides/skolko-stoit-pereezd/",
    "https://cargopt.pt/en/guides/moving-price-factors/",
    "https://cargopt.pt/ru/guides/faktory-stoimosti-pereezda/",
    "https://cargopt.pt/mudancas-lisboa-porto/",
    "https://cargopt.pt/en/guides/moving-lisbon-to-porto/",
    "https://cargopt.pt/ru/guides/pereezd-lissabon-portu/",
    "https://cargopt.pt/guias/",
    "https://cargopt.pt/knowledge.md",
}

ADD = {
    "https://cargopt.pt/mudancas-pequenas-lisboa/",
    "https://cargopt.pt/en/small-moves-lisbon/",
    "https://cargopt.pt/ru/nebolshoy-pereezd-lissabon/",
    "https://cargopt.pt/transporte-urgente-portugal/",
    "https://cargopt.pt/en/urgent-transport-portugal/",
    "https://cargopt.pt/ru/srochnaya-perevozka-portugaliya/",
    "https://cargopt.pt/servico-embalamento-desmontagem-montagem/",
    "https://cargopt.pt/en/packing-disassembly-assembly/",
    "https://cargopt.pt/ru/upakovka-razborka-sborka/",
}


def main() -> None:
    source = subprocess.check_output(
        ["git", "show", "HEAD:app/static/sitemap.xml"],
        cwd=ROOT,
        text=True,
    )
    lines = []
    seen = set()
    for line in source.splitlines():
        match = re.search(r"<loc>([^<]+)</loc>", line)
        if not match:
            lines.append(line)
            continue
        url = match.group(1)
        if url in REMOVE:
            continue
        if url in TOUCH:
            line = re.sub(r"<lastmod>[^<]+</lastmod>", f"<lastmod>{DATE}</lastmod>", line)
        seen.add(url)
        lines.append(line)
    insert_at = lines.index("</urlset>")
    additions = [
        f"  <url><loc>{url}</loc><lastmod>{DATE}</lastmod></url>"
        for url in sorted(ADD - seen)
    ]
    lines[insert_at:insert_at] = additions
    atomic_write_text(SITEMAP, "\n".join(lines) + "\n")
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    parsed = ElementTree.fromstring(SITEMAP.read_text(encoding="utf-8"))
    urls = [node.text for node in parsed.findall(f"{{{namespace}}}url/{{{namespace}}}loc")]
    assert not (REMOVE & set(urls))
    assert ADD <= set(urls)
    assert len(urls) == len(set(urls))
    print("SEO_SITEMAP_UPDATED", len(urls))


if __name__ == "__main__":
    main()
