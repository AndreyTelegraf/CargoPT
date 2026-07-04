const stateCard = document.querySelector("#stateCard");
const stateIcon = document.querySelector("#stateIcon");
const stateEyebrow = document.querySelector("#stateEyebrow");
const statusTitle = document.querySelector("#statusTitle");
const statusText = document.querySelector("#statusText");
const lastUpdated = document.querySelector("#lastUpdated");
const offersSection = document.querySelector("#offersSection");
const offersList = document.querySelector("#offersList");
const errorCard = document.querySelector("#errorCard");
const timelineList = document.querySelector("#timelineList");
const assignmentActions = document.createElement("div");
assignmentActions.className = "assignment-actions";
lastUpdated.insertAdjacentElement("afterend", assignmentActions);

const newPedidoCta = document.createElement("div");
newPedidoCta.className = "new-pedido-cta";
newPedidoCta.innerHTML = `
  <p><strong>Precisa de outro transporte?</strong><br>Pode criar um novo pedido separado.</p>
  <a class="assignment-button assignment-button-secondary" href="/#request">+ Criar novo pedido</a>
`;
assignmentActions.insertAdjacentElement("afterend", newPedidoCta);

const newPedidoLink = newPedidoCta.querySelector("a");

newPedidoLink.addEventListener("click", (event) => {
  const confirmed = window.confirm(
    "Esta será um novo pedido separado.\n\nO pedido atual continuará ativo."
  );

  if (!confirmed) {
    event.preventDefault();
  }
});

const token = decodeURIComponent(window.location.pathname.split("/").filter(Boolean).slice(1).join("/"));
const POLL_INTERVAL_MS = 5000;
let currentJobStatus = null;
let isSelectingOffer = false;
let isSendingAssignmentAction = false;

const TIMELINE_STEPS = [
  {
    key: "received",
    label: "Pedido recebido",
    statuses: ["draft", "created", "ready_for_matching", "matching", "offered", "assigned_pending_confirmation", "assigned", "in_progress", "completed"]
  },
  {
    key: "searching",
    label: "À procura",
    statuses: ["ready_for_matching", "matching", "offered", "assigned_pending_confirmation", "assigned", "in_progress", "completed"]
  },
  {
    key: "offers",
    label: "Propostas",
    statuses: ["offered", "assigned_pending_confirmation", "assigned", "in_progress", "completed"]
  },
  {
    key: "chosen",
    label: "Escolhido",
    statuses: ["assigned_pending_confirmation", "assigned", "in_progress", "completed"]
  },
  {
    key: "confirmed",
    label: "Confirmado",
    statuses: ["assigned", "in_progress", "completed"]
  },
  {
    key: "done",
    label: "Concluído",
    statuses: ["completed"]
  }
];

const ACTIVE_STEP_BY_STATUS = {
  draft: "received",
  created: "received",
  ready_for_matching: "searching",
  matching: "searching",
  offered: "offers",
  assigned_pending_confirmation: "chosen",
  assigned: "confirmed",
  in_progress: "confirmed",
  completed: "done",
  cancelled: "received",
  offers_exhausted: "searching",
  expired_without_response: "searching",
  manual_review_required: "searching",
  no_carriers_found: "searching"
};

const STATUS_COPY = {
  draft: {
    eyebrow: "Pedido criado",
    icon: "•",
    tone: "waiting",
    title: "Pedido em preparação.",
    text: "O pedido ainda não foi enviado para procura de transportadores."
  },
  created: {
    eyebrow: "Pedido recebido",
    icon: "✓",
    tone: "waiting",
    title: "Pedido recebido. Estamos a preparar a procura.",
    text: "O seu pedido foi criado e será enviado para transportadores disponíveis."
  },
  ready_for_matching: {
    eyebrow: "À procura",
    icon: "⌁",
    tone: "searching",
    title: "Pedido recebido. Estamos à procura de transportadores.",
    text: "O pedido está pronto para matching. Quando houver propostas, elas aparecerão aqui."
  },
  matching: {
    eyebrow: "Enviado aos transportadores",
    icon: "→",
    tone: "searching",
    title: "Pedido enviado a transportadores.",
    text: "Estamos a aguardar respostas dos transportadores disponíveis."
  },
  offered: {
    eyebrow: "Propostas recebidas",
    icon: "€",
    tone: "action",
    title: "Há propostas para o seu pedido.",
    text: "Veja abaixo as propostas recebidas e escolha o transportador."
  },
  assigned_pending_confirmation: {
    eyebrow: "Transportador escolhido",
    icon: "✓",
    tone: "action",
    title: "Transportador escolhido.",
    text: "Contacte o transportador e confirme se o negócio ficou fechado."
  },
  assigned: {
    eyebrow: "Negócio confirmado",
    icon: "✓",
    tone: "success",
    title: "Acordo confirmado.",
    text: "O pedido está atribuído a um transportador."
  },
  in_progress: {
    eyebrow: "Em curso",
    icon: "→",
    tone: "success",
    title: "Transporte em curso.",
    text: "O serviço está em andamento."
  },
  completed: {
    eyebrow: "Concluído",
    icon: "✓",
    tone: "success",
    title: "Transporte concluído.",
    text: "O pedido foi concluído."
  },
  cancelled: {
    eyebrow: "Cancelado",
    icon: "×",
    tone: "closed",
    title: "Pedido cancelado.",
    text: "Este pedido já não está ativo."
  },
  offers_exhausted: {
    eyebrow: "Sem propostas",
    icon: "!",
    tone: "warning",
    title: "Sem propostas disponíveis.",
    text: "As propostas disponíveis esgotaram ou expiraram."
  },
  expired_without_response: {
    eyebrow: "Sem resposta",
    icon: "!",
    tone: "warning",
    title: "Sem resposta a tempo.",
    text: "Não recebemos respostas suficientes dentro do prazo."
  },
  manual_review_required: {
    eyebrow: "Revisão manual",
    icon: "!",
    tone: "warning",
    title: "O pedido precisa de revisão.",
    text: "A equipa CargoPT terá de analisar este pedido manualmente."
  },
  no_carriers_found: {
    eyebrow: "Sem transportadores",
    icon: "!",
    tone: "warning",
    title: "Ainda não encontrámos transportadores.",
    text: "Não encontrámos transportadores adequados neste momento."
  }
};

function formatPrice(priceCents) {
  if (priceCents === null || priceCents === undefined) return null;
  return new Intl.NumberFormat("pt-PT", {
    style: "currency",
    currency: "EUR"
  }).format(priceCents / 100);
}

function formatBoolean(value) {
  return value ? "sim" : "não";
}

function renderTimeline(job) {
  const activeKey = ACTIVE_STEP_BY_STATUS[job.status] || "received";
  const activeIndex = TIMELINE_STEPS.findIndex((step) => step.key === activeKey);

  timelineList.textContent = "";

  TIMELINE_STEPS.forEach((step, index) => {
    const item = document.createElement("li");
    item.className = "timeline-item";

    if (index < activeIndex) {
      item.classList.add("is-complete");
    } else if (index === activeIndex) {
      item.classList.add("is-current");
    } else {
      item.classList.add("is-pending");
    }

    const marker = document.createElement("span");
    marker.className = "timeline-marker";
    marker.textContent = index < activeIndex ? "✓" : String(index + 1);

    const label = document.createElement("span");
    label.className = "timeline-label";
    label.textContent = step.label;

    item.appendChild(marker);
    item.appendChild(label);
    timelineList.appendChild(item);
  });
}

function setStatus(job) {
  const acceptedOffers = job.accepted_offers || [];
  let copy = STATUS_COPY[job.status] || {
    eyebrow: "Estado atualizado",
    icon: "•",
    tone: "waiting",
    title: "Estado do pedido atualizado.",
    text: `Estado técnico: ${job.status}.`
  };

  if (job.status === "offered" && acceptedOffers.length === 0) {
    copy = {
      eyebrow: "A aguardar propostas",
      icon: "→",
      tone: "searching",
      title: "Pedido enviado a transportadores.",
      text: "Estamos a aguardar propostas. Esta página atualiza automaticamente."
    };
  }

  if (job.status === "ready_for_matching" && acceptedOffers.length === 0) {
    copy = {
      eyebrow: "À procura",
      icon: "⌁",
      tone: "searching",
      title: "Pedido recebido. Estamos à procura de transportadores.",
      text: "Se uma combinação anterior falhou, o pedido voltou à procura."
    };
  }

  stateCard.className = `track-card state-card state-card-${copy.tone}`;
  stateIcon.textContent = copy.icon;
  stateEyebrow.textContent = copy.eyebrow;
  statusTitle.textContent = copy.title;
  statusText.textContent = copy.text;
  lastUpdated.textContent = `Atualizado às ${new Date().toLocaleTimeString("pt-PT", {hour: "2-digit", minute: "2-digit", second: "2-digit"})}`;
}

function renderAssignmentActions(job) {
  assignmentActions.textContent = "";

  if (job.status !== "assigned_pending_confirmation") {
    assignmentActions.hidden = true;
    return;
  }

  assignmentActions.hidden = false;

  if (job.client_confirmation_status === "confirmed") {
    const message = document.createElement("p");
    message.className = "assignment-note";
    message.textContent = "A sua confirmação foi registada. Aguardamos a confirmação do transportador.";
    assignmentActions.appendChild(message);
    return;
  }

  const confirmButton = document.createElement("button");
  confirmButton.className = "assignment-button";
  confirmButton.type = "button";
  confirmButton.textContent = "Negócio confirmado";
  confirmButton.addEventListener("click", () => sendAssignmentAction("confirm", confirmButton));

  const failButton = document.createElement("button");
  failButton.className = "assignment-button assignment-button-secondary";
  failButton.type = "button";
  failButton.textContent = "Não chegámos a acordo";
  failButton.addEventListener("click", () => sendAssignmentAction("fail", failButton));

  assignmentActions.appendChild(confirmButton);
  assignmentActions.appendChild(failButton);
}

function renderOffers(offers) {
  offersList.textContent = "";
  offersSection.hidden = offers.length === 0;

  for (const offer of offers) {
    const card = document.createElement("article");
    card.className = "offer-card";

    const title = document.createElement("h3");
    title.textContent = offer.company_name || "Transportador";

    const vehicle = document.createElement("p");
    vehicle.className = "offer-note";
    vehicle.textContent = `Viatura: ${offer.vehicle_type || "não especificada"}`;

    const meta = document.createElement("div");
    meta.className = "offer-meta";

    const rows = [
      ["Contacto", offer.contact_name || "não indicado"],
      ["Telefone", offer.phone || "não indicado"],
      ["Telegram", offer.telegram_username ? `@${offer.telegram_username.replace(/^@/, "")}` : "não indicado"],
      ["Carga", offer.payload_kg ? `${offer.payload_kg} kg` : "não indicada"],
      ["Volume", offer.volume_m3 ? `${offer.volume_m3} m³` : "não indicado"],
      ["Ajudantes", offer.max_loaders ?? "não indicado"],
      ["Plataforma elevatória", formatBoolean(offer.has_tail_lift)],
      ["Grua", formatBoolean(offer.has_crane)],
      ["Elevador exterior", formatBoolean(offer.has_mobile_lift)]
    ];

    for (const [label, value] of rows) {
      const item = document.createElement("div");
      item.textContent = `${label}: ${value}`;
      meta.appendChild(item);
    }

    card.appendChild(title);

    const price = formatPrice(offer.price_cents);
    if (price) {
      const priceBadge = document.createElement("div");
      priceBadge.className = "price";
      priceBadge.textContent = price;
      card.appendChild(priceBadge);
    }

    card.appendChild(vehicle);
    card.appendChild(meta);

    if (offer.carrier_note) {
      const note = document.createElement("p");
      note.className = "offer-note";
      note.textContent = offer.carrier_note;
      card.appendChild(note);
    }

    if (currentJobStatus === "offered") {
      const button = document.createElement("button");
      button.className = "select-button";
      button.type = "button";
      button.textContent = "Escolher";
      button.addEventListener("click", () => selectOffer(offer.offer_id, button));
      card.appendChild(button);
    }

    offersList.appendChild(card);
  }
}

async function selectOffer(offerId, button) {
  if (isSelectingOffer) return;
  isSelectingOffer = true;
  button.disabled = true;
  button.textContent = "A escolher...";

  try {
    const response = await fetch(`/api/v1/track/${encodeURIComponent(token)}/offers/${encodeURIComponent(offerId)}/select`, {
      method: "POST",
      headers: {"Accept": "application/json"}
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    await refresh();
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = "Tentar novamente";
  } finally {
    isSelectingOffer = false;
  }
}

async function sendAssignmentAction(action, button) {
  if (isSendingAssignmentAction) return;
  isSendingAssignmentAction = true;

  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "A enviar...";

  try {
    const response = await fetch(`/api/v1/track/${encodeURIComponent(token)}/assignment/${encodeURIComponent(action)}`, {
      method: "POST",
      headers: {"Accept": "application/json"}
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    await refresh();
  } catch (error) {
    console.error(error);
    button.disabled = false;
    button.textContent = "Tentar novamente";
    window.setTimeout(() => {
      if (!button.disabled) button.textContent = originalText;
    }, 2200);
  } finally {
    isSendingAssignmentAction = false;
  }
}

async function loadTrackingState() {
  if (!token) {
    throw new Error("missing tracking token");
  }

  const response = await fetch(`/api/v1/track/${encodeURIComponent(token)}`, {
    headers: {"Accept": "application/json"}
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

async function refresh() {
  try {
    const job = await loadTrackingState();
    currentJobStatus = job.status;
    errorCard.hidden = true;
    renderTimeline(job);
    setStatus(job);
    renderAssignmentActions(job);
    renderOffers(job.accepted_offers || []);
  } catch (error) {
    console.error(error);
    errorCard.hidden = false;
    stateCard.className = "track-card state-card state-card-warning";
    stateIcon.textContent = "!";
    stateEyebrow.textContent = "Erro";
    statusTitle.textContent = "Não foi possível carregar o estado.";
    statusText.textContent = "Verifique se abriu o link completo.";
    lastUpdated.textContent = "";
    offersSection.hidden = true;
    assignmentActions.hidden = true;
  }
}

refresh();
window.setInterval(refresh, POLL_INTERVAL_MS);
