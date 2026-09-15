const TRACKING_LINKS_KEY = "cargopt_tracking_links";
const ACTIVE_SUBMISSION_KEY = "cargopt_active_submission_v1";
const LANDING_VERSION = "landing_static_v3_acquisition";
const ACQUISITION_EVENT_ENDPOINT = "/api/v1/acquisition-events";
const pageLocale = document.body.dataset.locale || document.documentElement.lang || "ru";
const form = document.querySelector("#requestForm");
const hero = document.querySelector(".hero");
const steps = Array.from(document.querySelectorAll(".form-step"));
const stepLabel = document.querySelector("#stepLabel");
const progressFill = document.querySelector("#progressFill");
const formMessage = document.querySelector("#formMessage");
const progress = document.querySelector(".progress");
let currentStep = 1;
const sentAcquisitionEvents = new Set();
let activeSubmission = loadActiveSubmission();

const MESSAGES = {
  pt: {
    required: "Preencha os campos obrigatórios para continuar.",
    contact: "Indique pelo menos um contacto: telefone, WhatsApp ou email.",
    submitting: "A enviar o pedido...",
    success: "Pedido enviado. Vamos encaminhá-lo para transportadores.",
    validationFailure: "Alguns dados do pedido não são válidos. Verifique os campos e tente novamente.",
    validationFieldFailure: "Verifique estes campos: {fields}.",
    requestedDatePast: "A data do transporte não pode estar no passado.",
    requestedTimeRequired: "Indique a hora do transporte em Portugal.",
    leadTimeAutomatic: "Faltam pelo menos 72 horas. Depois do envio, o pedido entra na procura automática de transportadores adequados; propostas e disponibilidade não são garantidas.",
    leadTimeUrgent: "Faltam menos de 72 horas. A CargoPT irá, ainda assim, iniciar a procura automática entre transportadores adequados. Por ser um pedido urgente, a disponibilidade e as propostas não são garantidas.",
    leadTimeFlexible: "Sem uma data e hora exatas, o pedido será guardado para análise manual pela CargoPT. Entraremos em contacto através dos dados indicados.",
    conflictFailure: "Este pedido já foi alterado ou enviado. Atualize a página antes de tentar novamente.",
    rateLimitFailure: "Foram enviados demasiados pedidos. Aguarde um pouco e tente novamente.",
    serverFailure: "Ocorreu um erro no servidor. Os dados introduzidos foram mantidos; tente novamente.",
    timeoutFailure: "O envio demorou demasiado tempo. Verifique a ligação e tente novamente.",
    networkFailure: "Não foi possível ligar ao servidor. Verifique a ligação à internet e tente novamente.",
    unexpectedFailure: "Não foi possível enviar o pedido. Os dados introduzidos foram mantidos.",
    viewStatus: "Ver estado",
    newRequest: "← Novo pedido",
    statusNoOffers: "Sem propostas disponíveis",
    statusAwaitingConfirmation: "A aguardar confirmação do transportador",
    statusCarrierConfirmed: "Transportador confirmado",
    offersAvailable: "{count} proposta(s) disponível(eis)",
    defaultRoute: "Pedido CargoPT",
    waitingOffers: "A aguardar propostas",
    trackingEyebrow: "Estado do pedido",
    detailsTitle: "Detalhes do pedido",
    itemsLabel: "Itens",
    commentLabel: "Comentário",
    openRequestsShort: "Pedidos",
    openRequestsLong: "Meus pedidos",
    locationLoading: "A procurar locais...",
    locationNoResults: "Nenhum local encontrado. Acrescente a cidade, a rua e o país.",
    locationSearchFailure: "Não foi possível procurar locais agora. Tente novamente.",
    locationManualHelp: "Se a pesquisa continuar indisponível, envie os dois endereços para revisão manual.",
    locationManualContact: "Pedir ajuda por email",
    locationSelectRequired: "Escolha um local específico da lista.",
    locationConfirmRequired: "Confirme que o ponto selecionado está correto."
  },
  en: {
    required: "Fill in the required fields to continue.",
    contact: "Add at least one contact: phone, WhatsApp or email.",
    submitting: "Sending request...",
    success: "Request sent. We will forward it to carriers.",
    validationFailure: "Some request details are invalid. Check the fields and try again.",
    validationFieldFailure: "Check these fields: {fields}.",
    requestedDatePast: "The moving date cannot be in the past.",
    requestedTimeRequired: "Add the moving time in Portugal.",
    leadTimeAutomatic: "The move is at least 72 hours away. After submission, the request enters automatic matching with suitable carriers; offers and availability are not guaranteed.",
    leadTimeUrgent: "The move is less than 72 hours away. CargoPT will still start the automatic search among suitable carriers. Because the request is urgent, carrier availability and offers are not guaranteed.",
    leadTimeFlexible: "Without an exact date and time, CargoPT will save the request for manual review. We will contact you using the details provided.",
    conflictFailure: "This request has already been changed or submitted. Refresh the page before trying again.",
    rateLimitFailure: "Too many requests were submitted. Wait a moment and try again.",
    serverFailure: "A server error occurred. Your entered data was kept; try again.",
    timeoutFailure: "The request took too long to send. Check your connection and try again.",
    networkFailure: "Could not connect to the server. Check your internet connection and try again.",
    unexpectedFailure: "Could not send the request. Your entered data was kept.",
    viewStatus: "View status",
    newRequest: "← New request",
    statusNoOffers: "No offers available",
    statusAwaitingConfirmation: "Waiting for carrier confirmation",
    statusCarrierConfirmed: "Carrier confirmed",
    offersAvailable: "{count} offer(s) available",
    defaultRoute: "CargoPT request",
    waitingOffers: "Waiting for offers",
    trackingEyebrow: "Request status",
    detailsTitle: "Request details",
    itemsLabel: "Items",
    commentLabel: "Comment",
    openRequestsShort: "Requests",
    openRequestsLong: "My requests",
    locationLoading: "Searching for places...",
    locationNoResults: "No place found. Add the city, street and country.",
    locationSearchFailure: "Places could not be searched right now. Try again.",
    locationManualHelp: "If search remains unavailable, send both addresses for manual review.",
    locationManualContact: "Ask for help by email",
    locationSelectRequired: "Select a specific place from the list.",
    locationConfirmRequired: "Confirm that the selected point is correct."
  },
  ru: {
    required: "Заполните обязательные поля, чтобы продолжить.",
    contact: "Укажите хотя бы один контакт: телефон, WhatsApp или email.",
    submitting: "Отправляем заявку...",
    success: "Заявка отправлена. Мы передадим её перевозчикам.",
    validationFailure: "Некоторые данные заявки заполнены неверно. Проверьте поля и отправьте ещё раз.",
    validationFieldFailure: "Проверьте поля: {fields}.",
    requestedDatePast: "Дата перевозки не может быть в прошлом.",
    requestedTimeRequired: "Укажите время перевозки по Португалии.",
    leadTimeAutomatic: "До перевозки не менее 72 часов. После отправки заявка попадёт в автоматический подбор подходящих перевозчиков; предложения и доступность не гарантируются.",
    leadTimeUrgent: "До перевозки меньше 72 часов. CargoPT всё равно запустит автоматический поиск среди подходящих перевозчиков. Из-за срочности доступность перевозчиков и предложения не гарантируются.",
    leadTimeFlexible: "Без точной даты и времени CargoPT сохранит заявку для ручной проверки. Мы свяжемся по указанным контактам.",
    conflictFailure: "Эта заявка уже была изменена или отправлена. Обновите страницу перед повторной попыткой.",
    rateLimitFailure: "Отправлено слишком много заявок. Подождите немного и попробуйте снова.",
    serverFailure: "На сервере произошла ошибка. Введённые данные сохранены; попробуйте отправить ещё раз.",
    timeoutFailure: "Сервер слишком долго не отвечал. Проверьте соединение и попробуйте снова.",
    networkFailure: "Не удалось соединиться с сервером. Проверьте интернет и попробуйте снова.",
    unexpectedFailure: "Не удалось отправить заявку. Введённые данные сохранены.",
    viewStatus: "Статус заявки",
    newRequest: "← Новая заявка",
    statusNoOffers: "Нет доступных предложений",
    statusAwaitingConfirmation: "Ожидаем подтверждение перевозчика",
    statusCarrierConfirmed: "Перевозчик подтверждён",
    offersAvailable: "Доступно предложений: {count}",
    defaultRoute: "Заявка CargoPT",
    waitingOffers: "Ожидаем предложения",
    trackingEyebrow: "Статус заявки",
    detailsTitle: "Детали заявки",
    itemsLabel: "Груз",
    commentLabel: "Комментарий",
    openRequestsShort: "Заявки",
    openRequestsLong: "Мои заявки",
    locationLoading: "Ищем места...",
    locationNoResults: "Место не найдено. Добавьте город, улицу и страну.",
    locationSearchFailure: "Сейчас не удалось найти места. Попробуйте ещё раз.",
    locationManualHelp: "Если поиск остаётся недоступен, отправьте оба адреса на ручную проверку.",
    locationManualContact: "Запросить помощь по email",
    locationSelectRequired: "Выберите конкретное место из списка.",
    locationConfirmRequired: "Подтвердите, что выбранная точка правильная."
  }
};

const localeKey = pageLocale === "pt-PT" ? "pt" : pageLocale.slice(0, 2);
const messages = MESSAGES[localeKey] || MESSAGES.pt;
const localizedHomePath = {
  en: "/en/",
  ru: "/ru/",
}[localeKey] || "/";
const locationFieldStates = new Map();

const VALIDATION_FIELD_LABELS = {
  pt: {
    request: "dados do pedido",
    pickup: "local de recolha",
    dropoff: "local de entrega",
    items: "bens a transportar",
    customer_name: "nome",
    requested_date: "data",
    contact: "contacto",
    client_phone: "telefone",
    client_whatsapp: "WhatsApp",
    customer_email: "email",
    pickup_floor: "piso de recolha",
    pickup_elevator: "elevador na recolha",
    dropoff_floor: "piso de entrega",
    dropoff_elevator: "elevador na entrega",
    required_loaders: "ajudantes",
    estimated_volume_m3: "volume",
    comment: "comentário",
    unknown: "dados do pedido"
  },
  en: {
    request: "request details",
    pickup: "pickup location",
    dropoff: "delivery location",
    items: "items being moved",
    customer_name: "name",
    requested_date: "moving date",
    contact: "contact",
    client_phone: "phone",
    client_whatsapp: "WhatsApp",
    customer_email: "email",
    pickup_floor: "pickup floor",
    pickup_elevator: "pickup elevator",
    dropoff_floor: "delivery floor",
    dropoff_elevator: "delivery elevator",
    required_loaders: "movers",
    estimated_volume_m3: "volume",
    comment: "comment",
    unknown: "request details"
  },
  ru: {
    request: "данные заявки",
    pickup: "место отправления",
    dropoff: "место доставки",
    items: "описание груза",
    customer_name: "имя",
    requested_date: "дата перевозки",
    contact: "контакт",
    client_phone: "телефон",
    client_whatsapp: "WhatsApp",
    customer_email: "email",
    pickup_floor: "этаж отправления",
    pickup_elevator: "лифт на отправлении",
    dropoff_floor: "этаж доставки",
    dropoff_elevator: "лифт на доставке",
    required_loaders: "грузчики",
    estimated_volume_m3: "объём",
    comment: "комментарий",
    unknown: "данные заявки"
  }
};
const validationFieldLabels = VALIDATION_FIELD_LABELS[localeKey]
  || VALIDATION_FIELD_LABELS.pt;

function limitedAttributionValue(value, maxLength) {
  return (value || "").trim().slice(0, maxLength) || null;
}

function currentReferrerHost() {
  if (!document.referrer) return null;
  try {
    const host = new URL(document.referrer).hostname.toLowerCase();
    return host.endsWith("cargopt.pt") ? null : limitedAttributionValue(host, 255);
  } catch {
    return null;
  }
}

function captureFirstTouchAttribution() {
  const params = new URLSearchParams(window.location.search);
  const current = {
    utm_source: limitedAttributionValue(params.get("utm_source"), 255),
    utm_medium: limitedAttributionValue(params.get("utm_medium"), 255),
    utm_campaign: limitedAttributionValue(params.get("utm_campaign"), 255),
    utm_content: limitedAttributionValue(params.get("utm_content"), 255),
    referrer_host: limitedAttributionValue(params.get("referrer_host"), 255)
      || currentReferrerHost(),
    fbclid: limitedAttributionValue(params.get("fbclid"), 1024)
  };

  return current;
}

const firstTouchAttribution = captureFirstTouchAttribution();

function preserveAttributionOnLocaleLinks() {
  document.querySelectorAll(".locale-switcher a").forEach((link) => {
    const target = new URL(link.href, window.location.origin);
    for (const key of [
      "utm_source",
      "utm_medium",
      "utm_campaign",
      "utm_content",
      "referrer_host",
      "fbclid"
    ]) {
      const value = firstTouchAttribution[key];
      if (value) target.searchParams.set(key, value);
    }
    link.href = `${target.pathname}${target.search}${target.hash}`;
  });
}

function acquisitionEventPayload(eventType, errorCategory = "") {
  return {
    event_type: eventType,
    source_locale: localeKey,
    utm_source: firstTouchAttribution.utm_source
      || (firstTouchAttribution.fbclid ? "facebook" : null),
    utm_medium: firstTouchAttribution.utm_medium,
    utm_campaign: firstTouchAttribution.utm_campaign,
    utm_content: firstTouchAttribution.utm_content,
    referrer_host: firstTouchAttribution.referrer_host,
    landing_version: LANDING_VERSION,
    error_category: errorCategory
  };
}

function recordAcquisitionEvent(eventType, errorCategory = "") {
  const dedupeKey = `${eventType}:${errorCategory}`;
  if (sentAcquisitionEvents.has(dedupeKey)) return;
  sentAcquisitionEvents.add(dedupeKey);

  fetch(ACQUISITION_EVENT_ENDPOINT, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(acquisitionEventPayload(eventType, errorCategory)),
    keepalive: true
  }).catch(() => {
    // Analytics must never block or alter the request form.
  });
}

function setMessage(text, type) {
  formMessage.textContent = text || "";
  formMessage.classList.toggle("is-error", type === "error");
  formMessage.classList.toggle("is-success", type === "success");
}

function createIdempotencyKey() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }

  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).slice(2);
  return `web-${timestamp}-${random}`;
}

function submissionSignature(serializedPayload) {
  let hash = 2166136261;
  for (let index = 0; index < serializedPayload.length; index += 1) {
    hash ^= serializedPayload.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `${serializedPayload.length}:${(hash >>> 0).toString(16)}`;
}

function loadActiveSubmission() {
  try {
    const raw = sessionStorage.getItem(ACTIVE_SUBMISSION_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (
      parsed
      && typeof parsed.key === "string"
      && /^[A-Za-z0-9._:-]{8,128}$/.test(parsed.key)
      && typeof parsed.signature === "string"
    ) {
      return parsed;
    }
  } catch {
    // Storage must never block request submission.
  }
  return null;
}

function persistActiveSubmission() {
  try {
    sessionStorage.setItem(
      ACTIVE_SUBMISSION_KEY,
      JSON.stringify(activeSubmission)
    );
  } catch {
    // In-memory idempotency still protects rapid duplicate submits.
  }
}

function idempotencyKeyFor(serializedPayload) {
  const signature = submissionSignature(serializedPayload);
  if (activeSubmission && activeSubmission.signature === signature) {
    return activeSubmission.key;
  }

  activeSubmission = {
    key: createIdempotencyKey(),
    signature
  };
  persistActiveSubmission();
  return activeSubmission.key;
}

function clearActiveSubmission() {
  activeSubmission = null;
  try {
    sessionStorage.removeItem(ACTIVE_SUBMISSION_KEY);
  } catch {
    // A successful request must not be turned into an error by storage.
  }
}

function normalizeTrackingLink(entry) {
  if (!entry || !entry.token) return null;

  return {
    job_id: entry.job_id ?? null,
    tracking_url: localizedTrackingPath(entry.token),
    token: entry.token
  };
}

function localizedTrackingPath(token) {
  const basePath = {
    en: "/en/track",
    ru: "/ru/track"
  }[localeKey] || "/track";

  return `${basePath}/${encodeURIComponent(token)}`;
}

function getTrackingLinks() {
  try {
    const raw = localStorage.getItem(TRACKING_LINKS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];

    if (!Array.isArray(parsed)) return [];

    const links = parsed
      .map(normalizeTrackingLink)
      .filter(Boolean)
      .slice(0, 20);

    if (JSON.stringify(parsed) !== JSON.stringify(links)) {
      localStorage.setItem(TRACKING_LINKS_KEY, JSON.stringify(links));
    }

    return links;
  } catch {
    return [];
  }
}

function saveTrackingLink(entry) {
  const current = normalizeTrackingLink(entry);
  if (!current) return;

  const links = getTrackingLinks()
    .filter((item) => item.token !== current.token);

  links.unshift(current);

  try {
    localStorage.setItem(
      TRACKING_LINKS_KEY,
      JSON.stringify(links.slice(0, 20))
    );
  } catch {
    // Tracking navigation must survive unavailable or full local storage.
  }
}




function formatOpenPedidosLabel(count) {
  const isMobile = window.matchMedia("(max-width: 640px)").matches;
  const label = isMobile
    ? messages.openRequestsShort
    : messages.openRequestsLong;
  return `${label} (${count})`;
}

function renderOpenPedidos() {
  const cta = document.querySelector("#openPedidosCta");
  if (!cta) return;

  const links = getTrackingLinks().filter((entry) => entry && entry.tracking_url);
  const count = links.length;

  cta.textContent = formatOpenPedidosLabel(count);

  if (count === 0) {
    cta.hidden = true;
    cta.removeAttribute("href");
    return;
  }

  cta.hidden = false;
  cta.href = links[0].tracking_url;
}

function setStep(step) {
  currentStep = Math.min(Math.max(step, 1), steps.length);
  steps.forEach((item) => {
    item.classList.toggle("is-active", Number(item.dataset.step) === currentStep);
  });
  const template = form.dataset.stepTemplate || "Passo {current} de {total}";
  stepLabel.textContent = template
    .replace("{current}", currentStep)
    .replace("{total}", steps.length);
  progressFill.style.width = `${(currentStep / steps.length) * 100}%`;
  setMessage("", "");
}

function parseOptionalInt(value) {
  if (value === "") return null;
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseOptionalFloat(value) {
  if (value === "") return null;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseOptionalBool(value) {
  if (value === "") return null;
  return value === "true";
}

function getFormData() {
  return Object.fromEntries(new FormData(form).entries());
}

function getFieldValidationMessage(field) {
  const messageId = field.dataset.validationMessageId;
  return messageId ? document.getElementById(messageId) : null;
}

function removeFieldValidationMessage(field) {
  const message = getFieldValidationMessage(field);

  if (message) {
    message.remove();
  }

  delete field.dataset.validationMessageId;
  field.removeAttribute("aria-describedby");
}

function showFieldValidationMessage(field, message) {
  removeFieldValidationMessage(field);

  const messageNode = document.createElement("div");
  const messageId =
    `field-validation-${field.name || "field"}-${Date.now()}`;

  messageNode.id = messageId;
  messageNode.className = "field-validation-message";
  messageNode.setAttribute("role", "alert");

  const icon = document.createElement("span");
  icon.className = "field-validation-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = "!";

  const text = document.createElement("span");
  text.className = "field-validation-text";
  text.textContent = message;

  messageNode.append(icon, text);
  field.insertAdjacentElement("afterend", messageNode);

  field.dataset.validationMessageId = messageId;
  field.setAttribute("aria-describedby", messageId);
}

function markFieldInvalid(field, message, focusField = true) {
  field.setCustomValidity(message);
  field.setAttribute("aria-invalid", "true");
  showFieldValidationMessage(field, message);

  if (focusField) {
    field.focus({preventScroll: true});
    field.scrollIntoView({
      behavior: "smooth",
      block: "center"
    });
  }
}

function clearFieldValidity(field) {
  field.setCustomValidity("");
  field.removeAttribute("aria-invalid");
  removeFieldValidationMessage(field);
}

function clearEditedFieldValidity(event) {
  const field = event.target;

  if (
    !(field instanceof HTMLInputElement)
    && !(field instanceof HTMLTextAreaElement)
    && !(field instanceof HTMLSelectElement)
  ) {
    return;
  }

  clearFieldValidity(field);
  if (["client_phone", "client_whatsapp", "customer_email"].includes(field.name)) {
    for (const contactName of ["client_phone", "client_whatsapp", "customer_email"]) {
      clearFieldValidity(form.elements[contactName]);
    }
  }
}

function setLocationSuggestionsExpanded(state, expanded) {
  state.suggestions.hidden = !expanded;
  state.input.setAttribute("aria-expanded", String(expanded));
}

function clearLocationSelection(state) {
  state.selection = null;
  state.confirm.checked = false;
  state.confirmation.hidden = true;
  state.selectedLabel.textContent = "";
  state.mapLink.removeAttribute("href");
}

function renderLocationStatus(state, message) {
  state.suggestions.replaceChildren();
  const status = document.createElement("p");
  status.className = "location-suggestions-status";
  status.textContent = message;
  state.suggestions.append(status);
  setLocationSuggestionsExpanded(state, true);
}

function renderLocationFallback(state, message) {
  state.suggestions.replaceChildren();

  const status = document.createElement("p");
  status.className = "location-suggestions-status";
  status.textContent = `${message} ${messages.locationManualHelp} `;

  const contact = document.createElement("a");
  contact.href = "mailto:hello@cargopt.pt";
  contact.textContent = messages.locationManualContact;
  status.append(contact);

  state.suggestions.append(status);
  setLocationSuggestionsExpanded(state, true);
}

function selectLocationSuggestion(state, suggestion, rawText) {
  state.selection = {
    rawText,
    displayName: suggestion.display_name,
    latitude: suggestion.latitude,
    longitude: suggestion.longitude,
    mapUrl: suggestion.map_url,
    countryCode: suggestion.country_code,
    postalCode: suggestion.postal_code,
    addressDetailsHint: suggestion.address_details_hint
  };
  state.input.value = suggestion.display_name;
  const detailsField = form.elements[
    state.input.name === "pickup"
      ? "pickup_address_details"
      : "dropoff_address_details"
  ];
  if (
    detailsField
    && !detailsField.value.trim()
    && suggestion.address_details_hint
  ) {
    detailsField.value = suggestion.address_details_hint;
  }
  state.selectedLabel.textContent = suggestion.display_name;
  state.mapLink.href = suggestion.map_url;
  state.confirm.checked = false;
  state.confirmation.hidden = false;
  setLocationSuggestionsExpanded(state, false);
  clearFieldValidity(state.input);
  state.confirm.focus({preventScroll: true});
}

function renderLocationSuggestions(state, suggestions, rawText) {
  state.suggestions.replaceChildren();

  if (!suggestions.length) {
    renderLocationFallback(state, messages.locationNoResults);
    return;
  }

  suggestions.forEach((suggestion) => {
    const option = document.createElement("button");
    option.type = "button";
    option.className = "location-suggestion";
    option.setAttribute("role", "option");
    option.textContent = suggestion.display_name;
    option.addEventListener("mousedown", (event) => event.preventDefault());
    option.addEventListener("click", () => {
      selectLocationSuggestion(state, suggestion, rawText);
    });
    state.suggestions.append(option);
  });

  setLocationSuggestionsExpanded(state, true);
}

async function searchLocations(state, rawText) {
  if (state.controller) {
    state.controller.abort();
  }

  const controller = new AbortController();
  state.controller = controller;
  state.searchButton.disabled = true;
  renderLocationStatus(state, messages.locationLoading);

  try {
    const params = new URLSearchParams({
      q: rawText,
      locale: localeKey,
      limit: "5"
    });
    const response = await fetch(`/api/v1/locations/search?${params}`, {
      signal: controller.signal,
      headers: {"Accept": "application/json"}
    });

    if (!response.ok) {
      throw new Error(`location search failed: ${response.status}`);
    }

    const suggestions = await response.json();
    if (state.input.value.trim() !== rawText) return;
    renderLocationSuggestions(state, suggestions, rawText);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    renderLocationFallback(state, messages.locationSearchFailure);
  } finally {
    if (state.controller === controller) {
      state.controller = null;
    }
    state.searchButton.disabled = false;
  }
}

function initializeLocationFields() {
  document.querySelectorAll("[data-location-field]").forEach((container) => {
    const input = container.querySelector('input[name="pickup"], input[name="dropoff"]');
    const suggestions = container.querySelector(".location-suggestions");
    const confirmation = container.querySelector("[data-location-confirmation]");
    const selectedLabel = container.querySelector("[data-location-label]");
    const mapLink = container.querySelector("[data-location-map]");
    const confirm = container.querySelector("[data-location-confirm]");
    const searchButton = container.querySelector("[data-location-search]");

    if (!input || !suggestions || !confirmation || !selectedLabel || !mapLink || !confirm || !searchButton) {
      return;
    }

    const state = {
      input,
      suggestions,
      confirmation,
      selectedLabel,
      mapLink,
      confirm,
      searchButton,
      selection: null,
      controller: null
    };
    locationFieldStates.set(input, state);

    input.addEventListener("input", () => {
      if (state.controller) {
        state.controller.abort();
        state.controller = null;
        state.searchButton.disabled = false;
      }
      clearLocationSelection(state);
      state.suggestions.replaceChildren();
      setLocationSuggestionsExpanded(state, false);
    });

    searchButton.addEventListener("click", () => {
      const rawText = input.value.trim();
      clearFieldValidity(input);
      clearLocationSelection(state);

      if (rawText.length < 3) {
        markFieldInvalid(input, messages.locationSelectRequired, true);
        return;
      }

      searchLocations(state, rawText);
    });

    confirm.addEventListener("change", () => {
      clearFieldValidity(input);
    });
  });

  document.addEventListener("click", (event) => {
    locationFieldStates.forEach((state) => {
      if (!state.input.closest("[data-location-field]").contains(event.target)) {
        setLocationSuggestionsExpanded(state, false);
      }
    });
  });
}

initializeLocationFields();

form.addEventListener("input", clearEditedFieldValidity);
form.addEventListener("change", clearEditedFieldValidity);

function isValidCalendarDate(year, month, day) {
  const date = new Date(Date.UTC(year, month - 1, day));

  return (
    date.getUTCFullYear() === year
    && date.getUTCMonth() === month - 1
    && date.getUTCDate() === day
  );
}

function isValidRequestedDate(value) {
  const rawValue = (value || "").trim().toLowerCase();

  if (!rawValue) return false;

  const relativeValues = [
    "hoje",
    "today",
    "сегодня",
    "amanhã",
    "amanha",
    "tomorrow",
    "завтра",
    "próximos dias",
    "proximos dias",
    "next few days",
    "в ближайшие дни",
    "qualquer dia",
    "any day",
    "любой день"
  ];

  if (relativeValues.includes(rawValue)) {
    return true;
  }

  const europeanDateMatch =
    rawValue.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);

  if (europeanDateMatch) {
    const [, day, month, year] =
      europeanDateMatch.map(Number);

    return isValidCalendarDate(year, month, day);
  }

  const isoDateMatch =
    rawValue.match(/^(\d{4})-(\d{2})-(\d{2})$/);

  if (isoDateMatch) {
    const [, year, month, day] =
      isoDateMatch.map(Number);

    return isValidCalendarDate(year, month, day);
  }

  return false;
}

function isValidPhone(value) {
  const normalizedValue = (value || "").trim();

  if (!normalizedValue) return false;

  if (!/^[+()\d\s.-]+$/.test(normalizedValue)) {
    return false;
  }

  const digitCount =
    (normalizedValue.match(/\d/g) || []).length;

  return digitCount >= 7 && digitCount <= 15;
}

function isRequestedDateInPast(value) {
  const normalized = normalizeRequestedDate(value);
  if (!normalized) return false;
  return normalized < portugalCalendarToday();
}

function validateField(field, focusField = false) {
  clearFieldValidity(field);

  const value = field.value.trim();

  if (field.required && !value) {
    markFieldInvalid(
      field,
      messages.required,
      focusField
    );
    return false;
  }

  const locationState = locationFieldStates.get(field);
  if (locationState && value && !locationState.selection) {
    markFieldInvalid(
      field,
      messages.locationSelectRequired,
      focusField
    );
    return false;
  }

  if (locationState && value && !locationState.confirm.checked) {
    markFieldInvalid(
      field,
      messages.locationConfirmRequired,
      focusField
    );
    return false;
  }

  if (
    field.name === "requested_date"
    && value
    && !isValidRequestedDate(value)
  ) {
    markFieldInvalid(
      field,
      messages.validationFailure,
      focusField
    );
    return false;
  }

  if (
    field.name === "requested_date"
    && value
    && isRequestedDateInPast(value)
  ) {
    markFieldInvalid(
      field,
      messages.requestedDatePast,
      focusField
    );
    return false;
  }

  if (
    ["client_phone", "client_whatsapp"].includes(field.name)
    && value
    && !isValidPhone(value)
  ) {
    markFieldInvalid(
      field,
      messages.validationFailure,
      focusField
    );
    return false;
  }

  if (!field.validity.valid) {
    markFieldInvalid(
      field,
      messages.validationFailure,
      focusField
    );
    return false;
  }

  return true;
}

function validateStep(step) {
  const activeStep = steps[step - 1];
  const fields = Array.from(
    activeStep.querySelectorAll(
      "input, textarea, select"
    )
  );
  let firstInvalidField = null;

  for (const field of fields) {
    const isValid = validateField(field);

    if (!isValid && firstInvalidField === null) {
      firstInvalidField = field;
    }
  }

  if (step === 2) {
    const data = getFormData();
    const requestedDateLocal = normalizeRequestedDate(data.requested_date);
    if (requestedDateLocal && !(data.requested_time || "").trim()) {
      const requestedTimeField = form.elements.requested_time;
      markFieldInvalid(
        requestedTimeField,
        messages.requestedTimeRequired,
        false
      );
      if (firstInvalidField === null) firstInvalidField = requestedTimeField;
    }
    const hasContact = [
      data.client_phone,
      data.client_whatsapp,
      data.customer_email
    ].some((value) => (value || "").trim());

    if (!hasContact) {
      const contactField = form.elements.client_phone;
      markFieldInvalid(contactField, messages.contact, false);
      if (firstInvalidField === null) firstInvalidField = contactField;
    }
  }

  if (firstInvalidField) {
    firstInvalidField.focus({preventScroll: true});
    firstInvalidField.scrollIntoView({
      behavior: "smooth",
      block: "center"
    });
    return false;
  }

  return true;
}

function formatCalendarDate(year, month, day) {
  return [
    String(year).padStart(4, "0"),
    String(month).padStart(2, "0"),
    String(day).padStart(2, "0")
  ].join("-");
}

function portugalCalendarToday() {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Lisbon",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(new Date());
  const values = Object.fromEntries(
    parts
      .filter((part) => ["year", "month", "day"].includes(part.type))
      .map((part) => [part.type, part.value])
  );
  return `${values.year}-${values.month}-${values.day}`;
}

function shiftCalendarDate(value, days) {
  const [year, month, day] = value.split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1, day + days));
  return formatCalendarDate(
    shifted.getUTCFullYear(),
    shifted.getUTCMonth() + 1,
    shifted.getUTCDate()
  );
}

function portugalLocalDateTimeToInstant(localDate, localTime) {
  if (!localDate || !localTime) return null;
  const [year, month, day] = localDate.split("-").map(Number);
  const [hour, minute] = localTime.split(":").map(Number);
  if (![year, month, day, hour, minute].every(Number.isFinite)) return null;

  const desired = Date.UTC(year, month - 1, day, hour, minute);
  let instant = desired;
  const formatter = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Lisbon",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23"
  });

  for (let attempt = 0; attempt < 3; attempt += 1) {
    const values = Object.fromEntries(
      formatter
        .formatToParts(new Date(instant))
        .filter((part) => ["year", "month", "day", "hour", "minute"].includes(part.type))
        .map((part) => [part.type, Number(part.value)])
    );
    const represented = Date.UTC(
      values.year,
      values.month - 1,
      values.day,
      values.hour,
      values.minute
    );
    const adjustment = desired - represented;
    if (adjustment === 0) return new Date(instant);
    instant += adjustment;
  }
  return null;
}

function hasShortLeadRequestedDate(localDate, localTime, now = new Date()) {
  const requested = portugalLocalDateTimeToInstant(localDate, localTime);
  if (!requested) return null;
  return requested.getTime() < now.getTime() + 72 * 60 * 60 * 1000;
}

function normalizeRequestedDate(value) {
  const rawValue = (value || "").trim().toLowerCase();
  if (!rawValue) return null;

  const today = portugalCalendarToday();

  if (["hoje", "today", "сегодня"].includes(rawValue)) {
    return today;
  }

  if (["amanhã", "amanha", "tomorrow", "завтра"].includes(rawValue)) {
    return shiftCalendarDate(today, 1);
  }

  if (["próximos dias", "proximos dias", "next few days", "в ближайшие дни"].includes(rawValue)) {
    return shiftCalendarDate(today, 3);
  }

  if (["qualquer dia", "any day", "любой день"].includes(rawValue)) {
    return null;
  }

  const europeanDateMatch = rawValue.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (europeanDateMatch) {
    const [, day, month, year] = europeanDateMatch;
    return formatCalendarDate(Number(year), Number(month), Number(day));
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(rawValue)) {
    return rawValue;
  }

  return null;
}

function renderRequestLeadTimeNotice() {
  const notice = document.querySelector("#requestLeadTimeNotice");
  if (!notice) return;

  const rawDate = (form.elements.requested_date.value || "").trim();
  const rawTime = (form.elements.requested_time.value || "").trim();
  const flexible = ["qualquer dia", "any day", "любой день"].includes(
    rawDate.toLowerCase()
  );

  notice.classList.remove("is-manual", "is-urgent", "is-automatic");
  if (flexible) {
    notice.textContent = messages.leadTimeFlexible;
    notice.classList.add("is-manual");
    return;
  }

  const localDate = normalizeRequestedDate(rawDate);
  const shortLead = hasShortLeadRequestedDate(localDate, rawTime);
  if (shortLead === null) {
    notice.textContent = "";
    return;
  }

  notice.textContent = shortLead
    ? messages.leadTimeUrgent
    : messages.leadTimeAutomatic;
  notice.classList.add(shortLead ? "is-urgent" : "is-automatic");
}

form.elements.requested_date.addEventListener("input", renderRequestLeadTimeNotice);
form.elements.requested_time.addEventListener("input", renderRequestLeadTimeNotice);
renderRequestLeadTimeNotice();

function buildPayload() {
  const data = getFormData();
  const requestedDateLocal = normalizeRequestedDate(data.requested_date);
  const pickupLocation = locationFieldStates.get(form.elements.pickup);
  const dropoffLocation = locationFieldStates.get(form.elements.dropoff);

  function buildAddress(kind, state, floor, hasElevator, addressDetails) {
    const selection = state && state.selection;
    return {
      kind,
      raw_text: selection ? selection.rawText : "",
      normalized_address: selection ? selection.displayName : "",
      latitude: selection ? selection.latitude : null,
      longitude: selection ? selection.longitude : null,
      location_confirmed: Boolean(selection && state.confirm.checked),
      country_code: selection ? selection.countryCode : "",
      address_details: addressDetails || null,
      postal_code: selection ? selection.postalCode : null,
      floor,
      has_elevator: hasElevator
    };
  }

  return {
    source_locale: localeKey,
    customer_name: data.customer_name || null,
    customer_email: data.customer_email || null,
    preferred_contact: data.client_whatsapp ? "whatsapp" : data.client_phone ? "phone" : data.customer_email ? "email" : null,
    client_phone: data.client_phone || null,
    client_whatsapp: data.client_whatsapp || null,
    utm_source: firstTouchAttribution.utm_source
      || (firstTouchAttribution.fbclid ? "facebook" : null),
    utm_medium: firstTouchAttribution.utm_medium,
    utm_campaign: firstTouchAttribution.utm_campaign,
    utm_content: firstTouchAttribution.utm_content,
    referrer_host: firstTouchAttribution.referrer_host,
    fbclid: firstTouchAttribution.fbclid,
    landing_version: LANDING_VERSION,
    requested_date_local: requestedDateLocal,
    requested_time_local: requestedDateLocal
      ? (data.requested_time || null)
      : null,
    addresses: [
      buildAddress(
        "pickup",
        pickupLocation,
        parseOptionalInt(data.pickup_floor),
        parseOptionalBool(data.pickup_elevator),
        data.pickup_address_details
      ),
      buildAddress(
        "dropoff",
        dropoffLocation,
        parseOptionalInt(data.dropoff_floor),
        parseOptionalBool(data.dropoff_elevator),
        data.dropoff_address_details
      )
    ],
    items: [
      {
        description: data.items,
        quantity: null
      }
    ],
    required_loaders: parseOptionalInt(data.required_loaders),
    estimated_volume_m3: parseOptionalFloat(data.estimated_volume_m3),
    needs_assembly: data.needs_assembly === "true",
    needs_packing: data.needs_packing === "true",
    needs_tail_lift: data.needs_tail_lift === "true",
    needs_crane: data.needs_crane === "true",
    needs_mobile_lift: data.needs_mobile_lift === "true",
    comment: data.comment || null
  };
}

const SUBMIT_TIMEOUT_MS = 15000;

const VALIDATION_CATEGORY_FIELDS = {
  pickup: "pickup",
  dropoff: "dropoff",
  items: "items",
  customer_name: "customer_name",
  requested_date: "requested_date",
  contact: "client_phone",
  client_phone: "client_phone",
  client_whatsapp: "client_whatsapp",
  customer_email: "customer_email",
  pickup_floor: "pickup_floor",
  pickup_elevator: "pickup_elevator",
  dropoff_floor: "dropoff_floor",
  dropoff_elevator: "dropoff_elevator",
  required_loaders: "required_loaders",
  estimated_volume_m3: "estimated_volume_m3",
  comment: "comment"
};

function validationCategory(detail) {
  const location = Array.isArray(detail && detail.loc) ? detail.loc : [];
  const field = location[1];

  if (field === "addresses") {
    const addressIndex = Number(location[2]);
    const addressField = location[3];
    const prefix = addressIndex === 0 ? "pickup" : "dropoff";
    if (addressField === "floor") return `${prefix}_floor`;
    if (addressField === "has_elevator") return `${prefix}_elevator`;
    return prefix;
  }

  if (field === "items") return "items";
  if (Object.prototype.hasOwnProperty.call(VALIDATION_CATEGORY_FIELDS, field)) return field;
  return field ? "unknown" : "request";
}

function extractValidationCategories(body) {
  if (!body || !Array.isArray(body.detail)) return ["request"];
  const categories = body.detail.map(validationCategory);
  return [...new Set(categories.length ? categories : ["request"])];
}

function markServerValidationFields(categories) {
  let firstField = null;
  categories.forEach((category) => {
    const fieldName = VALIDATION_CATEGORY_FIELDS[category];
    const field = fieldName ? form.elements[fieldName] : null;
    if (!field) return;
    markFieldInvalid(field, messages.validationFailure, false);
    if (!firstField) firstField = field;
  });

  if (firstField) {
    firstField.focus({preventScroll: true});
    firstField.scrollIntoView({behavior: "smooth", block: "center"});
  }
}

class RequestSubmissionError extends Error {
  constructor(kind, status = null, validationCategories = []) {
    super(kind);
    this.name = "RequestSubmissionError";
    this.kind = kind;
    this.status = status;
    this.validationCategories = validationCategories;
  }
}

function classifySubmissionStatus(status) {
  if (status === 400 || status === 422) return "validation";
  if (status === 409) return "conflict";
  if (status === 429) return "rateLimit";
  if (status >= 500) return "server";
  return "unexpected";
}

function getSubmissionErrorMessage(error) {
  if (error instanceof RequestSubmissionError) {
    if (error.kind === "validation" && error.validationCategories.length) {
      const labels = error.validationCategories
        .map((category) => validationFieldLabels[category] || validationFieldLabels.unknown);
      return messages.validationFieldFailure.replace(
        "{fields}",
        [...new Set(labels)].join(", ")
      );
    }
    const messageKey = `${error.kind}Failure`;
    return messages[messageKey] || messages.unexpectedFailure;
  }

  if (error instanceof DOMException && error.name === "AbortError") {
    return messages.timeoutFailure;
  }

  if (error instanceof TypeError) {
    return messages.networkFailure;
  }

  return messages.unexpectedFailure;
}

async function submitRequest() {
  if (!validateStep(2)) return;

  recordAcquisitionEvent("submit_attempt");
  setMessage(messages.submitting, "");
  const submitButton = form.querySelector("button[type=\"submit\"]");
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    SUBMIT_TIMEOUT_MS
  );

  submitButton.disabled = true;

  try {
    const requestBody = JSON.stringify(buildPayload());
    const idempotencyKey = idempotencyKeyFor(requestBody);
    const response = await fetch("/api/v1/requests", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey
      },
      body: requestBody,
      signal: controller.signal
    });

    if (!response.ok) {
      let responseBody = null;
      try {
        responseBody = await response.json();
      } catch {
        responseBody = null;
      }
      throw new RequestSubmissionError(
        classifySubmissionStatus(response.status),
        response.status,
        response.status === 422
          ? extractValidationCategories(responseBody)
          : []
      );
    }

    const body = await response.json();
    recordAcquisitionEvent("submit_success");

    if (window.CargoPTMeta) {
      window.CargoPTMeta.trackLeadOnce(body.job_id);
    }

    if (body.tracking_token && body.tracking_url) {
      const trackingEntry = {
        job_id: body.job_id,
        tracking_url: body.tracking_url,
        token: body.tracking_token
      };
      saveTrackingLink(trackingEntry);
      clearActiveSubmission();
      window.location.href = localizedTrackingPath(body.tracking_token);
    } else {
      clearActiveSubmission();
      setMessage(messages.success, "success");
    }

    if (!body.tracking_token || !body.tracking_url) {
      form.reset();
      setStep(1);
    }
  } catch (error) {
    if (error instanceof RequestSubmissionError && error.kind === "validation") {
      markServerValidationFields(error.validationCategories);
      recordAcquisitionEvent(
        "submit_error_validation",
        error.validationCategories[0] || "request"
      );
    } else if (error instanceof RequestSubmissionError && error.kind === "rateLimit") {
      recordAcquisitionEvent("submit_error_rate_limit");
    } else if (error instanceof RequestSubmissionError && error.kind === "server") {
      recordAcquisitionEvent("submit_error_server");
    } else if (
      error instanceof TypeError
      || (error instanceof DOMException && error.name === "AbortError")
    ) {
      recordAcquisitionEvent("submit_error_network");
    } else {
      recordAcquisitionEvent("submit_error_unexpected");
    }
    setMessage(getSubmissionErrorMessage(error), "error");
    console.error(error);
  } finally {
    window.clearTimeout(timeoutId);
    submitButton.disabled = false;
  }
}

form.addEventListener("input", (event) => {
  recordAcquisitionEvent("form_start");

  const field = event.target.closest("[required]");
  if (field) {
    clearFieldValidity(field);
  }
});

form.addEventListener("change", (event) => {
  recordAcquisitionEvent("form_start");

  const field = event.target.closest("[required]");
  if (field) {
    clearFieldValidity(field);
  }
});

form.addEventListener("focusout", (event) => {
  const field = event.target.closest(
    "input, textarea, select"
  );
  if (!field || !form.contains(field)) return;

  validateField(field);
});

document.addEventListener("click", (event) => {
  const newRequest = event.target.closest("[data-new-request]");
  if (!newRequest || form.contains(newRequest)) return;
  window.location.href = localizedHomePath;
});

form.addEventListener("click", (event) => {
  const next = event.target.closest("[data-next]");
  const prev = event.target.closest("[data-prev]");
  const newRequest = event.target.closest("[data-new-request]");

  if (newRequest) {
    window.location.href = localizedHomePath;
    return;
  }

  if (next && validateStep(currentStep)) {
    recordAcquisitionEvent("step1_complete");
    setStep(currentStep + 1);
  }

  if (prev) {
    setStep(currentStep - 1);
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitRequest();
});

const carousel = document.querySelector(".process-carousel");

if (carousel) {
  const track = carousel.querySelector(".process-carousel-track");
  const cards = [...track.querySelectorAll(".process-card")];

  let index = 0;
  let animationFrame = 0;
  let trackWidth = 0;
  let cardGeometry = [];

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function measureCarousel() {
    trackWidth = track.clientWidth;

    cardGeometry = cards.map((card) => ({
      center: card.offsetLeft + card.offsetWidth / 2,
      width: card.offsetWidth,
    }));
  }

  function renderCarousel() {
    animationFrame = 0;

    const trackCenter = track.scrollLeft + trackWidth / 2;
    let closest = 0;
    let closestDistance = Infinity;

    cards.forEach((card, i) => {
      const geometry = cardGeometry[i];

      if (!geometry) {
        return;
      }

      const signedDistance = geometry.center - trackCenter;
      const normalizedDistance = clamp(
        signedDistance / Math.max(geometry.width * 0.82, 1),
        -1.4,
        1.4
      );
      const proximity = 1 - clamp(Math.abs(normalizedDistance), 0, 1);

      const scale = 0.82 + proximity * 0.22;
      const lift = 10 - proximity * 18;
      const rotation = -normalizedDistance * 10;
      const opacity = 0.5 + proximity * 0.5;
      const saturation = 0.68 + proximity * 0.32;
      const brightness = 0.94 + proximity * 0.06;
      const shadowStrength = 0.12 + proximity * 0.12;

      card.style.setProperty("--carousel-scale", scale.toFixed(4));
      card.style.setProperty("--carousel-lift", `${lift.toFixed(2)}px`);
      card.style.setProperty(
        "--carousel-rotation",
        `${rotation.toFixed(2)}deg`
      );
      card.style.setProperty(
        "--carousel-opacity",
        opacity.toFixed(4)
      );
      card.style.setProperty(
        "--carousel-saturation",
        saturation.toFixed(4)
      );
      card.style.setProperty(
        "--carousel-brightness",
        brightness.toFixed(4)
      );
      card.style.setProperty(
        "--carousel-shadow-strength",
        shadowStrength.toFixed(4)
      );
      card.style.zIndex = String(
        10 + Math.round(proximity * 20)
      );

      const absoluteDistance = Math.abs(signedDistance);

      if (absoluteDistance < closestDistance) {
        closestDistance = absoluteDistance;
        closest = i;
      }
    });

    index = closest;

    cards.forEach((card, i) => {
      const distance = i - index;

      card.classList.toggle("is-active", distance === 0);
      card.classList.toggle("is-prev", distance === -1);
      card.classList.toggle("is-next", distance === 1);
      card.classList.toggle("is-far", Math.abs(distance) > 1);
      card.setAttribute(
        "aria-current",
        distance === 0 ? "true" : "false"
      );
    });
  }

  function requestCarouselRender() {
    if (animationFrame) {
      return;
    }

    animationFrame = requestAnimationFrame(renderCarousel);
  }

  function refreshCarouselGeometry() {
    measureCarousel();
    requestCarouselRender();
  }

  track.addEventListener(
    "scroll",
    requestCarouselRender,
    { passive: true }
  );

  window.addEventListener(
    "resize",
    refreshCarouselGeometry
  );

  refreshCarouselGeometry();
}


preserveAttributionOnLocaleLinks();
recordAcquisitionEvent("landing_view");
setStep(1);
renderOpenPedidos();
window.addEventListener("resize", renderOpenPedidos);
