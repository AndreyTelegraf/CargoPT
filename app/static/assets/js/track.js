
const trackingPanelBody = document.querySelector("#trackingPanelBody");
const errorCard = document.querySelector("#errorCard");
const trackPedidosList = document.querySelector("#trackPedidosList");
const copyTrackingLink = document.querySelector("#copyTrackingLink");
const token = decodeURIComponent(window.location.pathname.split("/").filter(Boolean).slice(1).join("/"));

function absoluteTrackingUrl() {
  return new URL(`/track/${token}`, window.location.origin).toString();
}

if (copyTrackingLink) {
  copyTrackingLink.addEventListener("click", async () => {
    await navigator.clipboard.writeText(absoluteTrackingUrl());
    copyTrackingLink.textContent = "Track link copiado";
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

function renderOpenPedidosNavigation(activeEntry) {
  if (!trackPedidosList) return;

  const links = getTrackingLinks();
  trackPedidosList.textContent = "";

  if (!links.length) {
    const empty = document.createElement("p");
    empty.className = "track-offer-nav-empty";
    empty.textContent = "Ainda não há pedidos guardados neste dispositivo.";
    trackPedidosList.appendChild(empty);
    return;
  }

  links.slice(0, 5).forEach((entry) => {
    const isActive = entry.token === activeEntry.token;
    const card = document.createElement("article");
    card.className = "track-offer-nav-card";
    card.classList.toggle("is-chosen", isActive);
    card.tabIndex = 0;

    const top = document.createElement("div");
    top.className = "track-offer-nav-top";

    const route = document.createElement("strong");
    route.textContent = entry.route_summary || messages.defaultRoute;

    const status = document.createElement("span");
    status.className = "track-offer-nav-price";
    status.textContent = isActive ? "Atual" : "Abrir";

    top.append(route, status);

    const meta = document.createElement("div");
    meta.className = "track-offer-nav-meta";
    meta.textContent = entry.item_summary || entry.status_label || messages.waitingOffers;

    const line = document.createElement("div");
    line.className = "track-offer-nav-status";
    line.textContent = entry.status_label || messages.waitingOffers;

    card.append(top, meta, line);

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

const messages = {
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
  sendingAction: "A enviar..."
};

function formatSidebarPrice(priceCents) {
  if (priceCents == null) return "– €";
  return new Intl.NumberFormat("pt-PT").format(priceCents / 100) + " €";
}

function buildSidebarOfferSummary(offer, index) {
  if (!offer) return null;

  return {
    company_name: offer.company_name || `Transportador ${index + 1}`,
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
    locale: "pt-PT",
    hideOffers: true,
    hideStatusAction: true,
    hideShareActions: true,
    onSelectOffer: selectOffer,
    onAssignmentAction: sendAssignmentAction
  });
}

function getTrackingStatusDotState(snapshot, acceptedOffers) {
  if (snapshot.status === "completed") return "completed";
  if (snapshot.status === "cancelled") return "cancelled";
  if (snapshot.client_confirmation_status === "pending" || snapshot.carrier_confirmation_status === "pending") return "pending";
  if (acceptedOffers.length > 0) return "success";
  if (["ready_for_matching", "matching", "offered"].includes(snapshot.status)) return "searching";
  return "searching";
}

function formatTrackingStatus(snapshot) {
  const acceptedOffers = Array.isArray(snapshot.accepted_offers) ? snapshot.accepted_offers : [];

  if (snapshot.status === "completed") return messages.statusCompleted;
  if (snapshot.status === "cancelled") return messages.statusCancelled;

  if (snapshot.client_confirmation_status === "confirmed" && snapshot.carrier_confirmation_status === "confirmed") return messages.statusCarrierConfirmed;
  if (snapshot.client_confirmation_status === "pending" || snapshot.carrier_confirmation_status === "pending") return messages.statusAwaitingConfirmation;
  if (["assigned", "in_progress"].includes(snapshot.status)) return messages.statusAssigned;

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
    tracking_url: `/track/${snapshot.tracking_token || token}`,
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
