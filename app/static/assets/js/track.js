
const trackingPanelBody = document.querySelector("#trackingPanelBody");
const errorCard = document.querySelector("#errorCard");
const trackOffersList = document.querySelector("#trackOffersList");
const copyTrackingLink = document.querySelector("#copyTrackingLink");
const shareTrackingWhatsApp = document.querySelector("#shareTrackingWhatsApp");
const token = decodeURIComponent(window.location.pathname.split("/").filter(Boolean).slice(1).join("/"));

function absoluteTrackingUrl() {
  return new URL(`/track/${token}`, window.location.origin).toString();
}

if (shareTrackingWhatsApp) {
  shareTrackingWhatsApp.href = `https://wa.me/?text=${encodeURIComponent(absoluteTrackingUrl())}`;
}

if (copyTrackingLink) {
  copyTrackingLink.addEventListener("click", async () => {
    await navigator.clipboard.writeText(absoluteTrackingUrl());
    copyTrackingLink.textContent = "Link copiado";
  });
}

const POLL_INTERVAL_MS = 5000;
let activeTrackingEntry = null;
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
  if (priceCents == null) return "—";
  return new Intl.NumberFormat("pt-PT").format(priceCents / 100) + " €";
}

function renderOfferNavigation(entry) {
  if (!trackOffersList) return;

  const offers = entry.tracking_snapshot?.accepted_offers || [];
  trackOffersList.textContent = "";

  if (!offers.length) {
    const empty = document.createElement("p");
    empty.className = "track-offer-nav-empty";
    empty.textContent = "Ainda não há ofertas disponíveis.";
    trackOffersList.appendChild(empty);
    return;
  }

  offers.forEach((offer) => {
    const card = document.createElement("article");
    card.className = "track-offer-nav-card";

    const top = document.createElement("div");
    top.className = "track-offer-nav-top";

    const company = document.createElement("strong");
    company.textContent = offer.company_name || "Transportador";

    const price = document.createElement("span");
    price.textContent = formatSidebarPrice(offer.price_cents);

    top.append(company, price);

    const meta = document.createElement("div");
    meta.className = "track-offer-nav-meta";
    meta.textContent = [
      offer.vehicle_type,
      offer.payload_kg ? offer.payload_kg + " kg" : null,
      offer.volume_m3 ? offer.volume_m3 + " m³" : null
    ].filter(Boolean).join(" • ");

    card.append(top, meta);

    if (offer.carrier_note) {
      const note = document.createElement("p");
      note.className = "track-offer-nav-note";
      note.textContent = offer.carrier_note;
      card.appendChild(note);
    }

    if (entry.tracking_snapshot?.status === "offered") {
      const button = document.createElement("button");
      button.className = "button button-small track-offer-nav-select";
      button.type = "button";
      button.textContent = "Escolher esta oferta";
      button.addEventListener("click", () => selectOffer(offer.offer_id, button));
      card.appendChild(button);
    }

    trackOffersList.appendChild(card);
  });
}


function getTrackingStatusDotState(snapshot, acceptedOffers) {
  if (snapshot.status === "completed") return "completed";
  if (snapshot.status === "cancelled") return "cancelled";
  if (snapshot.client_confirmation_status === "pending" || snapshot.carrier_confirmation_status === "pending" || snapshot.status === "assigned_pending_confirmation") return "pending";
  if (acceptedOffers.length > 0) return "success";
  if (["ready_for_matching", "matching", "offered"].includes(snapshot.status)) return "searching";
  return "searching";
}

function formatTrackingStatus(snapshot) {
  const acceptedOffers = Array.isArray(snapshot.accepted_offers) ? snapshot.accepted_offers : [];

  if (snapshot.status === "completed") return messages.statusCompleted;
  if (snapshot.status === "cancelled") return messages.statusCancelled;

  if (snapshot.client_confirmation_status === "confirmed" && snapshot.carrier_confirmation_status === "confirmed") return messages.statusCarrierConfirmed;
  if (snapshot.client_confirmation_status === "pending" || snapshot.carrier_confirmation_status === "pending" || snapshot.status === "assigned_pending_confirmation") return messages.statusAwaitingConfirmation;
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

    renderOfferNavigation(activeTrackingEntry);

    window.CargoPTTrackingWorkspace.render(activeTrackingEntry, {
      container: trackingPanelBody,
      locale: "pt-PT",
      hideOffers: true,
      hideStatusAction: true,
      hideShareActions: true,
      onSelectOffer: selectOffer,
      onAssignmentAction: sendAssignmentAction
    });
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
