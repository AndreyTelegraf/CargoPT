
const trackingPanelBody = document.querySelector("#trackingPanelBody");
const errorCard = document.querySelector("#errorCard");
const token = decodeURIComponent(window.location.pathname.split("/").filter(Boolean).slice(1).join("/"));

const POLL_INTERVAL_MS = 5000;
let activeTrackingEntry = null;
let isSelectingOffer = false;
let isSendingAssignmentAction = false;

const messages = {
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
  retryOffer: "Tentar novamente",
  selectingOffer: "A escolher...",
  sendingAction: "A enviar..."
};

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
    accepted_offers_count: acceptedOffers.length,
    route_summary: messages.defaultRoute,
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

    window.CargoPTTrackingWorkspace.render(activeTrackingEntry, {
      container: trackingPanelBody,
      locale: "pt-PT",
      newRequestHref: "/#request",
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
