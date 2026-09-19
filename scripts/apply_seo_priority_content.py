import json
from pathlib import Path

from scripts.atomic_write import atomic_write_text


ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "content/guides/articles"
UPDATED = "2026-09-19"


PRIORITY_GUIDES = {
    "transporte-frigorifico-lisboa.json": {
        "meta_title": "Transporte de frigorífico em Lisboa: pedir propostas — CargoPT",
        "meta_description": "Peça propostas para transportar um frigorífico em Lisboa com medidas, fotografias, andares, elevadores, ajudantes e posição de transporte.",
        "hero_description": "Descreva o frigorífico, os acessos e a ajuda necessária para que transportadores independentes possam avaliar o mesmo serviço. A disponibilidade e as propostas não são garantidas.",
        "section": {
            "id": "pedido-local-frigorifico",
            "heading": "Dados que evitam dúvidas num transporte local",
            "paragraphs": [
                "Em Lisboa, o percurso dentro dos edifícios pode ser mais determinante do que a distância de estrada. Informe elevadores, escadas, corredores, portas e a distância real até ao lugar onde o veículo pode parar.",
                "Indique ainda se o aparelho estará desligado, vazio, descongelado e seco. A posição e o tempo de espera antes de voltar a ligar devem seguir o manual do fabricante.",
            ],
            "checklist": [
                "Medidas, peso aproximado, modelo e fotografias.",
                "Andares e elevadores nas duas moradas.",
                "Escadas, portas estreitas e distância ao veículo.",
                "Ajuda disponível e equipamento pretendido.",
                "Data, horário e preparação já concluída.",
            ],
        },
        "link": {"title": "Como preparar um frigorífico para transporte", "href": "/guias/objetos/preparar-frigorifico-transporte/", "type": "guide"},
    },
    "transporte-sofa-lisboa.json": {
        "meta_title": "Transporte de sofá em Lisboa: medidas e acessos — CargoPT",
        "meta_description": "Peça propostas para transportar um sofá em Lisboa com medidas, fotografias, módulos, desmontagem, escadas, elevador e ajudantes.",
        "hero_description": "Meça o sofá e todo o percurso, identifique peças desmontáveis e descreva a ajuda necessária. A disponibilidade e as propostas não são garantidas.",
        "section": {
            "id": "pedido-local-sofa",
            "heading": "O percurso que deve fotografar em Lisboa",
            "paragraphs": [
                "Fotografe a porta, o corredor, o elevador, os patamares e as curvas das escadas nas duas moradas. Indique também a distância entre a entrada e o local de estacionamento possível.",
                "Se o sofá tem módulos, chaise longue, pés ou braços removíveis, mostre-os separadamente. Não presuma que a desmontagem e a montagem estão incluídas na proposta.",
            ],
            "checklist": [
                "Medidas totais e de cada módulo.",
                "Portas, elevador, escadas, curvas e corredores.",
                "Peças removíveis e necessidade de ferramentas.",
                "Proteção pretendida para tecido, pele e cantos.",
                "Ajudantes disponíveis na recolha e entrega.",
            ],
        },
        "link": {"title": "Como transportar um sofá", "href": "/guias/objetos/como-transportar-sofa/", "type": "guide"},
    },
    "como-transportar-frigorifico.json": {
        "meta_title": "Como transportar um frigorífico em segurança — CargoPT",
        "meta_description": "Passos para transportar um frigorífico: preparação, posição vertical, medidas, acessos e dados necessários para pedir propostas comparáveis.",
        "hero_description": "Prepare o frigorífico, meça os acessos e descreva posição, dimensões e ajuda necessária antes de pedir transporte.",
        "section": {
            "id": "dados-pedido-frigorifico",
            "heading": "Que dados deve enviar para transportar um frigorífico?",
            "paragraphs": [
                "Um pedido útil identifica o aparelho e o percurso real. Esta informação permite avaliar capacidade, ajudantes e equipamento sem assumir condições que só serão descobertas no local.",
                "Na CargoPT, estes dados fazem parte da avaliação por transportadores independentes. Uma descrição completa não garante proposta, mas reduz perguntas e respostas baseadas em cargas diferentes.",
            ],
            "checklist": [
                "Altura, largura, profundidade e peso aproximado do frigorífico.",
                "Modelo, número de portas e fotografias do aparelho.",
                "Andares, elevadores, escadas, corredores e portas nos dois locais.",
                "Distância entre a entrada e o lugar onde o veículo pode parar.",
                "Ajuda disponível e necessidade de carrinho, plataforma ou mais pessoas.",
                "Data, janela horária e tempo disponível para preparar o aparelho.",
            ],
        },
        "link": {"title": "Pedir transporte de frigorífico em Lisboa", "href": "/transporte-frigorifico-lisboa/", "type": "service"},
    },
    "preparar-frigorifico-transporte.json": {
        "meta_title": "Como preparar um frigorífico para transporte — CargoPT",
        "meta_description": "Checklist para desligar, esvaziar, descongelar, secar e proteger um frigorífico antes do transporte, sem esquecer acessos e medidas.",
        "hero_description": "Esvazie, descongele, seque e proteja o aparelho com antecedência, seguindo o manual do fabricante e confirmando os acessos.",
        "section": {
            "id": "confirmacao-antes-recolha",
            "heading": "O que confirmar antes da recolha",
            "paragraphs": [
                "Além de preparar o aparelho, confirme com o transportador a posição prevista, o número de ajudantes e o equipamento de movimentação. O método adequado depende do modelo e das instruções do fabricante.",
                "Envie fotografias do frigorífico e das zonas estreitas. Informe também se portas, puxadores ou outros elementos podem precisar de remoção e quem ficará responsável por essa tarefa.",
            ],
            "checklist": [
                "Manual do fabricante consultado para transporte e reinício.",
                "Interior vazio, descongelado e seco.",
                "Prateleiras, gavetas, portas e cabo protegidos.",
                "Medidas do aparelho e dos acessos verificadas.",
                "Percurso, ajudantes e equipamento confirmados.",
            ],
        },
        "link": {"title": "Pedir transporte de frigorífico em Lisboa", "href": "/transporte-frigorifico-lisboa/", "type": "service"},
    },
    "como-transportar-maquina-lavar.json": {
        "meta_title": "Como transportar uma máquina de lavar — CargoPT",
        "meta_description": "Prepare uma máquina de lavar para transporte: desligar, drenar, fixar o tambor, medir acessos e informar peso, andares e ajudantes.",
        "hero_description": "Desligue e drene a máquina, siga o manual para fixar o tambor e descreva peso, medidas e acessos antes do transporte.",
        "section": {
            "id": "dados-pedido-maquina-lavar",
            "heading": "Que informação ajuda a avaliar o transporte?",
            "paragraphs": [
                "O tipo de máquina, as dimensões, o peso aproximado e os acessos determinam o número de pessoas e os meios de movimentação. Fotografias ajudam a distinguir uma carga simples de um percurso com risco adicional.",
                "A ligação e a instalação técnica no destino não devem ser presumidas. Se precisar dessas tarefas, identifique-as separadamente e confirme se fazem parte da proposta.",
            ],
            "checklist": [
                "Modelo, medidas, peso aproximado e fotografias.",
                "Estado das mangueiras, cabo e parafusos de transporte.",
                "Andares, elevadores, escadas e portas nos dois locais.",
                "Ajuda disponível para carga e descarga.",
                "Necessidade de desligação ou instalação técnica, se aplicável.",
            ],
        },
        "link": {"title": "Pedir transporte de eletrodomésticos em Lisboa", "href": "/transporte-eletrodomesticos-lisboa/", "type": "service"},
    },
    "como-transportar-sofa.json": {
        "meta_title": "Como transportar um sofá: medidas e acessos — CargoPT",
        "meta_description": "Meça sofá, portas, escadas e elevador; verifique módulos e pés desmontáveis e prepare um pedido de transporte com fotografias.",
        "hero_description": "Antes de transportar um sofá, compare as medidas com todo o percurso e identifique módulos, pés, acessos e ajuda necessária.",
        "section": {
            "id": "mapa-percurso-sofa",
            "heading": "Crie um mapa simples do percurso do sofá",
            "paragraphs": [
                "Meça não apenas a porta principal, mas também elevador, patamares, curvas, corredores e portões. Uma única passagem estreita pode definir se o sofá sai inteiro ou precisa de desmontagem.",
                "Fotografe as curvas críticas e indique a distância até ao veículo. Partilhe as mesmas imagens com todos os transportadores para comparar propostas sobre o mesmo trabalho.",
            ],
            "checklist": [
                "Largura, altura e profundidade do sofá.",
                "Módulos, chaise longue, pés e braços removíveis.",
                "Largura e altura de portas, elevador e corredores.",
                "Escadas, patamares, curvas e distância ao veículo.",
                "Proteção, desmontagem e número de ajudantes pretendidos.",
            ],
        },
        "link": {"title": "Pedir transporte de sofá em Lisboa", "href": "/transporte-sofa-lisboa/", "type": "service"},
    },
    "como-embalar-louca.json": {
        "meta_title": "Como embalar louça e copos para uma mudança — CargoPT",
        "meta_description": "Checklist para embalar pratos, copos e peças frágeis: materiais, separação, preenchimento, peso das caixas e identificação.",
        "hero_description": "Separe por tipo, envolva cada peça, elimine folgas e mantenha as caixas manuseáveis e claramente identificadas.",
        "section": {
            "id": "entrega-caixas-frageis",
            "heading": "Como entregar as caixas frágeis ao transportador",
            "paragraphs": [
                "Identifique a parte superior, o conteúdo e as caixas que não podem receber peso. Evite caixas demasiado pesadas, porque o fundo e a pega ficam mais sujeitos a falhas durante a movimentação.",
                "No pedido, indique a quantidade de caixas frágeis, o peso aproximado e se existem peças de valor especial. Confirme como serão colocadas e fixadas no veículo.",
            ],
            "checklist": [
                "Caixas fechadas, identificadas e sem movimento interno.",
                "Peso distribuído por várias caixas manuseáveis.",
                "Parte superior e conteúdo marcados.",
                "Peças excecionais descritas e fotografadas.",
                "Posição e fixação no veículo confirmadas.",
            ],
        },
        "link": {"title": "Pedir embalagem, desmontagem e montagem", "href": "/servico-embalamento-desmontagem-montagem/", "type": "service"},
    },
    "como-embalar-televisao.json": {
        "meta_title": "Como embalar uma televisão para transporte — CargoPT",
        "meta_description": "Proteja e transporte uma televisão com caixa adequada, ecrã protegido, base separada, posição vertical e dados completos no pedido.",
        "hero_description": "Use a caixa original ou uma solução ajustada, proteja o ecrã sem pressão e planeie transporte vertical e fixado.",
        "section": {
            "id": "dados-pedido-televisao",
            "heading": "Que dados enviar para transportar uma televisão",
            "paragraphs": [
                "Indique diagonal, largura, altura, profundidade e se existe caixa original. Uma fotografia da televisão e da embalagem ajuda a avaliar espaço, proteção e fixação.",
                "Se a televisão está presa à parede, esclareça se será retirada antes da recolha. A desmontagem do suporte e a instalação no destino não devem ser consideradas incluídas sem confirmação.",
            ],
            "checklist": [
                "Modelo, diagonal, dimensões e fotografias.",
                "Caixa original ou material de proteção disponível.",
                "Base, comando, cabos e suporte identificados separadamente.",
                "Andares, elevador, escadas e distância até ao veículo.",
                "Retirada e instalação de suporte confirmadas, se necessárias.",
            ],
        },
        "link": {"title": "Pedir embalagem, desmontagem e montagem", "href": "/servico-embalamento-desmontagem-montagem/", "type": "service"},
    },
}


PRICE_MERGE = {
    "quanto-custa-uma-mudanca.json": {
        "id": "fatores-descricao-comparavel",
        "heading": "Como transformar os fatores de preço numa descrição comparável",
        "paragraphs": [
            "Volume, peso, distância, acessos, ajudantes e serviços adicionais só são úteis quando aparecem como dados concretos. Em vez de escrever apenas “mudança de casa”, indique objetos, quantidades, medidas, pisos, elevadores e tarefas.",
            "Envie a mesma descrição e as mesmas fotografias a todos os transportadores. Assim, diferenças de preço refletem melhor as condições propostas e não omissões diferentes no pedido.",
        ],
        "items": [
            {"title": "Carga", "text": "Liste objetos, quantidades, dimensões e itens pesados ou frágeis."},
            {"title": "Percurso", "text": "Indique moradas, distância até ao veículo, andares, elevadores e escadas."},
            {"title": "Equipa", "text": "Confirme quem carrega e descarrega e quantos ajudantes são necessários."},
            {"title": "Serviços", "text": "Separe embalagem, materiais, desmontagem, montagem e equipamento especial."},
            {"title": "Data", "text": "Registe janela horária, flexibilidade real e limitações de acesso."},
        ],
    },
    "how-much-does-a-move-cost-en.json": {
        "id": "factors-comparable-description",
        "heading": "Turn price factors into a comparable description",
        "paragraphs": [
            "Volume, weight, distance, access, helpers and additional services are useful only when stated as concrete details. Instead of writing only “house move”, list items, quantities, measurements, floors, lifts and tasks.",
            "Share the same description and photos with every carrier. Price differences are then more likely to reflect the offered terms instead of different missing information.",
        ],
        "items": [
            {"title": "Load", "text": "List items, quantities, measurements and anything heavy or fragile."},
            {"title": "Route", "text": "State addresses, walking distance, floors, lifts and stairs."},
            {"title": "Team", "text": "Confirm who loads and unloads and how many helpers are required."},
            {"title": "Services", "text": "Separate packing, materials, disassembly, assembly and special equipment."},
            {"title": "Date", "text": "Record the time window, real flexibility and access limits."},
        ],
    },
    "skolko-stoit-pereezd-ru.json": {
        "id": "faktory-sravnimoe-opisanie",
        "heading": "Как превратить факторы цены в сопоставимое описание",
        "paragraphs": [
            "Объём, вес, расстояние, доступ, грузчики и дополнительные работы полезны только как конкретные данные. Вместо слов «переезд квартиры» перечислите вещи, количество, размеры, этажи, лифты и задачи.",
            "Отправляйте всем перевозчикам одинаковое описание и фотографии. Тогда разница в цене точнее отражает условия предложений, а не разный объём недостающих данных.",
        ],
        "items": [
            {"title": "Груз", "text": "Перечислите вещи, количество, размеры, тяжёлые и хрупкие предметы."},
            {"title": "Маршрут", "text": "Укажите адреса, путь до машины, этажи, лифты и лестницы."},
            {"title": "Команда", "text": "Зафиксируйте, кто грузит и разгружает и сколько нужно грузчиков."},
            {"title": "Работы", "text": "Отделите упаковку, материалы, разборку, сборку и оборудование."},
            {"title": "Дата", "text": "Укажите временное окно, реальную гибкость и ограничения доступа."},
        ],
    },
}


ROUTE_UPDATES = {
    "mudancas-lisboa-porto.json": {
        "title": "Mudanças entre Lisboa e o Porto",
        "meta_title": "Mudanças Lisboa–Porto nos dois sentidos — CargoPT",
        "meta_description": "Prepare uma mudança entre Lisboa e o Porto, em qualquer direção: inventário, acessos, ajudantes, proteção e serviços a confirmar.",
        "hero_description": "Prepare uma mudança Lisboa–Porto ou Porto–Lisboa com a mesma informação completa sobre carga, acessos, data e tarefas.",
        "section": {"id": "porto-lisboa", "heading": "O que muda no sentido Porto–Lisboa?", "paragraphs": ["Os dados essenciais são os mesmos nos dois sentidos: carga, acessos, data, equipa e equipamento. O que muda são as condições concretas das moradas de recolha e entrega.", "Para Porto–Lisboa, descreva primeiro o acesso no Porto e depois o destino em Lisboa. Não reutilize automaticamente informações da viagem inversa: andares, elevadores, estacionamento e distância ao veículo devem ser confirmados em cada local."], "checklist": ["Morada e acesso da recolha no Porto.", "Morada e acesso da entrega em Lisboa.", "Inventário e fotografias atuais.", "Data, flexibilidade e eventuais paragens.", "Ajudantes, proteção e serviços adicionais."]},
    },
    "moving-lisbon-to-porto-en.json": {
        "title": "Moving between Lisbon and Porto",
        "meta_title": "Moving Lisbon–Porto in either direction — CargoPT",
        "meta_description": "Prepare a move between Lisbon and Porto in either direction with a clear inventory, access details, helpers, protection and services.",
        "hero_description": "Prepare a Lisbon–Porto or Porto–Lisbon move with complete details about the load, access, date and tasks.",
        "section": {"id": "porto-lisbon", "heading": "What changes for a Porto-to-Lisbon move?", "paragraphs": ["The essential details are the same in both directions: load, access, date, team and equipment. What changes are the actual conditions at pickup and delivery.", "For Porto to Lisbon, describe the Porto pickup first and the Lisbon destination second. Do not reuse access assumptions from the reverse trip: floors, lifts, parking and walking distance must be checked at each address."], "checklist": ["Pickup address and access in Porto.", "Delivery address and access in Lisbon.", "Current inventory and photos.", "Date, flexibility and any stops.", "Helpers, protection and additional services."]},
    },
    "pereezd-lissabon-portu-ru.json": {
        "title": "Переезд между Лиссабоном и Порту",
        "meta_title": "Переезд Лиссабон–Порту в обе стороны — CargoPT",
        "meta_description": "Подготовьте переезд между Лиссабоном и Порту в любую сторону: список вещей, доступ, грузчики, защита и дополнительные работы.",
        "hero_description": "Опишите груз, доступ, дату и работы для переезда Лиссабон–Порту или Порту–Лиссабон.",
        "section": {"id": "portu-lissabon", "heading": "Что меняется при переезде из Порту в Лиссабон?", "paragraphs": ["Главные данные одинаковы в обоих направлениях: груз, доступ, дата, команда и оборудование. Меняются конкретные условия по адресам погрузки и доставки.", "Для маршрута Порту–Лиссабон сначала опишите доступ в Порту, затем адрес в Лиссабоне. Не переносите автоматически условия обратного маршрута: этажи, лифты, парковку и расстояние до машины проверяют для каждого адреса."], "checklist": ["Адрес и доступ при погрузке в Порту.", "Адрес и доступ при доставке в Лиссабоне.", "Актуальный список и фотографии вещей.", "Дата, гибкость и промежуточные точки.", "Грузчики, защита и дополнительные работы."]},
    },
}


def load(name: str) -> dict:
    return json.loads((ARTICLES / name).read_text(encoding="utf-8"))


def save(name: str, payload: dict) -> None:
    atomic_write_text(ARTICLES / name, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print("SEO_GUIDE_UPDATED", name)


def insert_before_cargopt(article: dict, section: dict) -> None:
    article["sections"] = [item for item in article["sections"] if item.get("id") != section["id"]]
    index = next((i for i, item in enumerate(article["sections"]) if item.get("id") == "cargopt"), len(article["sections"]))
    article["sections"].insert(index, section)


def main() -> None:
    for name, update in PRIORITY_GUIDES.items():
        article = load(name)
        for key in ("meta_title", "meta_description", "hero_description"):
            article[key] = update[key]
        article["date_modified"] = UPDATED
        insert_before_cargopt(article, update["section"])
        article["related_links"] = [item for item in article["related_links"] if item.get("href") != update["link"]["href"]]
        article["related_links"].insert(0, update["link"])
        save(name, article)

    for name, section in PRICE_MERGE.items():
        article = load(name)
        article["date_modified"] = UPDATED
        insert_before_cargopt(article, section)
        save(name, article)

    for name, update in ROUTE_UPDATES.items():
        article = load(name)
        for key in ("title", "meta_title", "meta_description", "hero_description"):
            article[key] = update[key]
        article["date_modified"] = UPDATED
        insert_before_cargopt(article, update["section"])
        save(name, article)

    for name in ("moving-price-factors-en.json", "faktory-stoimosti-pereezda-ru.json"):
        article = load(name)
        article["alternates"]["pt-PT"] = "/guias/precos/quanto-custa-uma-mudanca/"
        article["date_modified"] = UPDATED
        for link in article["related_links"]:
            if link.get("href") == "/guias/precos/fatores-preco-mudanca/":
                link["href"] = "/guias/precos/quanto-custa-uma-mudanca/"
        save(name, article)


if __name__ == "__main__":
    main()
