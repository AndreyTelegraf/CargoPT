const STORAGE_KEY = "cargopt_landing_request_v2";
const TRACKING_LINKS_KEY = "cargopt_tracking_links";
const pageLocale = document.body.dataset.locale || document.documentElement.lang || "ru";
const form = document.querySelector("#requestForm");
const hero = document.querySelector(".hero");
const steps = Array.from(document.querySelectorAll(".form-step"));
const stepLabel = document.querySelector("#stepLabel");
const progressFill = document.querySelector("#progressFill");
const formMessage = document.querySelector("#formMessage");
const trackingPanel = document.querySelector("#trackingPanel");
const trackingPanelBody = document.querySelector("#trackingPanelBody");
const progress = document.querySelector(".progress");
let currentStep = 1;
let activeTrackingEntry = null;
let trackingPollTimer = null;
let isSelectingLandingOffer = false;
let isSendingLandingAssignmentAction = false;

const MESSAGES = {
  pt: {
    required: "Preencha os campos obrigatórios deste passo.",
    contact: "Indique pelo menos um contacto: telefone, WhatsApp ou email.",
    submitting: "A enviar o pedido...",
    success: "Pedido enviado. Vamos encaminhá-lo para transportadores.",
    failure: "Não foi possível enviar o pedido. Verifique os campos ou tente mais tarde.",
    trackingTitle: "Acompanhe o seu pedido",
    trackingText: "Quando houver propostas, nesta mesma página poderá escolher o transportador, sem login e sem instalar nada.",
    viewStatus: "Ver estado",
    copyLink: "Copiar link",
    linkCopied: "Link copiado",
    shareWhatsApp: "Enviar por WhatsApp",
    newRequest: "← Novo pedido",
    viewOffers: "Ver propostas",
    selectOffer: "Escolher este transportador",
    selectingOffer: "A escolher...",
    retryOffer: "Tentar novamente",
    confirmDeal: "Negócio confirmado",
    failDeal: "Não chegámos a acordo com o transportador",
    sendingAction: "A enviar...",
    confirmationRecorded: "A sua confirmação foi registada. Aguardamos a confirmação do transportador.",
    statusSearching: "À procura de transportadores",
    statusAssigned: "Transportador escolhido",
    statusCompleted: "Pedido concluído",
    statusCancelled: "Pedido cancelado",
    statusNoOffers: "Sem propostas disponíveis",
    statusAwaitingConfirmation: "A aguardar confirmação do transportador",
    statusCarrierConfirmed: "Transportador confirmado",
    offersAvailable: "{count} proposta(s) disponível(eis)",
    defaultRoute: "Pedido CargoPT",
    waitingOffers: "A aguardar propostas",
    trackingEyebrow: "Estado do pedido",
    detailsTitle: "Detalhes do pedido",
    itemsLabel: "Itens",
    commentLabel: "Comentário"
  },
  en: {
    required: "Fill in the required fields for this step.",
    contact: "Add at least one contact: phone, WhatsApp or email.",
    submitting: "Sending request...",
    success: "Request sent. We will forward it to carriers.",
    failure: "Could not send the request. Check the fields or try again later.",
    trackingTitle: "Track your request",
    trackingText: "When offers arrive, you will be able to choose the carrier on this same page, without login or installing anything.",
    viewStatus: "View status",
    copyLink: "Copy link",
    linkCopied: "Link copied",
    shareWhatsApp: "Send by WhatsApp",
    newRequest: "← New request",
    viewOffers: "View offers",
    selectOffer: "Choose this carrier",
    selectingOffer: "Selecting...",
    retryOffer: "Try again",
    confirmDeal: "Deal confirmed",
    failDeal: "Could not agree with the carrier",
    sendingAction: "Sending...",
    confirmationRecorded: "Your confirmation was recorded. Waiting for carrier confirmation.",
    statusSearching: "Looking for carriers",
    statusAssigned: "Carrier selected",
    statusCompleted: "Request completed",
    statusCancelled: "Request cancelled",
    statusNoOffers: "No offers available",
    statusAwaitingConfirmation: "Waiting for carrier confirmation",
    statusCarrierConfirmed: "Carrier confirmed",
    offersAvailable: "{count} offer(s) available",
    defaultRoute: "CargoPT request",
    waitingOffers: "Waiting for offers",
    trackingEyebrow: "Request status",
    detailsTitle: "Request details",
    itemsLabel: "Items",
    commentLabel: "Comment"
  },
  ru: {
    required: "Заполните обязательные поля этого шага.",
    contact: "Укажите хотя бы один контакт: телефон, WhatsApp или email.",
    submitting: "Отправляем заявку...",
    success: "Заявка отправлена. Мы передадим её перевозчикам.",
    failure: "Не удалось отправить заявку. Проверьте поля или попробуйте позже.",
    trackingTitle: "Следите за статусом заявки",
    trackingText: "Когда появятся предложения, на этой же странице можно будет выбрать перевозчика без логина и установки приложения.",
    viewStatus: "Статус заявки",
    copyLink: "Скопировать ссылку",
    linkCopied: "Ссылка скопирована",
    shareWhatsApp: "Отправить в WhatsApp",
    newRequest: "← Новая заявка",
    viewOffers: "Смотреть предложения",
    selectOffer: "Выбрать перевозчика",
    selectingOffer: "Выбираем...",
    retryOffer: "Попробовать снова",
    confirmDeal: "Сделка подтверждена",
    failDeal: "Не договорились с перевозчиком",
    sendingAction: "Отправляем...",
    confirmationRecorded: "Ваше подтверждение сохранено. Ожидаем подтверждение перевозчика.",
    statusSearching: "Ищем перевозчиков",
    statusAssigned: "Перевозчик выбран",
    statusCompleted: "Заявка завершена",
    statusCancelled: "Заявка отменена",
    statusNoOffers: "Нет доступных предложений",
    statusAwaitingConfirmation: "Ожидаем подтверждение перевозчика",
    statusCarrierConfirmed: "Перевозчик подтверждён",
    offersAvailable: "Доступно предложений: {count}",
    defaultRoute: "Заявка CargoPT",
    waitingOffers: "Ожидаем предложения",
    trackingEyebrow: "Статус заявки",
    detailsTitle: "Детали заявки",
    itemsLabel: "Груз",
    commentLabel: "Комментарий"
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

function formatTrackingStatus(snapshot) {
  const acceptedOffers = Array.isArray(snapshot.accepted_offers) ? snapshot.accepted_offers : [];

  if (snapshot.status === "completed") {
    return messages.statusCompleted;
  }

  if (snapshot.status === "cancelled") {
    return messages.statusCancelled;
  }

  if (
    snapshot.client_confirmation_status === "confirmed" &&
    snapshot.carrier_confirmation_status === "confirmed"
  ) {
    return messages.statusCarrierConfirmed;
  }

  if (
    snapshot.client_confirmation_status === "pending" ||
    snapshot.carrier_confirmation_status === "pending" ||
    snapshot.status === "assigned_pending_confirmation"
  ) {
    return messages.statusAwaitingConfirmation;
  }

  if (["assigned", "in_progress"].includes(snapshot.status)) {
    return messages.statusAssigned;
  }

  if (acceptedOffers.length > 0) {
    return messages.offersAvailable.replace("{count}", String(acceptedOffers.length));
  }

  if (["ready_for_matching", "matching", "offered"].includes(snapshot.status)) {
    return messages.statusSearching;
  }

  if (["offers_exhausted", "expired_without_response"].includes(snapshot.status)) {
    return messages.statusNoOffers;
  }

  return messages.waitingOffers;
}

function getTrackingVisualState(entry) {
  const snapshot = entry.tracking_snapshot || {};

  if (snapshot.status === "completed") return "completed";
  if (snapshot.status === "cancelled") return "cancelled";

  if (
    snapshot.client_confirmation_status === "confirmed" &&
    snapshot.carrier_confirmation_status === "confirmed"
  ) {
    return "success";
  }

  if (
    snapshot.client_confirmation_status === "pending" ||
    snapshot.carrier_confirmation_status === "pending" ||
    snapshot.status === "assigned_pending_confirmation"
  ) {
    return "pending";
  }

  if ((entry.accepted_offers_count || 0) > 0) return "success";

  return "pending";
}

function mergeTrackingSnapshot(entry, snapshot) {
  const acceptedOffers = Array.isArray(snapshot.accepted_offers) ? snapshot.accepted_offers : [];
  return {
    ...entry,
    job_id: snapshot.job_id || entry.job_id,
    token: snapshot.tracking_token || entry.token,
    status_label: formatTrackingStatus(snapshot),
    accepted_offers_count: acceptedOffers.length,
    tracking_snapshot: snapshot,
    tracking_visual_state: getTrackingVisualState({...entry, tracking_snapshot: snapshot, accepted_offers_count: acceptedOffers.length})
  };
}

function stopTrackingPolling() {
  if (trackingPollTimer) {
    window.clearInterval(trackingPollTimer);
    trackingPollTimer = null;
  }
}

async function refreshTrackingEntry(entry, options = {}) {
  const token = entry && (entry.token || entry.tracking_token);
  if (!token) return entry;

  try {
    const response = await fetch(`/api/v1/track/${encodeURIComponent(token)}`);
    if (!response.ok) return entry;

    const snapshot = await response.json();
    const updatedEntry = mergeTrackingSnapshot(entry, snapshot);
    activeTrackingEntry = updatedEntry;
    saveTrackingLink(updatedEntry);

    if (options.rerender) {
      renderTrackingSuccess(updatedEntry);
    }

    renderOpenPedidos();
    return updatedEntry;
  } catch (error) {
    console.error(error);
    return entry;
  }
}

function startTrackingPolling(entry) {
  stopTrackingPolling();
  activeTrackingEntry = entry;
  refreshTrackingEntry(entry, {rerender: true});
  trackingPollTimer = window.setInterval(() => {
    if (activeTrackingEntry) {
      refreshTrackingEntry(activeTrackingEntry, {rerender: true});
    }
  }, 15000);
}


function restoreLatestTrackingEntry() {
  const links = getTrackingLinks();
  const latest = links.find((entry) => entry && entry.token && entry.tracking_url);
  if (!latest) return false;

  renderTrackingSuccess(latest);
  renderOpenPedidos();
  startTrackingPolling(latest);
  return true;
}



function switchFormToTrackingMode() {
  form.hidden = true;
  trackingPanel.hidden = false;
  form.classList.add("is-tracking-mode");
}

function switchTrackingToNewRequest() {
  stopTrackingPolling();

  trackingPanel.hidden = true;
  trackingPanelBody.textContent = "";
  form.hidden = false;
  form.classList.remove("is-tracking-mode");
  form.reset();
  localStorage.removeItem(STORAGE_KEY);

  steps.forEach((item) => {
    item.hidden = false;
  });

  if (progress) {
    progress.hidden = false;
  }

  setStep(1);
  renderOpenPedidos();
}

async function selectLandingOffer(offerId, button) {
  if (isSelectingLandingOffer || !activeTrackingEntry) return;

  isSelectingLandingOffer = true;
  button.disabled = true;
  button.textContent = messages.selectingOffer;

  try {
    const response = await fetch(`/api/v1/track/${encodeURIComponent(activeTrackingEntry.token)}/offers/${encodeURIComponent(offerId)}/select`, {
      method: "POST",
      headers: {"Accept": "application/json"}
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    await refreshTrackingEntry(activeTrackingEntry, {rerender: true});
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = messages.retryOffer;
  } finally {
    isSelectingLandingOffer = false;
  }
}

async function sendLandingAssignmentAction(action, button) {
  if (isSendingLandingAssignmentAction || !activeTrackingEntry) return;

  isSendingLandingAssignmentAction = true;

  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = messages.sendingAction;

  try {
    const response = await fetch(`/api/v1/track/${encodeURIComponent(activeTrackingEntry.token)}/assignment/${encodeURIComponent(action)}`, {
      method: "POST",
      headers: {"Accept": "application/json"}
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    await refreshTrackingEntry(activeTrackingEntry, {rerender: true});
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = messages.retryOffer;
    window.setTimeout(() => {
      if (!button.disabled) button.textContent = originalText;
    }, 2200);
  } finally {
    isSendingLandingAssignmentAction = false;
  }
}

function renderTrackingSuccess(entry) {
  switchFormToTrackingMode();
  formMessage.textContent = "";
  formMessage.classList.remove("is-success", "is-error");

  window.CargoPTTrackingWorkspace.render(entry, {
    container: trackingPanelBody,
    locale: localeKey,
    messages,
    onSelectOffer: selectLandingOffer,
    onAssignmentAction: sendLandingAssignmentAction
  });
}

function renderOpenPedidos() {
  const section = document.querySelector("#openPedidos");
  const list = document.querySelector("#openPedidosList");
  if (!section || !list) return;

  const links = getTrackingLinks();
  list.textContent = "";

  if (links.length === 0) {
    section.hidden = true;
    hero?.classList.remove("is-user-workspace");
    return;
  }

  links.slice(0, 5).forEach((entry) => {
    const card = document.createElement("article");
    card.className = "open-pedido-card";
    if (activeTrackingEntry && entry.token === activeTrackingEntry.token) {
      card.classList.add("is-active");
    }

    const copy = document.createElement("div");
    copy.className = "open-pedido-copy";

    const title = document.createElement("strong");
    title.textContent = entry.route_summary || messages.defaultRoute;

    const status = document.createElement("span");
    status.textContent = entry.status_label || messages.waitingOffers;

    if (entry.item_summary) {
      const items = document.createElement("span");
      items.className = "open-pedido-items";
      items.textContent = entry.item_summary;
      copy.append(title, items, status);
    } else {
      copy.append(title, status);
    }

    const action = document.createElement("button");
    action.className = "button button-small";
    action.type = "button";
    action.textContent = messages.viewStatus;
    action.addEventListener("click", () => {
      activeTrackingEntry = entry;
      renderTrackingSuccess(entry);
      startTrackingPolling(entry);
      renderOpenPedidos();
    });

    card.append(copy, action);
    card.addEventListener("click", (event) => {
      if (event.target.closest("button, a")) return;
      activeTrackingEntry = entry;
      renderTrackingSuccess(entry);
      startTrackingPolling(entry);
      renderOpenPedidos();
    });
    list.appendChild(card);
  });

  section.hidden = false;
  hero?.classList.add("is-user-workspace");
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
      renderTrackingSuccess(trackingEntry);
      renderOpenPedidos();
      startTrackingPolling(trackingEntry);
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
  switchTrackingToNewRequest();
  hero?.classList.add("is-user-workspace");
});

form.addEventListener("click", (event) => {
  const next = event.target.closest("[data-next]");
  const prev = event.target.closest("[data-prev]");
  const newRequest = event.target.closest("[data-new-request]");

  if (newRequest) {
    switchTrackingToNewRequest();
    hero?.classList.add("is-user-workspace");
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

if (!restoreLatestTrackingEntry()) {
  restoreDraft();
  setStep(1);
  renderOpenPedidos();
}
