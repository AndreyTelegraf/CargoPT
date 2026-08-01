const TRACKING_LINKS_KEY = "cargopt_tracking_links";
const pageLocale = document.body.dataset.locale || document.documentElement.lang || "ru";
const form = document.querySelector("#requestForm");
const hero = document.querySelector(".hero");
const steps = Array.from(document.querySelectorAll(".form-step"));
const stepLabel = document.querySelector("#stepLabel");
const progressFill = document.querySelector("#progressFill");
const formMessage = document.querySelector("#formMessage");
const progress = document.querySelector(".progress");
let currentStep = 1;

const MESSAGES = {
  pt: {
    required: "Preencha os campos obrigatórios para continuar.",
    contact: "Indique pelo menos um contacto: telefone, WhatsApp ou email.",
    submitting: "A enviar o pedido...",
    success: "Pedido enviado. Vamos encaminhá-lo para transportadores.",
    validationFailure: "Alguns dados do pedido não são válidos. Verifique os campos e tente novamente.",
    requestedDatePast: "A data do transporte não pode estar no passado.",
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
    openRequestsLong: "Meus pedidos"
  },
  en: {
    required: "Fill in the required fields to continue.",
    contact: "Add at least one contact: phone, WhatsApp or email.",
    submitting: "Sending request...",
    success: "Request sent. We will forward it to carriers.",
    validationFailure: "Some request details are invalid. Check the fields and try again.",
    requestedDatePast: "The moving date cannot be in the past.",
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
    openRequestsLong: "My requests"
  },
  ru: {
    required: "Заполните обязательные поля, чтобы продолжить.",
    contact: "Укажите хотя бы один контакт: телефон, WhatsApp или email.",
    submitting: "Отправляем заявку...",
    success: "Заявка отправлена. Мы передадим её перевозчикам.",
    validationFailure: "Некоторые данные заявки заполнены неверно. Проверьте поля и отправьте ещё раз.",
    requestedDatePast: "Дата перевозки не может быть в прошлом.",
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
    openRequestsLong: "Мои заявки"
  }
};

const localeKey = pageLocale === "pt-PT" ? "pt" : pageLocale.slice(0, 2);
const messages = MESSAGES[localeKey] || MESSAGES.pt;
const localizedHomePath = {
  en: "/en/",
  ru: "/ru/",
}[localeKey] || "/";

function setMessage(text, type) {
  formMessage.textContent = text || "";
  formMessage.classList.toggle("is-error", type === "error");
  formMessage.classList.toggle("is-success", type === "success");
}

function normalizeTrackingLink(entry) {
  if (!entry || !entry.token || !entry.tracking_url) return null;

  return {
    job_id: entry.job_id ?? null,
    tracking_url: entry.tracking_url,
    token: entry.token
  };
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

  localStorage.setItem(
    TRACKING_LINKS_KEY,
    JSON.stringify(links.slice(0, 20))
  );
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
}

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

  const [year, month, day] = normalized
    .slice(0, 10)
    .split("-")
    .map(Number);
  const requestedDate = new Date(year, month - 1, day);
  const now = new Date();
  const today = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate()
  );

  return requestedDate < today;
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

function formatDateForPayload(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function normalizeRequestedDate(value) {
  const rawValue = (value || "").trim().toLowerCase();
  if (!rawValue) return null;

  const today = new Date();
  const targetDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());

  if (["hoje", "today", "сегодня"].includes(rawValue)) {
    return `${formatDateForPayload(targetDate)}T12:00:00+00:00`;
  }

  if (["amanhã", "amanha", "tomorrow", "завтра"].includes(rawValue)) {
    targetDate.setDate(targetDate.getDate() + 1);
    return `${formatDateForPayload(targetDate)}T12:00:00+00:00`;
  }

  if (["próximos dias", "proximos dias", "next few days", "в ближайшие дни"].includes(rawValue)) {
    targetDate.setDate(targetDate.getDate() + 3);
    return `${formatDateForPayload(targetDate)}T12:00:00+00:00`;
  }

  if (["qualquer dia", "any day", "любой день"].includes(rawValue)) {
    return null;
  }

  const europeanDateMatch = rawValue.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (europeanDateMatch) {
    const [, day, month, year] = europeanDateMatch;
    return `${year}-${month}-${day}T12:00:00+00:00`;
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(rawValue)) {
    return `${rawValue}T12:00:00+00:00`;
  }

  return null;
}

function buildPayload() {
  const data = getFormData();
  const requestedDate = normalizeRequestedDate(data.requested_date);

  return {
    source_locale: localeKey,
    customer_name: data.customer_name || null,
    customer_email: data.customer_email || null,
    preferred_contact: data.client_whatsapp ? "whatsapp" : data.client_phone ? "phone" : data.customer_email ? "email" : null,
    client_phone: data.client_phone || null,
    client_whatsapp: data.client_whatsapp || null,
    utm_source: new URLSearchParams(window.location.search).get("utm_source"),
    utm_medium: new URLSearchParams(window.location.search).get("utm_medium"),
    utm_campaign: new URLSearchParams(window.location.search).get("utm_campaign"),
    utm_content: new URLSearchParams(window.location.search).get("utm_content"),
    landing_version: "landing_static_v2",
    requested_date: requestedDate,
    addresses: [
      {
        kind: "pickup",
        raw_text: data.pickup,
        floor: parseOptionalInt(data.pickup_floor),
        has_elevator: parseOptionalBool(data.pickup_elevator)
      },
      {
        kind: "dropoff",
        raw_text: data.dropoff,
        floor: parseOptionalInt(data.dropoff_floor),
        has_elevator: parseOptionalBool(data.dropoff_elevator)
      }
    ],
    items: [
      {
        description: data.items,
        quantity: null
      }
    ],
    required_loaders: parseOptionalInt(data.required_loaders),
    estimated_volume_m3: parseOptionalFloat(data.estimated_volume_m3),
    comment: data.comment || null
  };
}

const SUBMIT_TIMEOUT_MS = 15000;

class RequestSubmissionError extends Error {
  constructor(kind, status = null) {
    super(kind);
    this.name = "RequestSubmissionError";
    this.kind = kind;
    this.status = status;
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

  setMessage(messages.submitting, "");
  const submitButton = form.querySelector("button[type=\"submit\"]");
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    SUBMIT_TIMEOUT_MS
  );

  submitButton.disabled = true;

  try {
    const response = await fetch("/api/v1/requests", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(buildPayload()),
      signal: controller.signal
    });

    if (!response.ok) {
      throw new RequestSubmissionError(
        classifySubmissionStatus(response.status),
        response.status
      );
    }

    const body = await response.json();

    if (body.tracking_token && body.tracking_url) {
      const trackingEntry = {
        job_id: body.job_id,
        tracking_url: body.tracking_url,
        token: body.tracking_token
      };
      saveTrackingLink(trackingEntry);
      window.location.href = body.tracking_url;
    } else {
      setMessage(messages.success, "success");
    }

    if (!body.tracking_token || !body.tracking_url) {
      form.reset();
      setStep(1);
    }
  } catch (error) {
    setMessage(getSubmissionErrorMessage(error), "error");
    console.error(error);
  } finally {
    window.clearTimeout(timeoutId);
    submitButton.disabled = false;
  }
}

form.addEventListener("input", (event) => {

  const field = event.target.closest("[required]");
  if (field) {
    clearFieldValidity(field);
  }
});

form.addEventListener("change", (event) => {

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


setStep(1);
renderOpenPedidos();
window.addEventListener("resize", renderOpenPedidos);
