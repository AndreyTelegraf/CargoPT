from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton
from aiogram.types import ReplyKeyboardMarkup


SUPPORTED_CARRIER_LOCALES = ("pt", "en", "ru")
LANGUAGE_LABELS = {
    "Português": "pt",
    "English": "en",
    "Русский": "ru",
}


TRANSLATIONS = {
    "pt": {
        "yes": "Sim",
        "no": "Não",
        "start": "Começar",
        "done": "Concluir",
        "allow_publication": "Autorizo a publicação",
        "submit_moderation": "Enviar para revisão",
        "restart": "Preencher novamente",
        "language_saved": "Idioma guardado.",
        "profile_not_found": "Perfil de transportador não encontrado.",
        "no_invitation": "Não tem um convite. Contacte o administrador da CargoPT.",
        "invalid_invitation": "O convite é inválido ou já foi utilizado.",
        "already_registered": "Já está registado como transportador da CargoPT. Para alterar ou repetir o questionário, contacte o administrador.",
        "welcome": (
            "Bem-vindo à CargoPT.\n\nFoi convidado como transportador.\n\n"
            "Empresa:\n{company_name}\n\nAgora precisa de preencher o questionário do transportador.\n\n"
            "Será necessário indicar:\n- nome para o cartão público\n- ano de início de atividade e logótipo\n"
            "- regiões de trabalho\n- veículos e características\n- serviços de montagem e embalagem\n"
            "- contactos\n\nO questionário tem 10 passos e demora normalmente 4–5 minutos.\n\n"
            "Prima «Começar»."
        ),
        "questionnaire_not_found": "Questionário do transportador não encontrado.",
        "public_name_prompt": "Indique o nome completo da empresa ou o nome público exatamente como deve aparecer aos clientes da CargoPT.",
        "public_name_invalid": "O nome deve ter entre 2 e 100 caracteres.",
        "experience_prompt": "Desde que ano trabalha no transporte de mercadorias?\n\nEnvie o ano com quatro dígitos, por exemplo: 2018.",
        "experience_invalid": "Envie um ano com quatro dígitos, entre 1950 e {current_year}.",
        "logo_prompt": "Envie o logótipo da empresa ou uma fotografia profissional.\n\nDe preferência, use uma imagem quadrada. Envie-a como foto ou ficheiro JPG, PNG ou WEBP.",
        "logo_invalid": "Envie uma imagem em formato JPG, PNG ou WEBP.",
        "logo_too_large": "A imagem não pode ter mais de 10 MB.",
        "logo_save_error": "Não foi possível guardar a imagem. Tente enviá-la novamente.",
        "consent_prompt": "Autoriza a CargoPT a apresentar o nome, a imagem, a experiência e as regiões de trabalho no seu cartão público de transportador?",
        "consent_invalid": "Para continuar, prima «Autorizo a publicação». Se não quiser publicar os dados, contacte o administrador da CargoPT.",
        "regions_short_prompt": "Selecione as regiões de trabalho e prima «Concluir».",
        "regions_step_prompt": "Passo 5 de 10. Regiões de trabalho.\n\nEm que regiões de Portugal trabalha?\n\nPode selecionar várias regiões. Quando terminar, prima «Concluir».",
        "regions_invalid": "Selecione uma região com os botões ou prima «Concluir».",
        "regions_required": "Selecione pelo menos uma região de trabalho.",
        "profile_updated": "Perfil atualizado. As novas informações serão usadas no cartão de transportador da CargoPT.",
        "vehicles_count_prompt": "Passo 6 de 10. Veículos.\n\nQuantos veículos tem a sua empresa?",
        "vehicle_type_step": "Passo 7 de 10. Veículo 1 de {count}.\n\nSelecione o tipo de veículo.",
        "vehicle_type_invalid": "Selecione o tipo de veículo com um dos botões.",
        "payload_prompt": "Veículo {index} de {total}.\n\nQual é a carga útil do veículo em kg?",
        "volume_prompt": "Qual é o volume da caixa de carga em m³?",
        "assembly_prompt": "Presta serviços de montagem e desmontagem de mobiliário?",
        "packing_prompt": "Presta serviços de embalagem e desembalagem da carga?",
        "tail_lift_prompt": "O veículo tem plataforma elevatória traseira?",
        "crane_prompt": "O veículo tem grua?",
        "crane_weight_prompt": "Qual é o peso máximo que a grua consegue levantar, em kg?",
        "crane_reach_prompt": "Qual é o alcance máximo da lança da grua, em metros?",
        "mobile_lift_prompt": "Tem elevador exterior para cargas através das janelas?",
        "mobile_lift_floor_prompt": "Até que piso chega o elevador exterior?",
        "mobile_lift_weight_prompt": "Qual é o peso máximo suportado pelo elevador exterior, em kg?",
        "loaders_prompt": "Passo 8 de 10. Equipa.\n\nQuantos ajudantes pode disponibilizar em simultâneo para um serviço?",
        "vehicle_saved": "Veículo {current} guardado.\n\nPasso 7 de 10. Veículo {next} de {total}.\n\nSelecione o tipo de veículo.",
        "phone_prompt": "Passo 9 de 10. Contactos.\n\nQual é o telefone de contacto da empresa?",
        "email_prompt": "Indique o email de contacto da empresa.",
        "email_invalid": "Indique um email válido da empresa.",
        "number_invalid": "Envie um número válido maior que zero.",
        "floor_invalid": "Envie um número de piso válido, igual ou superior a zero.",
        "yes_no_invalid": "Selecione «Sim» ou «Não».",
        "not_provided": "não indicado",
        "uploaded": "carregado",
        "not_uploaded": "não carregado",
        "publication_allowed": "autorizada",
        "publication_unconfirmed": "não confirmada",
        "review_title": "Confirme o questionário antes de o enviar para revisão.",
        "company": "Empresa",
        "public_name": "Nome no cartão",
        "experience_since": "No transporte desde",
        "logo": "Logótipo",
        "publication": "Publicação",
        "contact": "Contacto",
        "assembly": "Montagem/desmontagem de mobiliário",
        "packing": "Embalagem da carga",
        "regions": "Regiões de trabalho",
        "vehicle": "Veículo {index}",
        "type": "Tipo",
        "payload": "Carga útil",
        "volume": "Volume",
        "tail_lift": "Plataforma elevatória",
        "crane": "Grua",
        "mobile_lift": "Elevador exterior",
        "mobile_lift_floor": "Piso máximo do elevador exterior",
        "mobile_lift_weight": "Peso máximo do elevador exterior",
        "crane_weight": "Peso máximo da grua",
        "crane_reach": "Alcance da lança da grua",
        "max_loaders": "Máximo de ajudantes para o veículo",
        "phone": "Telefone",
        "email": "Email",
        "submit_hint": "Se estiver tudo correto, prima «Enviar para revisão».",
        "restart_intro": "Empresa:\n{company_name}\n\nVamos preencher novamente o questionário.\n\n{regions_prompt}",
        "submission_missing": "Questionário não encontrado. Contacte o administrador da CargoPT.",
        "submission_sent": "Questionário enviado para revisão.\n\nReceberá uma notificação após a análise. Dúvidas: @{admin_username}",
        "approved": "O seu questionário CargoPT foi aprovado.\n\nAgora participa na distribuição de serviços.\n\nQuando surgir um serviço adequado, o bot enviará uma proposta com as opções para aceitar ou recusar.\n\nDúvidas: @{admin_username}",
        "rejected": "O seu questionário CargoPT não foi aprovado.\n\nPara esclarecer os detalhes, contacte o administrador:\n@{admin_username}",
        "status_pending": "Já está registado como transportador da CargoPT.\n\nO seu questionário foi enviado para revisão.\n\nApós a análise, o administrador entrará em contacto.",
        "status_active": "Está registado como transportador ativo da CargoPT.\n\nComo funciona:\n- quando surgir um serviço adequado, o bot enviará uma proposta;\n- poderá aceitar ou recusar a proposta;\n- depois de aceitar, o cliente confirma a atribuição.\n\nNeste momento não precisa de preencher nada. Aguarde novos serviços.",
        "status_completed": "O seu questionário de transportador já está preenchido.\n\nPara alterar alguma informação, contacte o administrador da CargoPT.",
        "status_bound": "Já está associado à CargoPT como transportador.\n\nPara criar um pedido de transporte como cliente, use /new_job.",
    },
    "en": {
        "yes": "Yes", "no": "No", "start": "Start", "done": "Done",
        "allow_publication": "I consent to publication", "submit_moderation": "Submit for review", "restart": "Fill in again",
        "language_saved": "Language saved.", "profile_not_found": "Carrier profile not found.",
        "no_invitation": "You do not have an invitation. Contact the CargoPT administrator.",
        "invalid_invitation": "This invitation is invalid or has already been used.",
        "already_registered": "You are already registered as a CargoPT carrier. To change or repeat the questionnaire, contact the administrator.",
        "welcome": "Welcome to CargoPT.\n\nYou have been invited as a carrier.\n\nCompany:\n{company_name}\n\nYou now need to complete the carrier questionnaire.\n\nYou will be asked for:\n- the name shown on your public card\n- your starting year and logo\n- operating regions\n- vehicles and specifications\n- assembly and packing services\n- contact details\n\nThe questionnaire has 10 steps and usually takes 4–5 minutes.\n\nPress “Start”.",
        "questionnaire_not_found": "Carrier questionnaire not found.",
        "public_name_prompt": "Enter the full company name or public name exactly as CargoPT customers should see it.",
        "public_name_invalid": "The name must contain between 2 and 100 characters.",
        "experience_prompt": "What year did you start working in freight transport?\n\nSend a four-digit year, for example: 2018.",
        "experience_invalid": "Send a four-digit year between 1950 and {current_year}.",
        "logo_prompt": "Send your company logo or a professional photo.\n\nA square image works best. Send it as a photo or a JPG, PNG, or WEBP file.",
        "logo_invalid": "Send an image in JPG, PNG, or WEBP format.", "logo_too_large": "The image must be no larger than 10 MB.",
        "logo_save_error": "The image could not be saved. Please send it again.",
        "consent_prompt": "Do you allow CargoPT to show your name, image, experience, and operating regions on your public carrier card?",
        "consent_invalid": "To continue, press “I consent to publication”. If you do not want your data published, contact the CargoPT administrator.",
        "regions_short_prompt": "Select your operating regions and press “Done”.",
        "regions_step_prompt": "Step 5 of 10. Operating regions.\n\nWhich regions of Portugal do you cover?\n\nYou can select several regions. When finished, press “Done”.",
        "regions_invalid": "Select a region with a button or press “Done”.", "regions_required": "Select at least one operating region.",
        "profile_updated": "Profile updated. The new information will be used on your CargoPT carrier card.",
        "vehicles_count_prompt": "Step 6 of 10. Vehicles.\n\nHow many vehicles does your company have?",
        "vehicle_type_step": "Step 7 of 10. Vehicle 1 of {count}.\n\nSelect the vehicle type.", "vehicle_type_invalid": "Select the vehicle type using a button.",
        "payload_prompt": "Vehicle {index} of {total}.\n\nWhat is the vehicle payload in kg?", "volume_prompt": "What is the cargo body volume in m³?",
        "assembly_prompt": "Do you provide furniture assembly and disassembly services?", "packing_prompt": "Do you provide cargo packing and unpacking services?",
        "tail_lift_prompt": "Does the vehicle have a tail lift?", "crane_prompt": "Does the vehicle have a crane?",
        "crane_weight_prompt": "What is the maximum weight the crane can lift, in kg?", "crane_reach_prompt": "What is the maximum crane boom reach, in metres?",
        "mobile_lift_prompt": "Do you have an exterior furniture lift for access through windows?", "mobile_lift_floor_prompt": "What is the highest floor the exterior lift can reach?",
        "mobile_lift_weight_prompt": "What is the maximum weight the exterior lift can carry, in kg?", "loaders_prompt": "Step 8 of 10. Team.\n\nHow many helpers can you provide at the same time for one job?",
        "vehicle_saved": "Vehicle {current} saved.\n\nStep 7 of 10. Vehicle {next} of {total}.\n\nSelect the vehicle type.",
        "phone_prompt": "Step 9 of 10. Contacts.\n\nWhat is your company contact phone number?", "email_prompt": "Enter the company contact email.",
        "email_invalid": "Enter a valid company email.", "number_invalid": "Send a valid number greater than zero.",
        "floor_invalid": "Send a valid floor number of zero or greater.", "yes_no_invalid": "Select “Yes” or “No”.",
        "not_provided": "not provided", "uploaded": "uploaded", "not_uploaded": "not uploaded", "publication_allowed": "allowed", "publication_unconfirmed": "not confirmed",
        "review_title": "Check the carrier questionnaire before submitting it for review.", "company": "Company", "public_name": "Name on card",
        "experience_since": "In transport since", "logo": "Logo", "publication": "Publication", "contact": "Contact",
        "assembly": "Furniture assembly/disassembly", "packing": "Cargo packing", "regions": "Operating regions", "vehicle": "Vehicle {index}",
        "type": "Type", "payload": "Payload", "volume": "Volume", "tail_lift": "Tail lift", "crane": "Crane", "mobile_lift": "Exterior lift",
        "mobile_lift_floor": "Exterior lift maximum floor", "mobile_lift_weight": "Exterior lift maximum weight", "crane_weight": "Crane maximum weight",
        "crane_reach": "Crane boom reach", "max_loaders": "Maximum helpers for vehicle", "phone": "Phone", "email": "Email",
        "submit_hint": "If everything is correct, press “Submit for review”.",
        "restart_intro": "Company:\n{company_name}\n\nLet’s fill in the questionnaire again.\n\n{regions_prompt}",
        "submission_missing": "Questionnaire not found. Contact the CargoPT administrator.",
        "submission_sent": "Questionnaire submitted for review.\n\nYou will receive a notification after it is checked. Questions: @{admin_username}",
        "approved": "Your CargoPT questionnaire has been approved.\n\nYou can now receive jobs.\n\nWhen a suitable job appears, the bot will send you an offer with options to accept or decline.\n\nQuestions: @{admin_username}",
        "rejected": "Your CargoPT questionnaire was not approved.\n\nTo clarify the details, contact the administrator:\n@{admin_username}",
        "status_pending": "You are already registered as a CargoPT carrier.\n\nYour questionnaire has been submitted for review.\n\nThe administrator will contact you after it is checked.",
        "status_active": "You are registered as an active CargoPT carrier.\n\nHow it works:\n- when a suitable job appears, the bot sends you an offer;\n- you can accept or decline it;\n- after acceptance, the customer confirms the assignment.\n\nYou do not need to fill in anything now. Wait for new jobs.",
        "status_completed": "Your carrier questionnaire is already complete.\n\nContact the CargoPT administrator if anything needs to be changed.",
        "status_bound": "You are already linked to CargoPT as a carrier.\n\nTo create a transport request as a customer, use /new_job.",
    },
    "ru": {
        "yes": "Да", "no": "Нет", "start": "Начать", "done": "Готово", "allow_publication": "Разрешаю публикацию",
        "submit_moderation": "Отправить на модерацию", "restart": "Заполнить заново", "language_saved": "Язык сохранён.",
        "profile_not_found": "Профиль перевозчика не найден.", "no_invitation": "У вас нет приглашения. Обратитесь к администратору CargoPT.",
        "invalid_invitation": "Приглашение недействительно или уже использовано.",
        "already_registered": "Вы уже зарегистрированы как перевозчик CargoPT. Если нужно изменить анкету или пройти её заново, свяжитесь с администратором.",
        "welcome": "Добро пожаловать в CargoPT.\n\nВы были приглашены как перевозчик.\n\nКомпания:\n{company_name}\n\nСейчас нужно заполнить анкету перевозчика.\n\nЧто потребуется:\n- название для публичной карточки\n- год начала работы и логотип\n- регионы работы\n- автомобили и их характеристики\n- услуги сборки и упаковки\n- контактные данные\n\nАнкета состоит из 10 шагов и обычно занимает 4–5 минут.\n\nНажмите «Начать».",
        "questionnaire_not_found": "Анкета перевозчика не найдена.", "public_name_prompt": "Укажите полное название компании или публичное имя — точно так, как его должны видеть клиенты CargoPT.",
        "public_name_invalid": "Название должно содержать от 2 до 100 символов.", "experience_prompt": "С какого года вы занимаетесь грузовыми перевозками?\n\nОтправьте год четырьмя цифрами, например: 2018.",
        "experience_invalid": "Отправьте год четырьмя цифрами — от 1950 до {current_year}.",
        "logo_prompt": "Пришлите логотип компании или рабочее фото.\n\nЛучше использовать квадратное изображение. Отправьте его как фото или как файл JPG, PNG либо WEBP.",
        "logo_invalid": "Пришлите изображение в формате JPG, PNG или WEBP.", "logo_too_large": "Изображение должно быть не больше 10 МБ.",
        "logo_save_error": "Не удалось сохранить изображение. Попробуйте отправить его ещё раз.",
        "consent_prompt": "Разрешаете CargoPT показывать название, изображение, стаж и регионы работы в вашей публичной карточке перевозчика?",
        "consent_invalid": "Для продолжения нажмите «Разрешаю публикацию». Если вы не хотите публиковать данные, свяжитесь с администратором CargoPT.",
        "regions_short_prompt": "Выберите регионы работы и нажмите «Готово».",
        "regions_step_prompt": "Шаг 5 из 10. Регионы работы.\n\nВ каких регионах Португалии вы работаете?\n\nМожно выбрать несколько регионов. Когда закончите, нажмите «Готово».",
        "regions_invalid": "Выберите регион кнопкой или нажмите «Готово».", "regions_required": "Выберите хотя бы один регион работы.",
        "profile_updated": "Профиль дополнен. Новые сведения будут использоваться в карточке перевозчика CargoPT.",
        "vehicles_count_prompt": "Шаг 6 из 10. Автомобили.\n\nСколько автомобилей у вашей компании?",
        "vehicle_type_step": "Шаг 7 из 10. Автомобиль 1 из {count}.\n\nВыберите тип автомобиля.", "vehicle_type_invalid": "Выберите тип автомобиля кнопкой.",
        "payload_prompt": "Автомобиль {index} из {total}.\n\nГрузоподъёмность автомобиля в кг?", "volume_prompt": "Объём кузова в м³?",
        "assembly_prompt": "Предоставляете ли вы услуги сборки и разборки мебели?", "packing_prompt": "Предоставляете ли вы услуги упаковки и распаковки груза?",
        "tail_lift_prompt": "Есть ли гидроборт?", "crane_prompt": "Есть ли кран?", "crane_weight_prompt": "Какой максимальный вес может поднять кран в кг?",
        "crane_reach_prompt": "Какой максимальный вылет стрелы крана в метрах?", "mobile_lift_prompt": "Есть ли мобильный лифт для подачи через окна?",
        "mobile_lift_floor_prompt": "На какой максимальный этаж может подавать мобильный лифт?", "mobile_lift_weight_prompt": "Какой максимальный вес может поднять мобильный лифт в кг?",
        "loaders_prompt": "Шаг 8 из 10. Команда.\n\nСколько грузчиков одновременно вы можете предоставить на один заказ?",
        "vehicle_saved": "Автомобиль {current} сохранён.\n\nШаг 7 из 10. Автомобиль {next} из {total}.\n\nВыберите тип автомобиля.",
        "phone_prompt": "Шаг 9 из 10. Контакты.\n\nКакой номер телефона для связи с вашей компанией?", "email_prompt": "Укажите контактный email компании.",
        "email_invalid": "Укажите корректный email компании.", "number_invalid": "Отправьте корректное число больше нуля.",
        "floor_invalid": "Отправьте корректный номер этажа — ноль или больше.", "yes_no_invalid": "Выберите «Да» или «Нет».",
        "not_provided": "не указано", "uploaded": "загружен", "not_uploaded": "не загружен", "publication_allowed": "разрешена", "publication_unconfirmed": "не подтверждена",
        "review_title": "Проверьте анкету перевозчика перед отправкой на модерацию.", "company": "Компания", "public_name": "Название в карточке",
        "experience_since": "В перевозках с", "logo": "Логотип", "publication": "Публикация", "contact": "Контакт",
        "assembly": "Сборка/разборка мебели", "packing": "Упаковка груза", "regions": "Регионы работы", "vehicle": "Автомобиль {index}",
        "type": "Тип", "payload": "Грузоподъёмность", "volume": "Объём", "tail_lift": "Гидроборт", "crane": "Кран", "mobile_lift": "Мобильный лифт",
        "mobile_lift_floor": "Макс. этаж мобильного лифта", "mobile_lift_weight": "Макс. вес мобильного лифта", "crane_weight": "Макс. вес крана",
        "crane_reach": "Вылет стрелы крана", "max_loaders": "Макс. грузчиков для автомобиля", "phone": "Телефон", "email": "Email",
        "submit_hint": "Если всё верно, нажмите «Отправить на модерацию».",
        "restart_intro": "Компания:\n{company_name}\n\nЗаполним анкету заново.\n\n{regions_prompt}",
        "submission_missing": "Анкета не найдена. Обратитесь к администратору CargoPT.",
        "submission_sent": "Анкета отправлена на модерацию.\n\nПосле проверки вы получите уведомление. По вопросам: @{admin_username}",
        "approved": "Ваша анкета CargoPT одобрена.\n\nТеперь вы участвуете в распределении заказов.\n\nКогда появится подходящий заказ, бот пришлёт вам предложение с кнопками принятия или отказа.\n\nПо вопросам: @{admin_username}",
        "rejected": "Ваша анкета CargoPT не была одобрена.\n\nДля уточнения деталей свяжитесь с администратором:\n@{admin_username}",
        "status_pending": "Вы уже зарегистрированы как перевозчик CargoPT.\n\nВаша анкета отправлена на проверку.\n\nКогда она будет обработана, администратор свяжется с вами.",
        "status_active": "Вы зарегистрированы как активный перевозчик CargoPT.\n\nКак это работает:\n- когда появится подходящий заказ, бот пришлёт вам предложение;\n- предложение можно принять или отклонить;\n- после принятия клиент должен подтвердить назначение.\n\nСейчас ничего заполнять не нужно. Ожидайте новых заказов.",
        "status_completed": "Ваша анкета перевозчика уже заполнена.\n\nЕсли нужно что-то изменить, свяжитесь с администратором CargoPT.",
        "status_bound": "Вы уже привязаны к CargoPT как перевозчик.\n\nЕсли нужно создать клиентскую заявку на перевозку, используйте команду /new_job.",
    },
}


def normalize_carrier_locale(value: str | None, *, fallback: str = "ru") -> str:
    normalized = (value or "").strip().lower().replace("_", "-")
    prefix = normalized.split("-", 1)[0]
    return prefix if prefix in SUPPORTED_CARRIER_LOCALES else fallback


def locale_from_language_button(value: str | None) -> str | None:
    return LANGUAGE_LABELS.get((value or "").strip())


def text(locale: str | None, key: str, **values) -> str:
    language = normalize_carrier_locale(locale)
    return TRANSLATIONS[language][key].format(**values)


async def get_carrier_locale(state: FSMContext) -> str:
    data = await state.get_data()
    return normalize_carrier_locale(data.get("carrier_locale"))


def language_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Português"), KeyboardButton(text="English")],
            [KeyboardButton(text="Русский")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def single_button_keyboard(locale: str, key: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text(locale, key))]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def yes_no_keyboard(locale: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=text(locale, "yes")), KeyboardButton(text=text(locale, "no"))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def parse_yes_no(value: str | None, locale: str) -> bool | None:
    cleaned = (value or "").strip()
    if cleaned == text(locale, "yes"):
        return True
    if cleaned == text(locale, "no"):
        return False
    return None
