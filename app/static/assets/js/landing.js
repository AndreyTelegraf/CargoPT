const STORAGE_KEY = "cargopt_landing_request_v2";
const TRACKING_LINKS_KEY = "cargopt_tracking_links";
const pageLocale = document.body.dataset.locale || document.documentElement.lang || "ru";
const form = document.querySelector("#requestForm");
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
    trackingTitle: "Guarde este link para acompanhar propostas deste pedido",
    trackingText: "Não enviamos spam. Este link serve apenas para acompanhar propostas deste pedido.",
    viewStatus: "Ver estado",
    copyLink: "Copiar link",
    linkCopied: "Link copiado",
    shareWhatsApp: "Enviar por WhatsApp",
    defaultRoute: "Pedido CargoPT",
    waitingOffers: "A aguardar propostas"
  },
  en: {
    required: "Fill in the required fields for this step.",
    contact: "Add at least one contact: phone, WhatsApp or email.",
    submitting: "Sending request...",
    success: "Request sent. We will forward it to carriers.",
    failure: "Could not send the request. Check the fields or try again later.",
    trackingTitle: "Save this link to track offers for this request",
    trackingText: "We do not send spam. This link is only for tracking offers for this request.",
    viewStatus: "View status",
    copyLink: "Copy link",
    linkCopied: "Link copied",
    shareWhatsApp: "Send by WhatsApp",
    defaultRoute: "CargoPT request",
    waitingOffers: "Waiting for offers"
  },
  ru: {
    required: "Заполните обязательные поля этого шага.",
    contact: "Укажите хотя бы один контакт: телефон, WhatsApp или email.",
    submitting: "Отправляем заявку...",
    success: "Заявка отправлена. Мы передадим её перевозчикам.",
    failure: "Не удалось отправить заявку. Проверьте поля или попробуйте позже.",
    trackingTitle: "Сохраните эту ссылку, чтобы отслеживать предложения по заявке",
    trackingText: "Мы не отправляем спам. Эта ссылка нужна только для отслеживания предложений по этой заявке.",
    viewStatus: "Статус заявки",
    copyLink: "Скопировать ссылку",
    linkCopied: "Ссылка скопирована",
    shareWhatsApp: "Отправить в WhatsApp",
    defaultRoute: "Заявка CargoPT",
    waitingOffers: "Ожидаем предложения"
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

function absoluteUrl(path) {
  return new URL(path, window.location.origin).toString();
}

function switchFormToTrackingMode() {
  const explainer = document.querySelector(".product-explainer");
  if (explainer) {
    explainer.hidden = true;
  }

  if (progress) {
    progress.hidden = true;
  }

  steps.forEach((item) => {
    item.classList.remove("is-active");
    item.hidden = true;
  });

  form.classList.add("is-tracking-mode");
}

function renderTrackingSuccess(entry) {
  switchFormToTrackingMode();
  formMessage.textContent = "";
  formMessage.classList.add("is-success");
  formMessage.classList.remove("is-error");

  const card = document.createElement("span");
  card.className = "tracking-success";

  const title = document.createElement("strong");
  title.textContent = messages.trackingTitle;

  const text = document.createElement("span");
  text.textContent = messages.trackingText;

  const actions = document.createElement("span");
  actions.className = "tracking-success-actions";

  const openLink = document.createElement("a");
  openLink.className = "button button-small";
  openLink.href = entry.tracking_url;
  openLink.textContent = messages.viewStatus;

  const copyButton = document.createElement("button");
  copyButton.className = "button button-small button-secondary";
  copyButton.type = "button";
  copyButton.textContent = messages.copyLink;
  copyButton.addEventListener("click", async () => {
    await navigator.clipboard.writeText(absoluteUrl(entry.tracking_url));
    copyButton.textContent = messages.linkCopied;
  });

  const whatsappLink = document.createElement("a");
  whatsappLink.className = "button button-small button-secondary";
  whatsappLink.href = `https://wa.me/?text=${encodeURIComponent(absoluteUrl(entry.tracking_url))}`;
  whatsappLink.target = "_blank";
  whatsappLink.rel = "noopener noreferrer";
  whatsappLink.textContent = messages.shareWhatsApp;

  actions.append(openLink, copyButton, whatsappLink);
  card.append(title, text, actions);
  formMessage.appendChild(card);
}

function renderOpenPedidos() {
  const section = document.querySelector("#openPedidos");
  const list = document.querySelector("#openPedidosList");
  if (!section || !list) return;

  const links = getTrackingLinks();
  list.textContent = "";

  if (links.length === 0) {
    section.hidden = true;
    return;
  }

  links.slice(0, 5).forEach((entry) => {
    const card = document.createElement("article");
    card.className = "open-pedido-card";

    const copy = document.createElement("div");
    copy.className = "open-pedido-copy";

    const title = document.createElement("strong");
    title.textContent = entry.route_summary || messages.defaultRoute;

    const status = document.createElement("span");
    status.textContent = entry.status_label || messages.waitingOffers;

    const action = document.createElement("a");
    action.className = "button button-small";
    action.href = entry.tracking_url;
    action.textContent = messages.viewStatus;

    copy.append(title, status);
    card.append(copy, action);
    list.appendChild(card);
  });

  section.hidden = false;
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

function validateStep(step) {
  const activeStep = steps[step - 1];
  const requiredFields = Array.from(activeStep.querySelectorAll("[required]"));
  for (const field of requiredFields) {
    if (!field.value.trim()) {
      field.focus();
      setMessage(messages.required, "error");
      return false;
    }
  }

  if (step === 2) {
    const data = getFormData();
    if (!data.client_phone.trim() && !data.client_whatsapp.trim() && !data.customer_email.trim()) {
      setMessage(messages.contact, "error");
      return false;
    }
  }

  return true;
}

function buildPayload() {
  const data = getFormData();
  const requestedDate = data.requested_date ? `${data.requested_date}T12:00:00+00:00` : null;

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
        route_summary: buildRouteSummary(submittedData)
      };
      saveTrackingLink(trackingEntry);
      renderTrackingSuccess(trackingEntry);
      renderOpenPedidos();
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

form.addEventListener("click", (event) => {
  const next = event.target.closest("[data-next]");
  const prev = event.target.closest("[data-prev]");

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

restoreDraft();
setStep(1);
renderOpenPedidos();
