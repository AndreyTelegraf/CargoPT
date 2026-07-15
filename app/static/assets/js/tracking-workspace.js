
(function () {
  const DEFAULT_MESSAGES = {
    trackingEyebrow: "Estado do pedido",
    trackingTitle: "Acompanhe o seu pedido",
    trackingText: "Quando houver propostas, poderá escolher o transportador nesta página, sem login e sem instalar nada.",
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
    confirmationRecorded: "A sua confirmação foi registada. Aguardamos a confirmação do transportador.",
    offersAvailable: "{count} oferta(s) disponível(eis)",
    defaultRoute: "Pedido CargoPT",
    waitingOffers: "A aguardar ofertas",
    statusCancelled: "Pedido cancelado",
    statusNoOffers: "Sem ofertas disponíveis",
    detailsTitle: "Detalhes do pedido",
    itemsLabel: "Itens",
    commentLabel: "Comentário",
    defaultCarrier: "Transportador",
    contactLabel: "Contacto",
    phoneLabel: "Telefone",
    telegramLabel: "Telegram",
    loadersLabel: "Ajudantes",
    tailLiftLabel: "Plataforma elevatória",
    craneLabel: "Grua",
    mobileLiftLabel: "Elevador exterior",
    failDealShort: "Não chegámos a acordo",
    selectedOfferLabel: "Oferta selecionada"
  };

  function absoluteUrl(path) {
    return new URL(path, window.location.origin).toString();
  }

  function formatPrice(priceCents, locale) {
    if (priceCents == null) return "—";
    return new Intl.NumberFormat(locale || "pt-PT").format(priceCents / 100) + " €";
  }

  function getVisualState(entry) {
    const snapshot = entry.tracking_snapshot || {};
    const acceptedOffers = Array.isArray(snapshot.accepted_offers) ? snapshot.accepted_offers : [];
    if (snapshot.status === "cancelled") return "cancelled";
    if (["offers_exhausted", "expired_without_response"].includes(snapshot.status)) return "cancelled";
    if (snapshot.status === "no_carriers_found") return "searching";
    if (snapshot.status === "completed") return "success";
    if (snapshot.client_confirmation_status === "confirmed" && snapshot.carrier_confirmation_status === "confirmed") return "success";
    if (snapshot.client_confirmation_status === "pending" || snapshot.carrier_confirmation_status === "pending") return "pending";
    if (["assigned_pending_confirmation", "assigned", "in_progress"].includes(snapshot.status)) return "pending";
    if (acceptedOffers.length > 0) return "success";
    if (["ready_for_matching", "matching", "offered"].includes(snapshot.status)) return "searching";
    return "completed";
  }

  function renderOffer(offer, entry, options, messages) {
    const card = document.createElement("article");
    card.className = "tracking-offer-card";

    const top = document.createElement("div");
    top.className = "tracking-offer-top";

    const company = document.createElement("strong");
    company.textContent = offer.company_name || messages.defaultCarrier;

    const price = document.createElement("strong");
    price.className = "tracking-offer-price";
    price.textContent = formatPrice(offer.price_cents, options.locale);

    top.append(company, price);

    const meta = document.createElement("div");
    meta.className = "tracking-offer-meta";
    meta.textContent = [
      offer.vehicle_type,
      offer.payload_kg ? offer.payload_kg + " kg" : null,
      offer.volume_m3 ? offer.volume_m3 + " m³" : null
    ].filter(Boolean).join(" • ");

    card.append(top, meta);

    const shouldShowCarrierContacts = entry.tracking_snapshot?.status !== "offered";
    const details = [
      shouldShowCarrierContacts && offer.contact_name ? `${messages.contactLabel}: ${offer.contact_name}` : null,
      shouldShowCarrierContacts && offer.phone ? `${messages.phoneLabel}: ${offer.phone}` : null,
      shouldShowCarrierContacts && offer.telegram_username ? `${messages.telegramLabel}: @${offer.telegram_username}` : null,
      offer.max_loaders ? `${messages.loadersLabel}: ${offer.max_loaders}` : null,
      offer.has_tail_lift ? messages.tailLiftLabel : null,
      offer.has_crane ? messages.craneLabel : null,
      offer.has_mobile_lift ? messages.mobileLiftLabel : null
    ].filter(Boolean);

    if (details.length) {
      const detailsNode = document.createElement("div");
      detailsNode.className = "tracking-offer-details";
      detailsNode.textContent = details.join(" • ");
      card.appendChild(detailsNode);
    }

    if (offer.carrier_note) {
      const note = document.createElement("div");
      note.className = "tracking-offer-note";
      note.textContent = offer.carrier_note;
      card.appendChild(note);
    }

    if (entry.tracking_snapshot?.status === "offered" && options.onSelectOffer) {
      const button = document.createElement("button");
      button.className = "button button-small tracking-select-button";
      button.type = "button";
      button.textContent = messages.selectOffer;
      button.addEventListener("click", () => options.onSelectOffer(offer.offer_id, button));
      card.appendChild(button);
    }

    if (
      ["assigned_pending_confirmation", "assigned"].includes(
        entry.tracking_snapshot?.status
      )
      && options.onAssignmentAction
    ) {
      const failButton = document.createElement("button");
      failButton.className = "button button-small button-secondary tracking-select-button tracking-assignment-fail";
      failButton.type = "button";
      failButton.textContent = messages.failDealShort;
      failButton.addEventListener("click", () => options.onAssignmentAction("fail", failButton));
      card.appendChild(failButton);
    }

    return card;
  }

  function renderAssignmentActions(entry, options, messages) {
    const snapshot = entry.tracking_snapshot || {};
    if (
      !["assigned_pending_confirmation", "assigned"].includes(snapshot.status)
    ) return null;
    if (snapshot.client_confirmation_status !== "confirmed") return null;

    const actions = document.createElement("div");
    actions.className = "tracking-assignment-actions";

    const note = document.createElement("p");
    note.className = "tracking-assignment-note";
    note.textContent = messages.confirmationRecorded;
    actions.appendChild(note);
    return actions;
  }

  function getEmptyStateCopy(entry, messages) {
    const status = String(
      entry.tracking_snapshot?.status || ""
    );

    if (status === "cancelled") {
      return {
        title: messages.statusCancelled,
        text: messages.closedRequestText,
        note: ""
      };
    }

    if (
      status === "no_carriers_found"
      || status === "offers_exhausted"
      || status === "expired_without_response"
    ) {
      return {
        title: messages.statusNoOffers,
        text: messages.noOffersText,
        note: ""
      };
    }

    return {
      title: messages.waitingTitle,
      text: messages.waitingText,
      note: messages.waitingNote
    };
  }

  function renderWaitingState(entry, messages) {
    const copy = getEmptyStateCopy(entry, messages);

    const waiting = document.createElement("section");
    waiting.className = "tracking-waiting-state";

    const title = document.createElement("strong");
    title.className = "tracking-waiting-title";
    title.textContent = copy.title;

    const text = document.createElement("span");
    text.className = "tracking-waiting-text";
    text.textContent = copy.text;

    waiting.append(title, text);

    if (copy.note) {
      const note = document.createElement("span");
      note.className = "tracking-waiting-note";
      note.textContent = copy.note;
      waiting.appendChild(note);
    }

    return waiting;
  }

  function renderOffers(entry, options, messages) {
    const offers = entry.tracking_snapshot?.accepted_offers || [];

    const wrap = document.createElement("section");
    wrap.className = "tracking-offers";

    const offersTitle = document.createElement("strong");
    offersTitle.className = "tracking-offers-title";
    offersTitle.textContent =
      messages.offersTitle || messages.viewOffers;

    const offersList = document.createElement("div");
    offersList.className = "tracking-offers-list";

    offers.forEach((offer) => {
      offersList.appendChild(
        renderOffer(offer, entry, options, messages)
      );
    });

    wrap.append(offersTitle, offersList);
    return wrap;
  }

  function render(entry, options = {}) {
    const container = options.container;

    if (!container) {
      throw new Error("tracking workspace container is required");
    }

    const messages = {
      ...DEFAULT_MESSAGES,
      ...(options.messages || {})
    };

    const offers =
      entry.tracking_snapshot?.accepted_offers || [];

    container.textContent = "";

    const workspace = document.createElement("div");
    workspace.className = "tracking-workspace-content";

    if (offers.length > 0 && !options.hideOffers) {
      workspace.appendChild(
        renderOffers(entry, options, messages)
      );
    } else {
      workspace.appendChild(
        renderWaitingState(entry, messages)
      );
    }

    const assignmentActions = renderAssignmentActions(
      entry,
      options,
      messages
    );

    if (assignmentActions) {
      workspace.appendChild(assignmentActions);
    }

    container.appendChild(workspace);
  }

  window.CargoPTTrackingWorkspace = {render, getVisualState};
})();
