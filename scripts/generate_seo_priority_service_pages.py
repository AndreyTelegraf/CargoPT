import html
import json
from pathlib import Path

from scripts.atomic_write import atomic_write_text


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"
UPDATED = "2026-09-19"


LOCALES = {
    "pt": {
        "lang": "pt-PT",
        "home": "/",
        "request": "/#request",
        "request_label": "Receber propostas",
        "open_form": "Abrir formulário",
        "nav": "Navegação",
        "choose": "Escolher idioma",
        "start": "Começar",
        "how": "Quando faz sentido",
        "details": "Dados para um pedido útil",
        "offer": "O que confirmar numa proposta",
        "limits": "Limites importantes",
        "faq": "Perguntas frequentes",
        "related": "Guias e serviços relacionados",
        "updated": "Revisto pela Redação CargoPT · Atualizado em 19 de setembro de 2026",
        "footer": [
            ("/transportadores/", "Para transportadores"),
            ("/privacy/", "Privacidade"),
            ("/terms/", "Termos"),
            ("/cookies/", "Cookies"),
        ],
        "legal": "Informação legal",
        "contact": "Contacto",
    },
    "en": {
        "lang": "en",
        "home": "/en/",
        "request": "/en/#request",
        "request_label": "Get offers",
        "open_form": "Open form",
        "nav": "Navigation",
        "choose": "Choose language",
        "start": "Start",
        "how": "When it fits",
        "details": "Details for a useful request",
        "offer": "What to confirm in an offer",
        "limits": "Important limits",
        "faq": "Frequently asked questions",
        "related": "Related guides and services",
        "updated": "Reviewed by CargoPT Editorial Team · Updated 19 September 2026",
        "footer": [
            ("/en/carriers/", "Carriers"),
            ("/en/privacy/", "Privacy"),
            ("/en/terms/", "Terms"),
            ("/en/cookies/", "Cookies"),
        ],
        "legal": "Legal information",
        "contact": "Contact",
    },
    "ru": {
        "lang": "ru",
        "home": "/ru/",
        "request": "/ru/#request",
        "request_label": "Получить предложения",
        "open_form": "Открыть форму",
        "nav": "Навигация",
        "choose": "Выбрать язык",
        "start": "Начать",
        "how": "Когда это подходит",
        "details": "Данные для полезной заявки",
        "offer": "Что проверить в предложении",
        "limits": "Важные ограничения",
        "faq": "Частые вопросы",
        "related": "Связанные статьи и услуги",
        "updated": "Проверено редакцией CargoPT · Обновлено 19 сентября 2026 года",
        "footer": [
            ("/ru/carriers/", "Перевозчикам"),
            ("/ru/privacy/", "Конфиденциальность"),
            ("/ru/terms/", "Условия"),
            ("/ru/cookies/", "Cookies"),
        ],
        "legal": "Юридическая информация",
        "contact": "Контакты",
    },
}


PAGES = [
    {
        "locale": "pt", "path": "/mudancas-escritorio-lisboa/",
        "title": "Mudanças de escritório em Lisboa: pedido e preparação — CargoPT",
        "description": "Prepare uma mudança de escritório em Lisboa com inventário, acessos, horários, equipamento e tarefas definidos para comparar propostas.",
        "eyebrow": "Mudanças empresariais em Lisboa", "h1": "Mudanças de escritório em Lisboa",
        "intro": "Organize computadores, mobiliário, arquivo, acessos e janela de trabalho num único pedido. A CargoPT pode encaminhá-lo para transportadores independentes adequados; a disponibilidade e as propostas não são garantidas.",
        "uses": [("Escritório completo", "Mesas, cadeiras, armários, caixas, equipamentos e arquivo com origem e destino definidos."), ("Mudança por fases", "Indique quais equipas ou zonas mudam primeiro e as janelas permitidas em cada morada."), ("Equipamento sensível", "Identifique monitores, servidores, impressoras e peças que exigem proteção ou manuseamento específico.")],
        "inputs": ["Moradas de recolha e entrega e data pretendida.", "Inventário por quantidade, dimensões e fotografias.", "Andares, elevadores, cais, corredores e estacionamento.", "Horários de acesso ao edifício e regras do condomínio.", "Necessidade de ajudantes, embalagem, desmontagem ou montagem.", "Equipamento pesado, frágil ou com requisitos especiais."],
        "checks": [("Âmbito", "Confirme carga, descarga, embalagem, montagem e materiais incluídos."), ("Equipa e veículo", "Verifique número de ajudantes, capacidade e equipamento previsto."), ("Calendário", "Registe a janela de trabalho, fases e condições para alterações."), ("Responsabilidade", "Confirme condições, documentação e tratamento de incidentes diretamente com o transportador.")],
        "limits_text": "A CargoPT organiza e pode partilhar o pedido; não executa a mudança e não garante preço, prazo, disponibilidade ou resposta. Cada transportador define a sua proposta e é responsável pela execução acordada.",
        "faq": [("A mudança pode ser feita fora do horário comercial?", "Indique a janela necessária no pedido. A possibilidade depende das regras dos edifícios e da disponibilidade do transportador."), ("A desmontagem de mesas está incluída?", "Não automaticamente. Liste o mobiliário e confirme por escrito quais tarefas e materiais estão incluídos."), ("Como descrever computadores e monitores?", "Indique quantidades, dimensões aproximadas, fragilidade, embalagem disponível e se existem requisitos internos de TI."), ("É preciso reservar estacionamento?", "Pode ser necessário. Informe restrições, cais, distância até à entrada e autorizações aplicáveis."), ("A CargoPT garante uma proposta?", "Não. Um pedido completo facilita a avaliação, mas não garante respostas nem disponibilidade.")],
        "related": [("/guias/planeamento/como-planear-uma-mudanca/", "Como planear uma mudança"), ("/servico-embalamento-desmontagem-montagem/", "Embalagem, desmontagem e montagem"), ("/#request", "Descrever a mudança de escritório")],
    },
    {
        "locale": "pt", "path": "/transportadora-porto/",
        "title": "Transportadora no Porto para mudanças e cargas — CargoPT",
        "description": "Envie um pedido estruturado a transportadores independentes no Porto e compare as propostas disponíveis para mudanças ou cargas.",
        "eyebrow": "Transportadores no Porto", "h1": "Transportadora no Porto para mudanças e cargas",
        "intro": "Descreva rota, carga, acessos, data e tarefas uma vez. A CargoPT pode partilhar o pedido com transportadores independentes adequados no Porto ou com cobertura nacional; respostas e disponibilidade não são garantidas.",
        "uses": [("Mudanças", "Casa, apartamento, quarto ou escritório, com inventário e acessos em ambas as moradas."), ("Objetos isolados", "Móveis, eletrodomésticos ou volumes grandes com dimensões e fotografias."), ("Cargas", "Caixas, paletes ou materiais com peso, volume, meios de carga e descarga claramente descritos.")],
        "inputs": ["Origem, destino e data ou intervalo possível.", "Lista, quantidades, peso e dimensões relevantes.", "Andares, elevadores, escadas e distância até ao veículo.", "Ajudantes necessários na recolha e na entrega.", "Necessidade de plataforma, grua ou outro equipamento.", "Fotografias da carga e dos acessos difíceis."],
        "checks": [("Preço e condições", "Compare o mesmo âmbito, incluindo deslocação, ajudantes e eventuais esperas."), ("Capacidade", "Confirme que o veículo e o equipamento correspondem à carga descrita."), ("Horário", "Registe data, janela de recolha e limites de acesso."), ("Execução", "Acorde diretamente com o transportador documentação, responsabilidade e contacto no dia.")],
        "limits_text": "A CargoPT não é a transportadora e não executa o serviço. Encaminha pedidos para avaliação; cada profissional decide se responde e define preço, disponibilidade e condições.",
        "faq": [("A CargoPT é uma transportadora no Porto?", "Não. É um serviço de pedidos que pode ligar clientes a transportadores independentes adequados."), ("Posso pedir apenas um móvel?", "Sim. Indique dimensões, peso aproximado, fotografias, acessos e ajuda disponível."), ("Recebo sempre várias propostas?", "Não. O número de respostas depende da rota, data, carga e disponibilidade dos transportadores."), ("Posso pedir transporte para outra cidade?", "Sim. Descreva a rota completa e eventuais paragens para que o pedido seja avaliado."), ("Como comparar propostas?", "Confirme que todas incluem a mesma carga, tarefas, ajudantes, equipamento e condições.")],
        "related": [("/mudancas-porto/", "Mudanças no Porto"), ("/mudancas-lisboa-porto/", "Mudanças entre Lisboa e o Porto"), ("/#request", "Pedir propostas")],
    },
    {
        "locale": "pt", "path": "/transporte-cama-lisboa/",
        "title": "Transporte de cama e colchão em Lisboa — CargoPT",
        "description": "Peça propostas para transportar cama, estrado e colchão em Lisboa, indicando medidas, desmontagem, acessos e ajuda necessária.",
        "eyebrow": "Cama, estrado e colchão", "h1": "Transporte de cama em Lisboa",
        "intro": "Indique medidas, tipo de estrutura, desmontagem, elevadores e percurso até ao veículo. A CargoPT pode encaminhar o pedido para transportadores independentes adequados; propostas e disponibilidade não são garantidas.",
        "uses": [("Cama completa", "Estrutura, estrado, colchão, cabeceira e peças soltas devem aparecer separadamente no inventário."), ("Apenas colchão", "Informe largura, comprimento, espessura e se pode ser dobrado ou deve permanecer plano."), ("Com desmontagem", "Envie fotografias das uniões e confirme se ferramentas, desmontagem e montagem fazem parte da proposta.")],
        "inputs": ["Medidas da cama e do colchão.", "Fotografias da estrutura montada e dos acessos.", "Moradas, andares e dimensões dos elevadores.", "Se a cama já estará desmontada.", "Ajuda disponível na recolha e na entrega.", "Data, horário e limitações de estacionamento."],
        "checks": [("Desmontagem", "Confirme quem desmonta e monta e se ferragens e peças serão identificadas."), ("Proteção", "Acorde como colchão, cabeceira e cantos serão protegidos."), ("Percurso", "Valide escadas, elevador, corredores e distância até ao veículo."), ("Âmbito", "Confirme carga, descarga, ajudantes e materiais incluídos.")],
        "limits_text": "A CargoPT organiza o pedido e pode partilhá-lo com profissionais independentes. O transportador escolhido define o método, preço e condições; a CargoPT não garante que a cama passe pelos acessos nem que haja resposta.",
        "faq": [("É obrigatório desmontar a cama?", "Depende das dimensões e dos acessos. Envie fotografias e confirme a solução com o transportador."), ("O colchão pode ser dobrado?", "Nem todos podem. Siga as indicações do fabricante e informe o tipo de colchão."), ("A proposta inclui proteção?", "Só se estiver indicada. Confirme capa, mantas, película e proteção de cantos por escrito."), ("E se não houver elevador?", "Informe piso, escadas e curvas. Isso pode alterar equipa, tempo e equipamento necessários."), ("A CargoPT garante transportador?", "Não. A disponibilidade e as propostas dependem dos detalhes e dos profissionais disponíveis.")],
        "related": [("/transporte-moveis-lisboa/", "Transporte de móveis em Lisboa"), ("/servico-embalamento-desmontagem-montagem/", "Embalagem, desmontagem e montagem"), ("/#request", "Pedir propostas")],
    },
]


CLUSTERS = {
    "small": {
        "pt": {"path": "/mudancas-pequenas-lisboa/", "title": "Mudanças pequenas em Lisboa: poucos móveis e caixas — CargoPT", "description": "Peça propostas para uma pequena mudança em Lisboa com poucos móveis, caixas ou eletrodomésticos, indicando carga, acessos e ajuda.", "eyebrow": "Poucos objetos em Lisboa", "h1": "Mudanças pequenas em Lisboa", "intro": "Para transportar alguns móveis, caixas ou eletrodomésticos, descreva exatamente a carga e os acessos. A CargoPT pode encaminhar o pedido para transportadores independentes adequados; não garante disponibilidade nem propostas.", "uses": [("Quarto ou estúdio", "Caixas, cama, mesa e poucos móveis entre duas moradas."), ("Compra ou venda", "Recolha de um conjunto de móveis ou eletrodomésticos num local e entrega noutro."), ("Carga parcial", "Poucos volumes que não justificam uma mudança completa, mas exigem veículo e manuseamento adequados.")], "inputs": ["Lista e quantidade de cada objeto.", "Medidas e fotografias dos itens maiores.", "Origem, destino e data possível.", "Andares, elevadores, escadas e estacionamento.", "Ajuda disponível nos dois locais.", "Necessidade de desmontagem, proteção ou materiais."], "checks": [("Serviço mínimo", "Pergunte se existe valor mínimo ou tempo mínimo aplicável."), ("Ajuda", "Confirme quantas pessoas participam na carga e descarga."), ("Veículo", "Verifique espaço, fixação e proteção previstos."), ("Tudo incluído", "Compare deslocação, esperas, materiais e tarefas no mesmo âmbito.")], "limits": "Pedido pequeno não significa disponibilidade imediata nem preço fixo. Cada transportador avalia rota, carga, acessos e horário e decide se apresenta proposta.", "faq": [("O que conta como mudança pequena?", "Não há um limite universal. Em geral é uma carga curta e bem definida, como algumas caixas e poucos móveis."), ("Posso transportar apenas um eletrodoméstico?", "Sim. Indique modelo, dimensões, peso aproximado, posição de transporte e acessos."), ("Há preço fixo?", "Não. O valor depende de rota, tempo, ajudantes, acessos e tarefas."), ("Pode ser no próprio dia?", "Pode pedir, mas a disponibilidade não é garantida. Para prazos curtos, envie dados completos e alguma flexibilidade."), ("A CargoPT faz a mudança?", "Não. A CargoPT pode encaminhar o pedido para transportadores independentes.")]},
        "en": {"path": "/en/small-moves-lisbon/", "title": "Small moves in Lisbon: a few items or boxes — CargoPT", "description": "Request offers for a small move in Lisbon with a few items, boxes or appliances, including load, access and helper details.", "eyebrow": "A few items in Lisbon", "h1": "Small moves in Lisbon", "intro": "For a few pieces of furniture, boxes or appliances, describe the load and access precisely. CargoPT may forward the request to suitable independent carriers; availability and offers are not guaranteed.", "uses": [("Room or studio", "Boxes, a bed, a table and a few pieces between two addresses."), ("Purchase or sale", "Pickup of furniture or appliances from one address and delivery to another."), ("Partial load", "A defined group of items that still needs the right vehicle and handling.")], "inputs": ["List and quantity of every item.", "Measurements and photos of larger objects.", "Pickup, destination and possible date.", "Floors, lifts, stairs and parking.", "Help available at both addresses.", "Disassembly, protection or materials required."], "checks": [("Minimum service", "Ask whether a minimum charge or minimum time applies."), ("Helpers", "Confirm who loads and unloads and how many people are included."), ("Vehicle", "Confirm space, securing and protection for the stated load."), ("Full scope", "Compare travel, waiting, materials and tasks on the same basis.")], "limits": "A small request does not mean immediate availability or a fixed price. Each carrier evaluates the route, load, access and timing before deciding whether to offer.", "faq": [("What is a small move?", "There is no universal limit. It usually means a short, clearly listed load such as boxes and a few items."), ("Can I move only one appliance?", "Yes. Include its model, measurements, approximate weight, transport position and access."), ("Is there a fixed price?", "No. Route, time, helpers, access and tasks all affect an offer."), ("Can it happen today?", "You may request it, but availability is not guaranteed. Complete details and flexibility help evaluation."), ("Does CargoPT perform the move?", "No. CargoPT may forward the request to independent carriers.")]},
        "ru": {"path": "/ru/nebolshoy-pereezd-lissabon/", "title": "Небольшой переезд в Лиссабоне: вещи и коробки — CargoPT", "description": "Запросите предложения для небольшого переезда в Лиссабоне: перечислите вещи, адреса, доступ и нужную помощь.", "eyebrow": "Несколько вещей в Лиссабоне", "h1": "Небольшой переезд в Лиссабоне", "intro": "Если нужно перевезти несколько предметов, коробок или техники, точно опишите груз и доступ. CargoPT может передать заявку подходящим независимым перевозчикам; доступность и предложения не гарантированы.", "uses": [("Комната или студия", "Коробки, кровать, стол и несколько предметов между двумя адресами."), ("Покупка или продажа", "Забор мебели или техники по одному адресу и доставка по другому."), ("Частичный груз", "Небольшой список вещей, которому всё равно нужны подходящий автомобиль и аккуратная погрузка.")], "inputs": ["Список и количество всех предметов.", "Размеры и фотографии крупных вещей.", "Адреса и возможная дата.", "Этажи, лифты, лестницы и парковка.", "Помощь при погрузке и разгрузке.", "Разборка, защита и материалы."], "checks": [("Минимальный заказ", "Уточните минимальную стоимость или продолжительность работы."), ("Грузчики", "Зафиксируйте, кто грузит и разгружает и сколько человек включено."), ("Автомобиль", "Проверьте вместимость, крепление и защиту груза."), ("Полный объём", "Сравнивайте проезд, ожидание, материалы и работы на одинаковых условиях.")], "limits": "Небольшой объём не означает мгновенную доступность или фиксированную цену. Каждый перевозчик оценивает маршрут, груз, доступ и время и сам решает, делать ли предложение.", "faq": [("Что считается небольшим переездом?", "Единого лимита нет. Обычно это точный короткий список: коробки и несколько предметов."), ("Можно перевезти только одну вещь?", "Да. Укажите модель, размеры, примерный вес, положение при перевозке и доступ."), ("Есть фиксированная цена?", "Нет. На предложение влияют маршрут, время, грузчики, доступ и работы."), ("Можно заказать на сегодня?", "Запросить можно, но доступность не гарантирована. Полные данные и гибкость помогают оценке."), ("CargoPT выполняет перевозку?", "Нет. CargoPT может передать заявку независимым перевозчикам.")]},
    },
    "urgent": {
        "pt": {"path": "/transporte-urgente-portugal/", "title": "Transporte urgente em Portugal: pedido com prazo curto — CargoPT", "description": "Saiba como enviar um pedido urgente de transporte ou mudança em Portugal e que dados aumentam a possibilidade de avaliação rápida.", "eyebrow": "Prazo inferior a 72 horas", "h1": "Transporte urgente em Portugal", "intro": "A CargoPT inicia a procura automática também quando faltam menos de 72 horas, mas um prazo curto reduz as opções. A disponibilidade, as respostas e a execução no horário pretendido não são garantidas.", "uses": [("Mudança imprevista", "Data próxima com carga e acessos já conhecidos."), ("Recolha com prazo", "Objeto ou carga que tem de sair de um local numa janela definida."), ("Substituição urgente", "Eletrodoméstico, móvel ou material necessário noutro endereço com pouca antecedência.")], "inputs": ["Data, hora limite e flexibilidade real.", "Moradas completas e eventuais paragens.", "Lista, peso, dimensões e fotografias.", "Andares, elevadores e distância até ao veículo.", "Ajuda e equipamento necessários.", "Contacto que possa responder rapidamente."], "checks": [("Disponibilidade confirmada", "Uma resposta não basta: confirme data, hora e duração diretamente."), ("Preço completo", "Valide deslocação, urgência, ajudantes, equipamento e esperas."), ("Plano de acesso", "Confirme chaves, autorizações, estacionamento e pessoa presente."), ("Alterações", "Comunique imediatamente qualquer mudança na carga ou no horário.")], "limits": "CargoPT pode iniciar a procura automática, mas não reserva veículos nem garante resposta, preço ou chegada. Cada transportador decide se tem disponibilidade e apresenta as suas próprias condições.", "faq": [("O que é um pedido urgente?", "Na CargoPT, o aviso especial aplica-se quando faltam menos de 72 horas para a data pedida."), ("A procura é feita automaticamente?", "Sim, entre transportadores adequados, mas disponibilidade e propostas não são garantidas."), ("Como aumentar a possibilidade de resposta?", "Envie moradas, carga, fotografias, acessos, horário e contacto completos e indique flexibilidade real."), ("O preço é mais alto?", "Não existe regra fixa. Cada transportador avalia disponibilidade, rota, equipa e condições."), ("CargoPT garante chegada a uma hora?", "Não. Horário e execução devem ser confirmados diretamente com o transportador escolhido.")]},
        "en": {"path": "/en/urgent-transport-portugal/", "title": "Urgent transport in Portugal: short-notice requests — CargoPT", "description": "Learn how to submit an urgent moving or transport request in Portugal and which details help carriers assess it quickly.", "eyebrow": "Less than 72 hours", "h1": "Urgent transport in Portugal", "intro": "CargoPT also starts automatic matching when fewer than 72 hours remain, but short notice reduces the available options. Carrier availability, offers and performance at the requested time are not guaranteed.", "uses": [("Unexpected move", "A near date with a known load and access conditions."), ("Timed pickup", "An item or load that must leave a location within a defined window."), ("Urgent replacement", "An appliance, item or material needed at another address on short notice.")], "inputs": ["Date, hard deadline and real flexibility.", "Complete addresses and any stops.", "Item list, weight, measurements and photos.", "Floors, lifts and distance to the vehicle.", "Helpers and equipment required.", "A contact able to reply quickly."], "checks": [("Confirmed availability", "Confirm date, time and expected duration directly with the carrier."), ("Complete price", "Check travel, urgency, helpers, equipment and waiting time."), ("Access plan", "Confirm keys, permits, parking and who will be present."), ("Changes", "Report any load or timing change immediately.")], "limits": "CargoPT may start automatic matching, but it does not reserve vehicles or guarantee a reply, price or arrival. Each carrier decides whether it is available and sets its own terms.", "faq": [("What is an urgent request?", "CargoPT shows the special warning when fewer than 72 hours remain before the requested date."), ("Is matching still automatic?", "Yes, among suitable carriers, but availability and offers are not guaranteed."), ("How can I improve the chance of a reply?", "Provide complete addresses, load, photos, access, timing and contact details and state real flexibility."), ("Does urgent transport always cost more?", "There is no fixed rule. Each carrier evaluates availability, route, team and conditions."), ("Does CargoPT guarantee an arrival time?", "No. Timing and performance must be confirmed with the selected carrier.")]},
        "ru": {"path": "/ru/srochnaya-perevozka-portugaliya/", "title": "Срочная перевозка в Португалии: заявка на ближайшие дни — CargoPT", "description": "Как подать срочную заявку на перевозку или переезд в Португалии и какие данные нужны перевозчику для быстрой оценки.", "eyebrow": "До даты меньше 72 часов", "h1": "Срочная перевозка в Португалии", "intro": "CargoPT запускает автоматический поиск и когда до даты меньше 72 часов, но короткий срок уменьшает число вариантов. Доступность перевозчиков, предложения и выполнение к нужному времени не гарантированы.", "uses": [("Внеплановый переезд", "Близкая дата при уже известном составе груза и условиях доступа."), ("Забор к сроку", "Вещь или груз нужно вывезти из помещения в определённое окно."), ("Срочная доставка", "Техника, мебель или материалы нужны по другому адресу в ближайшее время.")], "inputs": ["Дата, крайнее время и реальная гибкость.", "Полные адреса и промежуточные точки.", "Список, вес, размеры и фотографии.", "Этажи, лифты и расстояние до автомобиля.", "Нужные грузчики и оборудование.", "Контакт, который быстро отвечает."], "checks": [("Подтверждённое время", "Согласуйте дату, время и длительность напрямую с перевозчиком."), ("Полная цена", "Уточните дорогу, срочность, грузчиков, оборудование и ожидание."), ("Доступ", "Проверьте ключи, разрешения, парковку и присутствующего человека."), ("Изменения", "Сразу сообщайте об изменении груза или времени.")], "limits": "CargoPT может запустить автоматический поиск, но не резервирует автомобили и не гарантирует ответ, цену или прибытие. Перевозчик сам решает, доступен ли он, и задаёт условия.", "faq": [("Что считается срочной заявкой?", "CargoPT показывает специальное предупреждение, если до запрошенной даты меньше 72 часов."), ("Поиск всё равно автоматический?", "Да, среди подходящих перевозчиков, но доступность и предложения не гарантированы."), ("Как повысить шанс ответа?", "Укажите полные адреса, груз, фотографии, доступ, время, контакт и реальную гибкость."), ("Срочная перевозка всегда дороже?", "Единого правила нет. Перевозчик оценивает доступность, маршрут, команду и условия."), ("CargoPT гарантирует прибытие ко времени?", "Нет. Время и выполнение нужно подтвердить с выбранным перевозчиком.")]},
    },
    "packing": {
        "pt": {"path": "/servico-embalamento-desmontagem-montagem/", "title": "Embalagem, desmontagem e montagem numa mudança — CargoPT", "description": "Saiba como pedir embalagem, desmontagem e montagem como parte de uma mudança e o que confirmar na proposta do transportador.", "eyebrow": "Serviços adicionais", "h1": "Embalagem, desmontagem e montagem",
        "intro": "Pode incluir estas tarefas no pedido de mudança. Alguns transportadores independentes indicam que as disponibilizam, mas deve confirmar materiais, peças, limites e preço na proposta; a CargoPT não garante a sua disponibilidade.", "uses": [("Embalagem completa", "Preparação de caixas e proteção de móveis antes da carga."), ("Móveis desmontáveis", "Desmontagem na origem e montagem no destino, com fotografias e instruções."), ("Proteção específica", "Mantas, película, cantos, caixas reforçadas ou materiais adequados a objetos frágeis.")], "inputs": ["Lista e fotografias dos móveis e objetos.", "Peças que precisam de desmontagem e montagem.", "Materiais existentes e materiais a fornecer.", "Acessos, andares e espaço de trabalho.", "Manuais ou ferragens especiais.", "Tarefas que ficam a cargo do cliente."], "checks": [("Materiais", "Confirme tipos, quantidades, fornecimento e destino dos materiais."), ("Peças", "Acorde identificação, acondicionamento de ferragens e instruções de montagem."), ("Limites", "Liste objetos não embalados, ligações técnicas e trabalhos excluídos."), ("Responsabilidade", "Registe estado, fotografias e procedimento para incidentes diretamente com o transportador.")], "limits": "Embalagem, desmontagem e montagem são opções de transportadores independentes, não serviços garantidos pela CargoPT. Confirme sempre o âmbito e as condições antes de escolher.", "faq": [("A embalagem está incluída na mudança?", "Não automaticamente. Deve aparecer de forma explícita na proposta."), ("Quem fornece caixas e película?", "Pode ser o cliente ou o transportador. Confirme materiais, quantidades e preço."), ("Todos os móveis podem ser desmontados?", "Não. Envie fotografias e instruções e confirme viabilidade e riscos."), ("A montagem inclui ligações elétricas ou água?", "Não presuma. Trabalhos técnicos devem ser identificados e confirmados separadamente."), ("A CargoPT garante este serviço?", "Não. Pode encaminhar o pedido para profissionais adequados, mas disponibilidade e propostas não são garantidas.")]},
        "en": {"path": "/en/packing-disassembly-assembly/", "title": "Packing, disassembly and assembly for a move — CargoPT", "description": "Learn how to request packing, furniture disassembly and assembly with a move and what to confirm in a carrier offer.", "eyebrow": "Additional services", "h1": "Packing, disassembly and assembly", "intro": "You may include these tasks in a moving request. Some independent carriers state that they provide them, but materials, parts, limits and price must be confirmed in the offer; CargoPT does not guarantee availability.", "uses": [("Full packing", "Preparing boxes and protecting furniture before loading."), ("Furniture", "Disassembly at pickup and assembly at destination, supported by photos and instructions."), ("Specific protection", "Blankets, wrap, corners, reinforced boxes or suitable materials for fragile objects.")], "inputs": ["List and photos of furniture and objects.", "Items requiring disassembly and assembly.", "Materials available and materials to supply.", "Access, floors and working space.", "Manuals or special fittings.", "Tasks the customer will perform."], "checks": [("Materials", "Confirm types, quantities, supply and disposal or return."), ("Parts", "Agree labelling, storage of fittings and assembly instructions."), ("Limits", "List unpacked objects, technical connections and excluded work."), ("Responsibility", "Record condition, photos and incident procedure with the carrier.")], "limits": "Packing, disassembly and assembly are options offered by independent carriers, not services guaranteed by CargoPT. Confirm the scope and conditions before choosing.", "faq": [("Is packing included in a move?", "Not automatically. It must be stated explicitly in the offer."), ("Who supplies boxes and wrap?", "Either the customer or the carrier may do so. Confirm materials, quantities and price."), ("Can all furniture be disassembled?", "No. Share photos and instructions and confirm feasibility and risks."), ("Does assembly include electrical or water connections?", "Do not assume so. Technical work must be identified and agreed separately."), ("Does CargoPT guarantee this service?", "No. It may forward the request to suitable professionals, but availability and offers are not guaranteed.")]},
        "ru": {"path": "/ru/upakovka-razborka-sborka/", "title": "Упаковка, разборка и сборка при переезде — CargoPT", "description": "Как запросить упаковку, разборку и сборку мебели вместе с переездом и что проверить в предложении перевозчика.", "eyebrow": "Дополнительные работы", "h1": "Упаковка, разборка и сборка", "intro": "Эти работы можно указать в заявке на переезд. Некоторые независимые перевозчики отмечают, что выполняют их, но материалы, детали, ограничения и цену нужно подтвердить в предложении; CargoPT не гарантирует доступность.", "uses": [("Полная упаковка", "Подготовка коробок и защита мебели до погрузки."), ("Разборная мебель", "Разборка по адресу отправления и сборка по адресу доставки с фотографиями и инструкциями."), ("Особая защита", "Одеяла, плёнка, уголки, усиленные коробки и материалы для хрупких вещей.")], "inputs": ["Список и фотографии мебели и вещей.", "Предметы, которые нужно разобрать и собрать.", "Имеющиеся и нужные материалы.", "Доступ, этажи и место для работы.", "Инструкции и особый крепёж.", "Работы, которые выполнит клиент."], "checks": [("Материалы", "Уточните виды, количество, поставку и дальнейшее обращение с материалами."), ("Детали", "Согласуйте маркировку, хранение крепежа и инструкции по сборке."), ("Ограничения", "Перечислите неупакованные вещи, технические подключения и исключённые работы."), ("Ответственность", "Зафиксируйте состояние, фотографии и порядок действий при инциденте.")], "limits": "Упаковка, разборка и сборка — возможные услуги независимых перевозчиков, а не гарантированная услуга CargoPT. До выбора подтвердите объём и условия.", "faq": [("Упаковка входит в переезд?", "Не автоматически. Она должна быть прямо указана в предложении."), ("Кто предоставляет коробки и плёнку?", "Клиент или перевозчик. Уточните материалы, количество и цену."), ("Любую мебель можно разобрать?", "Нет. Отправьте фотографии и инструкции и подтвердите возможность и риски."), ("Сборка включает подключение электричества или воды?", "Не предполагайте этого. Технические работы согласуются отдельно."), ("CargoPT гарантирует эту услугу?", "Нет. CargoPT может передать заявку подходящим специалистам, но доступность и предложения не гарантированы.")]},
    },
}


CLUSTER_RELATED = {
    "small": {
        "pt": [("/transporte-moveis-lisboa/", "Transporte de móveis em Lisboa"), ("/transporte-eletrodomesticos-lisboa/", "Transporte de eletrodomésticos em Lisboa")],
        "en": [("/en/guides/sofa-transport-lisbon/", "Sofa transport in Lisbon"), ("/en/guides/refrigerator-transport-lisbon/", "Refrigerator transport in Lisbon")],
        "ru": [("/ru/guides/perevozka-divana-lissabon/", "Перевозка дивана в Лиссабоне"), ("/ru/guides/perevozka-holodilnika-lissabon/", "Перевозка холодильника в Лиссабоне")],
    },
    "urgent": {
        "pt": [("/guias/planeamento/como-planear-uma-mudanca/", "Como planear uma mudança"), ("/guias/planeamento/quando-e-mais-barato-mudar/", "Como a data influencia uma mudança")],
        "en": [("/en/guides/complete-moving-checklist/", "Complete moving checklist"), ("/en/guides/when-is-it-cheaper-to-move/", "How timing affects a move")],
        "ru": [("/ru/guides/polnyy-cheklist-pereezda/", "Полный чек-лист переезда"), ("/ru/guides/kogda-deshevle-pereezzhat/", "Как дата влияет на переезд")],
    },
    "packing": {
        "pt": [("/guias/embalamento/como-embalar-louca/", "Como embalar louça"), ("/guias/embalamento/como-embalar-televisao/", "Como embalar uma televisão")],
        "en": [("/en/guides/how-to-pack-dishes-and-glasses/", "How to pack dishes and glasses"), ("/en/guides/how-to-pack-a-tv/", "How to pack a television")],
        "ru": [("/ru/guides/kak-upakovat-posudu-i-bokaly/", "Как упаковать посуду и бокалы"), ("/ru/guides/kak-upakovat-televizor/", "Как упаковать телевизор")],
    },
}


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_page(page: dict, alternates: dict[str, str] | None = None) -> str:
    locale = page["locale"]
    labels = LOCALES[locale]
    canonical = "https://cargopt.pt" + page["path"]
    alternates = alternates or {labels["lang"]: page["path"]}
    hreflang = "\n".join(
        f'  <link rel="alternate" hreflang="{lang}" href="https://cargopt.pt{path}">'
        for lang, path in alternates.items()
    )
    x_default = alternates.get("en", page["path"])
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in page["faq"]
        ],
    }
    service_schema = {
        "@context": "https://schema.org", "@type": "Service", "name": page["h1"],
        "serviceType": "Moving and transport request service", "areaServed": {"@type": "Country", "name": "Portugal"},
        "provider": {"@type": "Organization", "name": "CargoPT", "url": "https://cargopt.pt/"},
        "url": canonical, "description": page["description"],
    }
    locale_links = []
    for lang, path in alternates.items():
        code = {"pt-PT": "PT", "en": "EN", "ru": "RU"}.get(lang, lang.upper())
        current = ' aria-current="page"' if path == page["path"] else ""
        locale_links.append(f'<a href="{path}"{current}>{code}</a>')
    use_cards = "".join(f'<article class="card"><h3>{esc(h)}</h3><p>{esc(t)}</p></article>' for h, t in page["uses"])
    input_items = "".join(f"<li>{esc(item)}</li>" for item in page["inputs"])
    check_cards = "".join(f'<article class="card"><h3>{esc(h)}</h3><p>{esc(t)}</p></article>' for h, t in page["checks"])
    faqs = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in page["faq"])
    related = "".join(f'<a href="{href}">{esc(title)}</a>' for href, title in page["related"])
    footer = "".join(f'<a href="{href}">{esc(title)}</a>' for href, title in labels["footer"])
    return f'''<!doctype html>
<html lang="{labels["lang"]}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(page["title"])}</title>
  <meta name="description" content="{esc(page["description"])}">
  <link rel="canonical" href="{canonical}">
{hreflang}
  <link rel="alternate" hreflang="x-default" href="https://cargopt.pt{x_default}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="CargoPT">
  <meta property="og:title" content="{esc(page["title"])}">
  <meta property="og:description" content="{esc(page["description"])}">
  <meta property="og:url" content="{canonical}">
  <script type="application/ld+json">{json.dumps(service_schema, ensure_ascii=False, separators=(",", ":"))}</script>
  <script type="application/ld+json">{json.dumps(faq_schema, ensure_ascii=False, separators=(",", ":"))}</script>
  <link rel="stylesheet" href="/assets/css/design-system.css?v=tokens-v1">
  <link rel="stylesheet" href="/assets/css/components.css?v=reduced-motion-v2">
  <link rel="stylesheet" href="/assets/css/landing.css?v=reduced-motion-v2">
</head>
<body data-locale="{locale}">
  <header class="site-header">
    <a class="logo" href="{labels["home"]}" aria-label="CargoPT"><span class="logo-cargo">Cargo</span><span class="logo-pt">PT</span></a>
    <nav class="header-actions" aria-label="{esc(labels["nav"])}">
      <span class="locale-switcher"><button class="locale-current" type="button" aria-label="{esc(labels["choose"])}">{locale.upper()}</button><span class="locale-menu">{"".join(locale_links)}</span></span>
      <a class="button button-small button-carrier" href="{labels["request"]}">{esc(labels["request_label"])}</a>
    </nav>
  </header>
  <main>
    <section class="hero section hero-v2">
      <div class="hero-copy">
        <p class="eyebrow">{esc(page["eyebrow"])}</p>
        <h1>{esc(page["h1"])}</h1>
        <p class="hero-text">{esc(page["intro"])}</p>
        <p class="form-note">{esc(labels["updated"])}</p>
      </div>
      <div class="hero-workspace"><article class="request-form request-card"><p class="eyebrow">{esc(labels["start"])}</p><h2>{esc(labels["request_label"])}</h2><p class="form-intro">{esc(labels["details"])}</p><a class="button" href="{labels["request"]}">{esc(labels["open_form"])}</a></article></div>
    </section>
    <section class="section"><div class="section-heading"><p class="eyebrow">{esc(labels["how"])}</p><h2>{esc(page["h1"])}</h2></div><div class="cards three">{use_cards}</div></section>
    <section class="section"><div class="section-heading"><p class="eyebrow">{esc(labels["details"])}</p><h2>{esc(labels["details"])}</h2></div><div class="legal-summary"><ul>{input_items}</ul></div></section>
    <section class="section"><div class="section-heading"><p class="eyebrow">{esc(labels["offer"])}</p><h2>{esc(labels["offer"])}</h2></div><div class="cards">{check_cards}</div></section>
    <section class="section problem"><div class="section-heading"><p class="eyebrow">{esc(labels["limits"])}</p><h2>{esc(labels["limits"])}</h2></div><p class="wide-text">{esc(page["limits_text"])}</p></section>
    <section class="section faq"><div class="section-heading"><p class="eyebrow">FAQ</p><h2>{esc(labels["faq"])}</h2></div>{faqs}</section>
    <section class="section"><div class="section-heading"><p class="eyebrow">CargoPT</p><h2>{esc(labels["related"])}</h2></div><div class="guide-related-links">{related}</div></section>
    <section class="section final-cta"><h2>{esc(page["h1"])}</h2><p>{esc(page["intro"])}</p><a class="button" href="{labels["request"]}">{esc(labels["request_label"])}</a></section>
  </main>
  <footer class="site-footer"><div class="footer-brand"><strong class="footer-logo"><span class="logo-cargo">Cargo</span><span class="logo-pt">PT</span></strong></div><nav class="footer-links" aria-label="{esc(labels["legal"])}">{footer}<a href="mailto:hello@cargopt.pt">{esc(labels["contact"])}</a></nav></footer>
</body>
</html>
'''


def cluster_pages() -> list[dict]:
    output = []
    for cluster, translations in CLUSTERS.items():
        alternates = {LOCALES[key]["lang"]: value["path"] for key, value in translations.items()}
        for locale, payload in translations.items():
            output.append({
                "locale": locale,
                **payload,
                "limits_text": payload["limits"],
                "related": CLUSTER_RELATED[cluster][locale] + [(LOCALES[locale]["request"], LOCALES[locale]["request_label"])],
                "alternates": alternates,
            })
    return output


def main() -> None:
    pages = PAGES + cluster_pages()
    for page in pages:
        output = STATIC / page["path"].strip("/") / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(output, render_page(page, page.get("alternates")))
        print("SEO_SERVICE_PAGE_RENDERED", page["path"], output)


if __name__ == "__main__":
    main()
