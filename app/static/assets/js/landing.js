const STORAGE_KEY = "cargopt_landing_request_v2";
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
    required: "Preencha os campos obrigatórios deste passo.",
    contact: "Indique pelo menos um contacto: telefone, WhatsApp ou email.",
    submitting: "A enviar o pedido...",
    success: "Pedido enviado. Vamos encaminhá-lo para transportadores.",
    failure: "Não foi possível enviar o pedido. Verifique os campos ou tente mais tarde.",
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
    required: "Fill in the required fields for this step.",
    contact: "Add at least one contact: phone, WhatsApp or email.",
    submitting: "Sending request...",
    success: "Request sent. We will forward it to carriers.",
    failure: "Could not send the request. Check the fields or try again later.",
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
    required: "Заполните обязательные поля этого шага.",
    contact: "Укажите хотя бы один контакт: телефон, WhatsApp или email.",
    submitting: "Отправляем заявку...",
    success: "Заявка отправлена. Мы передадим её перевозчикам.",
    failure: "Не удалось отправить заявку. Проверьте поля или попробуйте позже.",
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

function setMessage(text, type) {
  formMessage.textContent = text || "";
  formMessage.classList.toggle("is-error", type === "error");
  formMessage.classList.toggle("is-success", type === "success");
}

function buildRouteSummary(data) {
  const pickup = data.pickup ? data.pickup.trim() : "";
  const dropoff = data.dropoff ? data.dropoff.trim() : "";
  if (pickup && dropoff) return `${pickup} → ${dropoff}`;
  return pickup || dropoff || messages.defaultRoute;
}

function buildShortSummary(value) {
  const normalized = value ? value.trim().replace(/\s+/g, " ") : "";
  if (normalized.length <= 80) return normalized;
  return `${normalized.slice(0, 77)}...`;
}

function getTrackingLinks() {
  try {
    const raw = localStorage.getItem(TRACKING_LINKS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveTrackingLink(entry) {
  const links = getTrackingLinks().filter((item) => item.token !== entry.token);
  links.unshift(entry);
  localStorage.setItem(TRACKING_LINKS_KEY, JSON.stringify(links.slice(0, 20)));
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

function saveDraft() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(getFormData()));
}

function restoreDraft() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;

  try {
    const data = JSON.parse(raw);
    Object.entries(data).forEach(([name, value]) => {
      const field = form.elements[name];
      if (field) field.value = value;
    });
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function markFieldInvalid(field, message) {
  field.setCustomValidity(message);
  field.reportValidity();
  field.focus();
}

function clearFieldValidity(field) {
  field.setCustomValidity("");
}

function validateStep(step) {
  const activeStep = steps[step - 1];
  const requiredFields = Array.from(activeStep.querySelectorAll("[required]"));
  for (const field of requiredFields) {
    clearFieldValidity(field);
    if (!field.value.trim()) {
      markFieldInvalid(field, messages.required);
      return false;
    }
  }

  return true;
}

function formatDateForPayload(date) {
  return date.toISOString().slice(0, 10);
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
    utm_campaign: new URLSearchParams(window.location.search).get("utm_campaign"),
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

async function submitRequest() {
  if (!validateStep(2)) return;

  setMessage(messages.submitting, "");
  const submitButton = form.querySelector("button[type=\"submit\"]");
  submitButton.disabled = true;

  try {
    const response = await fetch("/api/v1/requests", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(buildPayload())
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }

    const body = await response.json();
    const submittedData = getFormData();

    if (body.tracking_token && body.tracking_url) {
      const trackingEntry = {
        job_id: body.job_id,
        tracking_url: body.tracking_url,
        token: body.tracking_token,
        created_at: new Date().toISOString(),
        status_label: messages.waitingOffers,
        route_summary: buildRouteSummary(submittedData),
        item_summary: buildShortSummary(submittedData.items),
        comment_summary: buildShortSummary(submittedData.comment)
      };
      saveTrackingLink(trackingEntry);
      window.location.href = body.tracking_url;
    } else {
      setMessage(messages.success, "success");
    }

    localStorage.removeItem(STORAGE_KEY);
    if (!body.tracking_token || !body.tracking_url) {
      form.reset();
      setStep(1);
    }
  } catch (error) {
    setMessage(messages.failure, "error");
    console.error(error);
  } finally {
    submitButton.disabled = false;
  }
}

form.addEventListener("input", saveDraft);
form.addEventListener("change", saveDraft);

document.addEventListener("click", (event) => {
  const newRequest = event.target.closest("[data-new-request]");
  if (!newRequest || form.contains(newRequest)) return;
  window.location.href = "/";
});

form.addEventListener("click", (event) => {
  const next = event.target.closest("[data-next]");
  const prev = event.target.closest("[data-prev]");
  const newRequest = event.target.closest("[data-new-request]");

  if (newRequest) {
    window.location.href = "/";
    return;
  }

  if (next && validateStep(currentStep)) {
    saveDraft();
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
  const prev = carousel.querySelector(".process-carousel-prev");
  const next = carousel.querySelector(".process-carousel-next");
  const dots = [...carousel.querySelectorAll(".process-carousel-dots button")];

  let index = 0;

  function update() {
    dots.forEach((dot, i) => {
      dot.classList.toggle("is-active", i === index);
    });

    prev.disabled = index === 0;
    next.disabled = index === cards.length - 1;
  }

  function go(i) {
    index = Math.max(0, Math.min(i, cards.length - 1));

    track.scrollTo({
      left: cards[index].offsetLeft,
      behavior: "smooth"
    });

    update();
  }

  track.addEventListener("scroll", () => {
    let closest = 0;
    let distance = Infinity;

    cards.forEach((card, i) => {
      const d = Math.abs(track.scrollLeft - card.offsetLeft);
      if (d < distance) {
        distance = d;
        closest = i;
      }
    });

    if (closest !== index) {
      index = closest;
      update();
    }
  });

  prev.addEventListener("click", () => go(index - 1));
  next.addEventListener("click", () => go(index + 1));

  dots.forEach((dot, i) => {
    dot.addEventListener("click", () => go(i));
  });

  update();
}


restoreDraft();
setStep(1);
renderOpenPedidos();
window.addEventListener("resize", renderOpenPedidos);
