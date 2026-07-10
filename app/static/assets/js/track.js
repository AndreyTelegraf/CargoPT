
const trackingPanelBody = document.querySelector("#trackingPanelBody");
const errorCard = document.querySelector("#errorCard");
const trackPedidosList = document.querySelector("#trackPedidosList");
const copyTrackingLink = document.querySelector("#copyTrackingLink");

const pathParts = window.location.pathname.split("/").filter(Boolean);
const supportedLocales = new Set(["en", "ru"]);
const pageLocale = supportedLocales.has(pathParts[0]) ? pathParts[0] : "pt";
const trackSegmentIndex = pageLocale === "pt" ? 0 : 1;
const token = decodeURIComponent(pathParts.slice(trackSegmentIndex + 1).join("/"));
const trackBasePath = pageLocale === "pt" ? "/track" : `/${pageLocale}/track`;
const numberLocale = {
  pt: "pt-PT",
  en: "en-GB",
  ru: "ru-RU"
}[pageLocale];

const localizedTrackPaths = {
  PT: "/track",
  EN: "/en/track",
  RU: "/ru/track"
};

function updateLocaleLinks() {
  document.querySelectorAll(".locale-menu a").forEach((link) => {
    const basePath = localizedTrackPaths[link.textContent.trim()];
    if (!basePath) return;

    link.href = token
      ? `${basePath}/${encodeURIComponent(token)}`
      : `${basePath}/`;
  });
}

updateLocaleLinks();

function absoluteTrackingUrl() {
  return new URL(`${trackBasePath}/${token}`, window.location.origin).toString();
}

if (copyTrackingLink) {
  copyTrackingLink.addEventListener("click", async () => {
    await navigator.clipboard.writeText(absoluteTrackingUrl());
    copyTrackingLink.textContent = messages.trackLinkCopied;

    clearTimeout(copyTrackingLink._copyResetTimer);
    copyTrackingLink._copyResetTimer = setTimeout(() => {
      if (copyTrackingLink.isConnected) {
        copyTrackingLink.textContent = messages.copyTrackLink;
      }
    }, 3000);
  });
}

const TRACKING_LINKS_KEY = "cargopt_tracking_links";

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
  if (!entry.token) return;

  const current = {
    job_id: entry.job_id,
    tracking_url: entry.tracking_url,
    token: entry.token,
    route_summary: entry.route_summary,
    item_summary: entry.item_summary,
    status_label: entry.status_label
  };

  const links = getTrackingLinks();
  const existingIndex = links.findIndex((item) => item.token === entry.token);

  if (existingIndex >= 0) {
    links[existingIndex] = {...links[existingIndex], ...current};
  } else {
    links.unshift(current);
  }

  localStorage.setItem(TRACKING_LINKS_KEY, JSON.stringify(links.slice(0, 20)));
}

function renderOpenPedidosNavigation(activeEntry) {
  if (!trackPedidosList) return;

  const links = getTrackingLinks();
  trackPedidosList.textContent = "";

  if (!links.length) {
    const empty = document.createElement("p");
    empty.className = "track-offer-nav-empty";
    empty.textContent = messages.noSavedRequests;
    trackPedidosList.appendChild(empty);
    return;
  }

  links.slice(0, 5).forEach((storedEntry) => {
    const isActive = storedEntry.token === activeEntry.token;
    const entry = isActive ? {...storedEntry, ...activeEntry} : storedEntry;
    const card = document.createElement("article");
    card.className = "track-offer-nav-card";
    card.classList.toggle("is-chosen", isActive);
    card.tabIndex = 0;

    const top = document.createElement("div");
    top.className = "track-offer-nav-top";

    const route = document.createElement("strong");
    const routeLabel = entry.route_summary || messages.defaultRoute;
    route.textContent = entry.job_id ? `#${entry.job_id} · ${routeLabel}` : routeLabel;

    const status = document.createElement("span");
    status.className = "track-offer-nav-price";
    status.textContent = isActive ? messages.currentRequest : messages.openRequest;

    top.append(route, status);

    const line = document.createElement("div");
    line.className = "track-offer-nav-status";

    const dot = document.createElement("span");
    dot.className = `tracking-status-dot tracking-status-dot-${entry.status_dot_state || "searching"}`;
    dot.setAttribute("aria-hidden", "true");

    const statusText = document.createElement("span");
    statusText.textContent = entry.status_label || messages.waitingOffers;

    line.append(dot, statusText);

    card.appendChild(top);

    if (entry.item_summary) {
      const meta = document.createElement("div");
      meta.className = "track-offer-nav-meta";
      meta.textContent = entry.item_summary;
      card.appendChild(meta);
    }

    card.appendChild(line);

    const open = () => {
      if (entry.tracking_url) window.location.href = entry.tracking_url;
    };

    card.addEventListener("click", (event) => {
      if (event.target.closest("button, a")) return;
      open();
    });

    card.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      open();
    });

    trackPedidosList.appendChild(card);
  });
}


const POLL_INTERVAL_MS = 5000;
let activeTrackingEntry = null;
let activeSidebarOfferId = null;
let isSelectingOffer = false;
let isSendingAssignmentAction = false;

const MESSAGE_SETS = {
  pt: {
    copyTrackLink: "Copiar track link",
    trackLinkCopied: "Track link copiado",
    noSavedRequests: "Ainda não há pedidos guardados neste dispositivo.",
    currentRequest: "Atual",
    openRequest: "Abrir",
    statusSearching: "À procura de transportadores",
    statusAssigned: "Transportador escolhido",
    statusCompleted: "Pedido concluído",
    statusCancelled: "Pedido cancelado",
    statusNoOffers: "Sem ofertas disponíveis",
    statusAwaitingConfirmation: "A aguardar confirmação do transportador",
    statusCarrierConfirmed: "Transportador confirmado",
    offersAvailable: "{count} oferta(s) disponível(eis)",
    defaultRoute: "Pedido CargoPT",
    waitingOffers: "A aguardar ofertas",
    retryOffer: "Tentar novamente",
    selectingOffer: "A escolher...",
    sendingAction: "A enviar...",
    defaultCarrier: "Transportador",
    trackingEyebrow: "Estado do pedido",
    trackingTitle: "Acompanhe o seu pedido",
    trackingText: "Quando houver propostas, poderá escolher o transportador nesta página, sem login e sem instalar nada.",
    viewStatus: "Ver estado",
    copyLink: "Copiar link",
    linkCopied: "Link copiado",
    shareWhatsApp: "Enviar por WhatsApp",
    newRequest: "← Novo pedido",
    viewOffers: "Ver ofertas",
    selectOffer: "Escolher esta oferta",
    confirmDeal: "Negócio confirmado",
    failDeal: "Não chegámos a acordo com o transportador",
    failDealShort: "Não chegámos a acordo",
    confirmationRecorded: "A sua confirmação foi registada. Aguardamos a confirmação do transportador.",
    detailsTitle: "Detalhes do pedido",
    itemsLabel: "Itens",
    commentLabel: "Comentário",
    contactLabel: "Contacto",
    phoneLabel: "Telefone",
    telegramLabel: "Telegram",
    loadersLabel: "Ajudantes",
    tailLiftLabel: "Plataforma elevatória",
    craneLabel: "Grua",
    mobileLiftLabel: "Elevador exterior",
    selectedOfferLabel: "Oferta selecionada"
  },

  en: {
    copyTrackLink: "Copy tracking link",
    trackLinkCopied: "Tracking link copied",
    noSavedRequests: "There are no requests saved on this device yet.",
    currentRequest: "Current",
    openRequest: "Open",
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
    retryOffer: "Try again",
    selectingOffer: "Selecting...",
    sendingAction: "Sending...",
    defaultCarrier: "Carrier",
    trackingEyebrow: "Request status",
    trackingTitle: "Track your request",
    trackingText: "When offers arrive, you can choose a carrier on this page without logging in or installing anything.",
    viewStatus: "View status",
    copyLink: "Copy link",
    linkCopied: "Link copied",
    shareWhatsApp: "Share via WhatsApp",
    newRequest: "← New request",
    viewOffers: "View offers",
    selectOffer: "Choose this offer",
    confirmDeal: "Deal confirmed",
    failDeal: "We did not reach an agreement with the carrier",
    failDealShort: "No agreement reached",
    confirmationRecorded: "Your confirmation has been recorded. We are waiting for the carrier's confirmation.",
    detailsTitle: "Request details",
    itemsLabel: "Items",
    commentLabel: "Comment",
    contactLabel: "Contact",
    phoneLabel: "Phone",
    telegramLabel: "Telegram",
    loadersLabel: "Helpers",
    tailLiftLabel: "Tail lift",
    craneLabel: "Crane",
    mobileLiftLabel: "External lift",
    selectedOfferLabel: "Selected offer"
  },

  ru: {
    copyTrackLink: "Скопировать ссылку",
    trackLinkCopied: "Ссылка скопирована",
    noSavedRequests: "На этом устройстве пока нет сохранённых заявок.",
    currentRequest: "Текущая",
    openRequest: "Открыть",
    statusSearching: "Ищем перевозчиков",
    statusAssigned: "Перевозчик выбран",
    statusCompleted: "Заявка завершена",
    statusCancelled: "Заявка отменена",
    statusNoOffers: "Нет доступных предложений",
    statusAwaitingConfirmation: "Ожидаем подтверждения перевозчика",
    statusCarrierConfirmed: "Перевозчик подтвердил заказ",
    offersAvailable: "Доступно предложений: {count}",
    defaultRoute: "Заявка CargoPT",
    waitingOffers: "Ожидаем предложения",
    retryOffer: "Попробовать снова",
    selectingOffer: "Выбираем...",
    sendingAction: "Отправляем...",
    defaultCarrier: "Перевозчик",
    trackingEyebrow: "Статус заявки",
    trackingTitle: "Следите за своей заявкой",
    trackingText: "Когда поступят предложения, вы сможете выбрать перевозчика на этой странице без регистрации и установки приложений.",
    viewStatus: "Посмотреть статус",
    copyLink: "Скопировать ссылку",
    linkCopied: "Ссылка скопирована",
    shareWhatsApp: "Отправить в WhatsApp",
    newRequest: "← Новая заявка",
    viewOffers: "Посмотреть предложения",
    selectOffer: "Выбрать это предложение",
    confirmDeal: "Заказ подтверждён",
    failDeal: "Договориться с перевозчиком не удалось",
    failDealShort: "Не удалось договориться",
    confirmationRecorded: "Ваше подтверждение сохранено. Ожидаем подтверждения перевозчика.",
    detailsTitle: "Детали заявки",
    itemsLabel: "Что перевезти",
    commentLabel: "Комментарий",
    contactLabel: "Контакт",
    phoneLabel: "Телефон",
    telegramLabel: "Telegram",
    loadersLabel: "Грузчики",
    tailLiftLabel: "Гидроборт",
    craneLabel: "Кран",
    mobileLiftLabel: "Внешний подъёмник",
    selectedOfferLabel: "Выбранное предложение"
  }
};

const messages = MESSAGE_SETS[pageLocale] || MESSAGE_SETS.pt;

function formatSidebarPrice(priceCents) {
  if (priceCents == null) return "– €";
  return new Intl.NumberFormat(numberLocale).format(priceCents / 100) + " €";
}

function buildSidebarOfferSummary(offer, index) {
  if (!offer) return null;

  return {
    company_name: offer.company_name || `${messages.defaultCarrier} ${index + 1}`,
    price_label: formatSidebarPrice(offer.price_cents),
    vehicle_label: [
      offer.vehicle_type,
      offer.payload_kg ? offer.payload_kg + " kg" : null,
      offer.volume_m3 ? offer.volume_m3 + " m³" : null
    ].filter(Boolean).join(" • ")
  };
}

function withSelectedOfferSummary(entry) {
  const offers = entry.tracking_snapshot?.accepted_offers || [];
  const activeOffer = offers.find((offer) => offer.offer_id === activeSidebarOfferId);
  const activeIndex = offers.findIndex((offer) => offer.offer_id === activeSidebarOfferId);

  return {
    ...entry,
    selected_offer_summary: buildSidebarOfferSummary(activeOffer, activeIndex),
  };
}

function renderTrackingWorkspace(entry) {
  activeTrackingEntry = withSelectedOfferSummary(entry);

  window.CargoPTTrackingWorkspace.render(activeTrackingEntry, {
    container: trackingPanelBody,
    locale: numberLocale,
    messages,
    hideStatusAction: true,
    hideShareActions: true,
    onSelectOffer: selectOffer,
    onAssignmentAction: sendAssignmentAction
  });
}

function getTrackingStatusDotState(snapshot, acceptedOffers) {
  if (snapshot.status === "cancelled") return "cancelled";
  if (["offers_exhausted", "expired_without_response"].includes(snapshot.status)) return "cancelled";
  if (snapshot.status === "completed") return "success";
  if (snapshot.client_confirmation_status === "confirmed" && snapshot.carrier_confirmation_status === "confirmed") return "success";
  if (snapshot.client_confirmation_status === "pending" || snapshot.carrier_confirmation_status === "pending") return "pending";
  if (["assigned_pending_confirmation", "assigned", "in_progress"].includes(snapshot.status)) return "pending";
  if (acceptedOffers.length > 0) return "success";
  if (["ready_for_matching", "matching", "offered"].includes(snapshot.status)) return "searching";
  return "completed";
}

function formatTrackingStatus(snapshot) {
  const acceptedOffers = Array.isArray(snapshot.accepted_offers) ? snapshot.accepted_offers : [];

  if (snapshot.status === "completed") return messages.statusCompleted;
  if (snapshot.status === "cancelled") return messages.statusCancelled;

  if (snapshot.client_confirmation_status === "confirmed" && snapshot.carrier_confirmation_status === "confirmed") return messages.statusCarrierConfirmed;
  if (snapshot.client_confirmation_status === "pending" || snapshot.carrier_confirmation_status === "pending") return messages.statusAwaitingConfirmation;
  if (["assigned_pending_confirmation", "assigned", "in_progress"].includes(snapshot.status)) return messages.statusAssigned;

  if (acceptedOffers.length > 0) return messages.offersAvailable.replace("{count}", String(acceptedOffers.length));
  if (["ready_for_matching", "matching", "offered"].includes(snapshot.status)) return messages.statusSearching;
  if (["offers_exhausted", "expired_without_response"].includes(snapshot.status)) return messages.statusNoOffers;

  return messages.waitingOffers;
}

function mergeTrackingSnapshot(snapshot) {
  const acceptedOffers = Array.isArray(snapshot.accepted_offers) ? snapshot.accepted_offers : [];
  const entry = {
    job_id: snapshot.job_id,
    token: snapshot.tracking_token || token,
    tracking_url: `${trackBasePath}/${snapshot.tracking_token || token}`,
    status_label: formatTrackingStatus(snapshot),
    status_dot_state: getTrackingStatusDotState(snapshot, acceptedOffers),
    accepted_offers_count: acceptedOffers.length,
    route_summary: snapshot.route_summary || messages.defaultRoute,
    tracking_snapshot: snapshot
  };

  entry.tracking_visual_state = window.CargoPTTrackingWorkspace.getVisualState(entry);
  return entry;
}

async function loadTrackingState() {
  if (!token) throw new Error("missing tracking token");

  const response = await fetch(`/api/v1/track/${encodeURIComponent(token)}`, {
    headers: {"Accept": "application/json"}
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function refresh() {
  try {
    const snapshot = await loadTrackingState();
    activeTrackingEntry = mergeTrackingSnapshot(snapshot);
    errorCard.hidden = true;

    saveTrackingLink(activeTrackingEntry);
    renderOpenPedidosNavigation(activeTrackingEntry);
    renderTrackingWorkspace(activeTrackingEntry);
  } catch (error) {
    console.error(error);
    errorCard.hidden = false;
    trackingPanelBody.textContent = "";
  }
}

async function selectOffer(offerId, button) {
  if (isSelectingOffer || !activeTrackingEntry) return;

  isSelectingOffer = true;
  button.disabled = true;
  button.textContent = messages.selectingOffer;

  try {
    const response = await fetch(`/api/v1/track/${encodeURIComponent(activeTrackingEntry.token)}/offers/${encodeURIComponent(offerId)}/select`, {
      method: "POST",
      headers: {"Accept": "application/json"}
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    await refresh();
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = messages.retryOffer;
  } finally {
    isSelectingOffer = false;
  }
}

async function sendAssignmentAction(action, button) {
  if (isSendingAssignmentAction || !activeTrackingEntry) return;

  isSendingAssignmentAction = true;

  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = messages.sendingAction;

  try {
    const response = await fetch(`/api/v1/track/${encodeURIComponent(activeTrackingEntry.token)}/assignment/${encodeURIComponent(action)}`, {
      method: "POST",
      headers: {"Accept": "application/json"}
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    await refresh();
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = messages.retryOffer;
    window.setTimeout(() => {
      if (!button.disabled) button.textContent = originalText;
    }, 2200);
  } finally {
    isSendingAssignmentAction = false;
  }
}

refresh();
window.setInterval(refresh, POLL_INTERVAL_MS);
