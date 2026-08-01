
const trackingPanelBody = document.querySelector("#trackingPanelBody");
const trackingProgressHeader = document.querySelector("#trackingProgressHeader");
const trackWorkspaceShell = document.querySelector(".track-workspace-shell");
const otherRequestsPanel = document.querySelector("#otherRequestsPanel");
const otherRequestsToggle = document.querySelector("#otherRequestsToggle");
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

const STATUS_CHROME_COLORS = {
  searching: "#2B6FD6",
  pending: "#d97706",
  success: "#0F8A5F",
  error: "#D92D20",
  cancelled: "#D92D20"
};

function buildStatusFaviconSvg(color) {
  return `<svg xmlns="http://www.w3.org/2000/svg"
    width="512"
    height="512"
    viewBox="90 56 78 78">
    <circle
      cx="129.3"
      cy="95.86"
      r="36.77"
      fill="${color}"/>
    <path
      fill="#ffffff"
      d="M110.71,95.53c-1.22-1.35-1.23-3-.02-4.07,1.37-1.22,2.99-.86,4.18.47l11.64,13.01,18.06-27.32c.88-1.33,2.51-1.67,3.78-.87,1.24.79,1.75,2.46.84,3.84l-20.12,30.45c-.48.72-1.35,1.06-1.98,1.1-.86.06-1.67-.23-2.29-.92l-14.09-15.69Z"/>
    <path
      fill="#fbfcfc"
      d="M126.88,113.56c-1.21,0-2.31-.49-3.12-1.4l-14.09-15.69c-.89-.99-1.34-2.17-1.28-3.32.06-1.04.55-2.02,1.37-2.75,1.89-1.67,4.36-1.43,6.17.59l10.42,11.64,17.05-25.79c1.28-1.94,3.79-2.5,5.71-1.28.95.6,1.64,1.58,1.87,2.67.23,1.08.02,2.2-.61,3.14l-20.12,30.45c-.78,1.18-2.09,1.67-3.07,1.73-.1,0-.21.01-.31.01ZM112.52,92.13c-.3,0-.6.13-.89.39-.26.23-.41.5-.42.8-.02.4.18.85.56,1.27h0s14.09,15.69,14.09,15.69c.3.34.64.48,1.15.45.26-.02.7-.17.9-.47l20.12-30.45c.26-.39.25-.75.2-.99-.08-.36-.3-.68-.62-.88-.63-.4-1.41-.21-1.85.45l-19.07,28.85-12.86-14.37c-.44-.49-.88-.74-1.3-.74Z"/>
  </svg>`;
}

function updateStatusChrome(statusDotState) {
  const color =
    STATUS_CHROME_COLORS[statusDotState]
    || STATUS_CHROME_COLORS.searching;

  const favicon = document.querySelector(
    'link[rel="icon"][type="image/svg+xml"]'
  );

  if (favicon) {
    const svg = buildStatusFaviconSvg(color);
    favicon.href =
      `data:image/svg+xml,${encodeURIComponent(svg)}`;
  }

  const themeColor = document.querySelector(
    'meta[name="theme-color"]'
  );

  if (themeColor) {
    themeColor.content = color;
  }
}

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

function copyTextWithLegacyFallback(value) {
  const textarea = document.createElement("textarea");

  try {
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.opacity = "0";
    textarea.style.pointerEvents = "none";

    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);

    return document.execCommand("copy") === true;
  } catch {
    return false;
  } finally {
    textarea.remove();
  }
}

async function copyTrackingUrl() {
  const value = absoluteTrackingUrl();
  const clipboard = navigator.clipboard;

  if (
    clipboard
    && typeof clipboard.writeText === "function"
  ) {
    try {
      await clipboard.writeText(value);
      return true;
    } catch {
      return copyTextWithLegacyFallback(value);
    }
  }

  return copyTextWithLegacyFallback(value);
}

if (copyTrackingLink) {
  copyTrackingLink.addEventListener("click", async () => {
    const copied = await copyTrackingUrl();

    if (!copied) return;

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

function normalizeTrackingLink(entry) {
  if (!entry || !entry.token) return null;

  return {
    job_id: entry.job_id ?? null,
    tracking_url:
      entry.tracking_url
      || `${trackBasePath}/${encodeURIComponent(entry.token)}`,
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

  const links = getTrackingLinks();
  const existingIndex = links.findIndex(
    (item) => item.token === current.token
  );

  if (existingIndex >= 0) {
    links[existingIndex] = current;
  } else {
    links.unshift(current);
  }

  localStorage.setItem(
    TRACKING_LINKS_KEY,
    JSON.stringify(links.slice(0, 20))
  );
}

function getVisibleTrackingLinks() {
  return getTrackingLinks().slice(0, 5);
}

function getOtherTrackingLinks() {
  return getTrackingLinks()
    .filter((entry) => entry?.token && entry.token !== token)
    .slice(0, 5);
}

function setOtherRequestsExpanded(isExpanded) {
  if (!otherRequestsPanel || !otherRequestsToggle) return;

  otherRequestsPanel.classList.toggle(
    "is-mobile-expanded",
    isExpanded
  );

  otherRequestsToggle.setAttribute(
    "aria-expanded",
    String(isExpanded)
  );
}

if (otherRequestsToggle) {
  otherRequestsToggle.addEventListener("click", () => {
    const isExpanded =
      otherRequestsPanel?.classList.contains(
        "is-mobile-expanded"
      ) || false;

    setOtherRequestsExpanded(!isExpanded);
  });
}

function renderOpenPedidosNavigation() {
  if (
    !trackPedidosList
    || !otherRequestsPanel
    || !trackWorkspaceShell
  ) return;

  const links = getOtherTrackingLinks();
  const hasOtherRequests = links.length > 0;

  trackPedidosList.textContent = "";

  if (otherRequestsToggle) {
    otherRequestsToggle.textContent =
      messages.otherRequestsLabel.replace(
        "{count}",
        String(links.length)
      );
  }

  otherRequestsPanel.hidden = !hasOtherRequests;
  trackWorkspaceShell.classList.toggle(
    "has-no-other-requests",
    !hasOtherRequests
  );

  if (!hasOtherRequests) {
    setOtherRequestsExpanded(false);
    return;
  }

  links.forEach((storedEntry) => {
    const liveEntry = liveEntriesByToken.get(storedEntry.token);

    const entry = liveEntry
      ? {
          ...storedEntry,
          ...liveEntry,
          item_summary:
            storedEntry.item_summary || liveEntry.item_summary
        }
      : storedEntry;

    const card = document.createElement("article");
    card.className = "track-offer-nav-card";
    card.setAttribute("role", "link");
    card.tabIndex = 0;

    const top = document.createElement("div");
    top.className = "track-offer-nav-top";

    const route = document.createElement("strong");
    const routeLabel =
      entry.route_summary || messages.defaultRoute;

    route.textContent = entry.job_id
      ? `#${entry.job_id} · ${routeLabel}`
      : routeLabel;

    const status = document.createElement("span");
    const hasAcceptedOffers =
      Number(entry.accepted_offers_count || 0) > 0;

    status.className = "track-offer-nav-price";

    if (hasAcceptedOffers) {
      status.classList.add("track-offer-nav-badge");
      status.textContent = messages.offerAvailableBadge;
    } else {
      status.textContent = messages.openRequest;
    }

    top.append(route, status);

    const line = document.createElement("div");
    line.className = "track-offer-nav-status";

    const dot = document.createElement("span");
    dot.className = "tracking-status-dot";

    if (liveEntry?.status_dot_state) {
      dot.classList.add(
        `tracking-status-dot-${liveEntry.status_dot_state}`
      );
    }

    dot.setAttribute("aria-hidden", "true");

    const statusText = document.createElement("span");
    statusText.textContent =
      liveEntry?.status_label || messages.waitingOffers;

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
      if (entry.tracking_url) {
        window.location.href = entry.tracking_url;
      }
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
const SAVED_REQUESTS_POLL_INTERVAL_MS = 30000;

const liveEntriesByToken = new Map();

let isRefreshingActiveTrackingEntry = false;
let isRefreshingSavedTrackingEntries = false;
let activeSidebarOfferId = null;
let isSelectingOffer = false;
let isSendingAssignmentAction = false;
let isSendingCompletionAction = false;

const MESSAGE_SETS = {
  pt: {
    copyTrackLink: "Copiar track link",
    trackLinkCopied: "Track link copiado",
    noSavedRequests: "Ainda não há pedidos guardados neste dispositivo.",
    currentRequest: "Atual",
    openRequest: "Abrir",
    offerAvailableBadge: "Há proposta",
    otherRequestsLabel: "Outros pedidos ({count})",
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
    allPortugalLabel: "Todo o Portugal",
    experienceSinceLabel: "Transportes desde {year}",
    trackingEyebrow: "Estado do pedido",
    trackingTitle: "Acompanhe o seu pedido",
    trackingText: "Quando houver propostas, poderá escolher o transportador nesta página, sem login e sem instalar nada.",
    searchingTitle: "Pedido enviado com sucesso",
    searchingText: "Estamos a procurar transportadores adequados. Pode fechar esta página: o pedido ficou guardado em «Meus pedidos» neste navegador. Guarde também este link para abrir o pedido noutro dispositivo.",
    offersTitle: "Propostas",
    waitingTitle: "Ainda não recebemos propostas.",
    waitingText: "Estamos à procura de transportadores.",
    waitingNote: "Isto normalmente demora apenas alguns minutos.",
    closedRequestText: "Este pedido já não está ativo.",
    noOffersText: "Não recebemos propostas para este pedido.",
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
    confirmationCompleted: "A confirmação de ambas as partes foi registada. O transporte está confirmado.",
    completionPrompt: "O transporte foi concluído?",
    completionConfirm: "Transporte concluído",
    completionProblem: "Existe um problema",
    completionRecorded: "A sua resposta foi guardada. Aguardamos a confirmação do transportador.",
    completionProblemRecorded: "O problema foi registado. A CargoPT irá verificar a situação.",
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
    selectedOfferLabel: "Oferta selecionada",
    priceLabel: "Preço",
    vehicleDetailsLabel: "Veículo e capacidade",
    vehicleLabel: "Veículo",
    payloadLabel: "Carga",
    volumeLabel: "Volume",
    equipmentLabel: "Equipamento",
    carrierContactLabel: "Contacto do transportador",
    carrierNoteLabel: "Nota do transportador"
  },

  en: {
    copyTrackLink: "Copy tracking link",
    trackLinkCopied: "Tracking link copied",
    noSavedRequests: "There are no requests saved on this device yet.",
    currentRequest: "Current",
    openRequest: "Open",
    offerAvailableBadge: "Offer available",
    otherRequestsLabel: "Other requests ({count})",
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
    allPortugalLabel: "All Portugal",
    experienceSinceLabel: "In transport since {year}",
    trackingEyebrow: "Request status",
    trackingTitle: "Track your request",
    trackingText: "When offers arrive, you can choose a carrier on this page without logging in or installing anything.",
    searchingTitle: "Request submitted successfully",
    searchingText: "We are looking for suitable carriers. You can close this page: the request is saved under “My requests” in this browser. Save this link as well to open the request on another device.",
    offersTitle: "Offers",
    waitingTitle: "We have not received any offers yet.",
    waitingText: "We are looking for suitable carriers.",
    waitingNote: "This usually takes only a few minutes.",
    closedRequestText: "This request is no longer active.",
    noOffersText: "We did not receive any offers for this request.",
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
    confirmationCompleted: "Both confirmations have been recorded. The transport is confirmed.",
    completionPrompt: "Was the transport completed?",
    completionConfirm: "Transport completed",
    completionProblem: "There is a problem",
    completionRecorded: "Your response was saved. We are waiting for the carrier's confirmation.",
    completionProblemRecorded: "The problem was recorded. CargoPT will review the situation.",
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
    selectedOfferLabel: "Selected offer",
    priceLabel: "Price",
    vehicleDetailsLabel: "Vehicle and capacity",
    vehicleLabel: "Vehicle",
    payloadLabel: "Payload",
    volumeLabel: "Volume",
    equipmentLabel: "Equipment",
    carrierContactLabel: "Carrier contact",
    carrierNoteLabel: "Carrier note"
  },

  ru: {
    copyTrackLink: "Скопировать ссылку",
    trackLinkCopied: "Ссылка скопирована",
    noSavedRequests: "На этом устройстве пока нет сохранённых заявок.",
    currentRequest: "Текущая",
    openRequest: "Открыть",
    offerAvailableBadge: "Есть предложение",
    otherRequestsLabel: "Другие заявки ({count})",
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
    allPortugalLabel: "Вся Португалия",
    experienceSinceLabel: "В перевозках с {year} года",
    trackingEyebrow: "Статус заявки",
    trackingTitle: "Следите за своей заявкой",
    trackingText: "Когда поступят предложения, вы сможете выбрать перевозчика на этой странице без регистрации и установки приложений.",
    searchingTitle: "Заявка успешно отправлена",
    searchingText: "Мы ищем подходящих перевозчиков. Эту страницу можно закрыть: заявка сохранена в разделе «Мои заявки» в этом браузере. Сохраните также ссылку, чтобы открыть заявку на другом устройстве.",
    offersTitle: "Предложения",
    waitingTitle: "Предложений пока нет.",
    waitingText: "Мы ищем подходящих перевозчиков.",
    waitingNote: "Обычно это занимает всего несколько минут.",
    closedRequestText: "Эта заявка больше не активна.",
    noOffersText: "На эту заявку не поступило предложений.",
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
    confirmationCompleted: "Обе стороны подтвердили заказ. Перевозка подтверждена.",
    completionPrompt: "Перевозка завершена?",
    completionConfirm: "Перевозка завершена",
    completionProblem: "Возникла проблема",
    completionRecorded: "Ваш ответ сохранён. Ожидаем подтверждение перевозчика.",
    completionProblemRecorded: "Проблема зафиксирована. CargoPT проверит ситуацию.",
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
    selectedOfferLabel: "Выбранное предложение",
    priceLabel: "Цена",
    vehicleDetailsLabel: "Машина и вместимость",
    vehicleLabel: "Машина",
    payloadLabel: "Грузоподъёмность",
    volumeLabel: "Объём",
    equipmentLabel: "Оборудование",
    carrierContactLabel: "Контакт перевозчика",
    carrierNoteLabel: "Комментарий перевозчика"
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

function renderTrackingProgress(entry) {
  if (!trackingProgressHeader) return;

  if (!window.CargoPTProgressHeader) {
    throw new Error("tracking progress header component unavailable");
  }

  window.CargoPTProgressHeader.render(entry, {
    container: trackingProgressHeader
  });
}

function renderTrackingWorkspace(entry) {
  const workspaceEntry = withSelectedOfferSummary(entry);

  renderTrackingProgress(workspaceEntry);

  window.CargoPTTrackingWorkspace.render(workspaceEntry, {
    container: trackingPanelBody,
    locale: numberLocale,
    messages,
    hideStatusAction: true,
    hideShareActions: true,
    onSelectOffer: selectOffer,
    onAssignmentAction: sendAssignmentAction,
    onCompletionAction: sendCompletionAction
  });
}

function getTrackingStatusDotState(snapshot, acceptedOffers) {
  if (snapshot.status === "cancelled") return "cancelled";
  if (["offers_exhausted", "expired_without_response"].includes(snapshot.status)) return "error";
  if (snapshot.status === "no_carriers_found") return "searching";
  if (snapshot.status === "completed") return "success";
  if (snapshot.client_confirmation_status === "confirmed" && snapshot.carrier_confirmation_status === "confirmed") return "success";
  if (snapshot.client_confirmation_status === "pending" || snapshot.carrier_confirmation_status === "pending") return "pending";
  if (["assigned_pending_confirmation", "assigned", "in_progress"].includes(snapshot.status)) return "pending";
  if (acceptedOffers.length > 0) return "success";
  if (["ready_for_matching", "matching", "offered", "manual_review_required"].includes(snapshot.status)) return "searching";
  return "searching";
}

function formatTrackingStatus(snapshot) {
  const acceptedOffers = Array.isArray(snapshot.accepted_offers) ? snapshot.accepted_offers : [];

  if (snapshot.status === "completed") return messages.statusCompleted;
  if (snapshot.status === "cancelled") return messages.statusCancelled;

  if (snapshot.client_confirmation_status === "confirmed" && snapshot.carrier_confirmation_status === "confirmed") return messages.statusCarrierConfirmed;
  if (snapshot.client_confirmation_status === "pending" || snapshot.carrier_confirmation_status === "pending") return messages.statusAwaitingConfirmation;
  if (["assigned_pending_confirmation", "assigned", "in_progress"].includes(snapshot.status)) return messages.statusAssigned;

  if (acceptedOffers.length > 0) return messages.offersAvailable.replace("{count}", String(acceptedOffers.length));
  if (["ready_for_matching", "matching", "offered", "manual_review_required"].includes(snapshot.status)) return messages.statusSearching;
  if (["no_carriers_found", "offers_exhausted", "expired_without_response"].includes(snapshot.status)) return messages.statusNoOffers;

  return messages.waitingOffers;
}

function buildTrackingEntry(snapshot, fallbackToken) {
  const acceptedOffers = Array.isArray(snapshot.accepted_offers) ? snapshot.accepted_offers : [];
  const isSearching =
    acceptedOffers.length === 0
    && ["ready_for_matching", "matching", "offered", "manual_review_required"].includes(snapshot.status);

  const entry = {
    job_id: snapshot.job_id,
    token: snapshot.tracking_token || fallbackToken,
    tracking_url:
      `${trackBasePath}/${snapshot.tracking_token || fallbackToken}`,
    status_label: formatTrackingStatus(snapshot),
    status_dot_state: getTrackingStatusDotState(snapshot, acceptedOffers),
    status_title: isSearching ? messages.searchingTitle : null,
    status_text: isSearching ? messages.searchingText : null,
    accepted_offers_count: acceptedOffers.length,
    route_summary: snapshot.route_summary || messages.defaultRoute,
    tracking_snapshot: snapshot
  };

  entry.tracking_visual_state = window.CargoPTTrackingWorkspace.getVisualState(entry);
  return entry;
}

async function loadTrackingSnapshot(requestToken) {
  if (!requestToken) {
    throw new Error("missing tracking token");
  }

  const response = await fetch(
    `/api/v1/track/${encodeURIComponent(requestToken)}`,
    {headers: {"Accept": "application/json"}}
  );

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

async function refreshTrackingToken(requestToken) {
  const snapshot = await loadTrackingSnapshot(requestToken);
  const entry = buildTrackingEntry(snapshot, requestToken);

  liveEntriesByToken.set(requestToken, entry);

  if (requestToken === token) {
    updateStatusChrome(entry.status_dot_state);
  }

  return entry;
}

async function refreshVisibleTrackingEntries({
  includeActive = true
} = {}) {
  const links = getVisibleTrackingLinks();

  return Promise.allSettled(
    links.map((storedEntry) => {
      if (!includeActive && storedEntry.token === token) {
        return Promise.resolve(null);
      }

      return refreshTrackingToken(storedEntry.token);
    })
  );
}

function getActiveTrackingEntry() {
  return liveEntriesByToken.get(token) || null;
}

async function bootstrapTrackingPage() {
  try {
    await refreshTrackingToken(token);
    await refreshVisibleTrackingEntries({
      includeActive: false
    });

    const activeEntry = getActiveTrackingEntry();

    if (!activeEntry) {
      throw new Error("active tracking entry unavailable");
    }

    saveTrackingLink(activeEntry);
    errorCard.hidden = true;

    renderOpenPedidosNavigation();
    renderTrackingWorkspace(activeEntry);
  } catch (error) {
    console.error(error);
    errorCard.hidden = false;
    trackingPanelBody.textContent = "";

    if (trackingProgressHeader) {
      trackingProgressHeader.textContent = "";
    }
  }
}

async function refreshActiveTrackingEntry() {
  if (isRefreshingActiveTrackingEntry) return;

  isRefreshingActiveTrackingEntry = true;

  try {
    const activeEntry = await refreshTrackingToken(token);

    saveTrackingLink(activeEntry);
    errorCard.hidden = true;

    renderOpenPedidosNavigation();
    renderTrackingWorkspace(activeEntry);
  } catch (error) {
    console.error(error);
    errorCard.hidden = false;
  } finally {
    isRefreshingActiveTrackingEntry = false;
  }
}

async function refreshSavedTrackingEntries() {
  if (isRefreshingSavedTrackingEntries) return;

  isRefreshingSavedTrackingEntries = true;

  try {
    await refreshVisibleTrackingEntries({
      includeActive: false
    });

    renderOpenPedidosNavigation();
  } catch (error) {
    console.error(error);
  } finally {
    isRefreshingSavedTrackingEntries = false;
  }
}

async function selectOffer(offerId, button) {
  const activeEntry = getActiveTrackingEntry();
  if (isSelectingOffer || !activeEntry) return;

  isSelectingOffer = true;
  button.disabled = true;
  button.textContent = messages.selectingOffer;

  try {
    const response = await fetch(`/api/v1/track/${encodeURIComponent(activeEntry.token)}/offers/${encodeURIComponent(offerId)}/select`, {
      method: "POST",
      headers: {"Accept": "application/json"}
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    await refreshActiveTrackingEntry();
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = messages.retryOffer;
  } finally {
    isSelectingOffer = false;
  }
}

async function sendAssignmentAction(action, button) {
  const activeEntry = getActiveTrackingEntry();
  if (isSendingAssignmentAction || !activeEntry) return;

  isSendingAssignmentAction = true;

  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = messages.sendingAction;

  try {
    const response = await fetch(`/api/v1/track/${encodeURIComponent(activeEntry.token)}/assignment/${encodeURIComponent(action)}`, {
      method: "POST",
      headers: {"Accept": "application/json"}
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    await refreshActiveTrackingEntry();
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

async function sendCompletionAction(action, button) {
  const activeEntry = getActiveTrackingEntry();
  if (isSendingCompletionAction || !activeEntry) return;

  isSendingCompletionAction = true;
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = messages.sendingAction;

  try {
    const response = await fetch(
      `/api/v1/track/${encodeURIComponent(activeEntry.token)}/completion/${encodeURIComponent(action)}`,
      {
        method: "POST",
        headers: {"Accept": "application/json"}
      }
    );

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await refreshActiveTrackingEntry();
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = messages.retryOffer;
    window.setTimeout(() => {
      if (!button.disabled) button.textContent = originalText;
    }, 2200);
  } finally {
    isSendingCompletionAction = false;
  }
}

void bootstrapTrackingPage();

window.setInterval(
  () => void refreshActiveTrackingEntry(),
  POLL_INTERVAL_MS
);

window.setInterval(
  () => void refreshSavedTrackingEntries(),
  SAVED_REQUESTS_POLL_INTERVAL_MS
);
