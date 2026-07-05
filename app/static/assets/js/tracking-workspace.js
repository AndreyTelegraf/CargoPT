
(function () {
  const DEFAULT_MESSAGES = {
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
    failDeal: "Não chegámos a acordo",
    confirmationRecorded: "A sua confirmação foi registada. Aguardamos a confirmação do transportador.",
    offersAvailable: "{count} oferta(s) disponível(eis)",
    defaultRoute: "Pedido CargoPT",
    waitingOffers: "A aguardar ofertas",
    detailsTitle: "Detalhes do pedido",
    itemsLabel: "Itens",
    commentLabel: "Comentário"
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
    if (snapshot.status === "completed") return "completed";
    if (snapshot.status === "cancelled") return "cancelled";
    if (snapshot.client_confirmation_status === "confirmed" && snapshot.carrier_confirmation_status === "confirmed") return "success";
    if (snapshot.client_confirmation_status === "pending" || snapshot.carrier_confirmation_status === "pending" || snapshot.status === "assigned_pending_confirmation") return "pending";
    if ((entry.accepted_offers_count || 0) > 0) return "success";
    return "pending";
  }

  function renderOffer(offer, entry, options, messages) {
    const card = document.createElement("article");
    card.className = "tracking-offer-card";

    const top = document.createElement("div");
    top.className = "tracking-offer-top";

    const company = document.createElement("strong");
    company.textContent = offer.company_name || "Transportador";

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

    return card;
  }

  function renderAssignmentActions(entry, options, messages) {
    const snapshot = entry.tracking_snapshot || {};
    if (snapshot.status !== "assigned_pending_confirmation") return null;

    const actions = document.createElement("div");
    actions.className = "tracking-assignment-actions";

    if (snapshot.client_confirmation_status === "confirmed") {
      const note = document.createElement("p");
      note.className = "tracking-assignment-note";
      note.textContent = messages.confirmationRecorded;
      actions.appendChild(note);
      return actions;
    }

    if (!options.onAssignmentAction) return null;

    const confirmButton = document.createElement("button");
    confirmButton.className = "button button-small tracking-assignment-confirm";
    confirmButton.type = "button";
    confirmButton.textContent = messages.confirmDeal;
    confirmButton.addEventListener("click", () => options.onAssignmentAction("confirm", confirmButton));

    const failButton = document.createElement("button");
    failButton.className = "button button-small button-secondary tracking-assignment-fail";
    failButton.type = "button";
    failButton.textContent = messages.failDeal;
    failButton.addEventListener("click", () => options.onAssignmentAction("fail", failButton));

    actions.append(confirmButton, failButton);
    return actions;
  }

  function render(entry, options = {}) {
    const container = options.container;
    if (!container) throw new Error("tracking workspace container is required");

    const messages = {...DEFAULT_MESSAGES, ...(options.messages || {})};
    container.textContent = "";

    const card = document.createElement("span");
    const visualState = entry.tracking_visual_state || getVisualState(entry);
    card.className = `tracking-success tracking-status-card tracking-status-${visualState}`;
    card.classList.toggle("has-offers", (entry.accepted_offers_count || 0) > 0);

    const eyebrow = document.createElement("span");
    eyebrow.className = "tracking-status-eyebrow";
    eyebrow.textContent = messages.trackingEyebrow;

    const title = document.createElement("strong");
    title.className = "tracking-status-title";
    title.textContent = messages.trackingTitle;

    const text = document.createElement("span");
    text.className = "tracking-status-text";
    text.textContent = messages.trackingText;

    const summary = document.createElement("span");
    summary.className = "tracking-status-summary";

    const route = document.createElement("strong");
    route.textContent = entry.route_summary || messages.defaultRoute;

    const status = document.createElement("span");
    status.className = "tracking-status-line";

    const statusDot = document.createElement("span");
    statusDot.className = `tracking-status-dot tracking-status-dot-${entry.status_dot_state || visualState || "searching"}`;
    statusDot.setAttribute("aria-hidden", "true");

    const statusLabel = document.createElement("span");
    statusLabel.textContent = entry.status_label || messages.waitingOffers;

    status.append(statusDot, statusLabel);

    summary.append(route, status);

    if ((entry.accepted_offers_count || 0) > 0) {
      const badge = document.createElement("span");
      badge.className = "tracking-status-badge";
      badge.textContent = messages.offersAvailable.replace("{count}", String(entry.accepted_offers_count));
      summary.appendChild(badge);
    }

    const details = document.createElement("span");
    details.className = "tracking-status-details";

    const detailsTitle = document.createElement("strong");
    detailsTitle.className = "tracking-status-details-title";
    detailsTitle.textContent = messages.detailsTitle;
    details.appendChild(detailsTitle);

    if (entry.item_summary) {
      const label = document.createElement("span");
      label.className = "tracking-status-detail-label";
      label.textContent = messages.itemsLabel;
      const value = document.createElement("span");
      value.className = "tracking-status-detail-text";
      value.textContent = entry.item_summary;
      details.append(label, value);
    }

    if (entry.comment_summary) {
      const label = document.createElement("span");
      label.className = "tracking-status-detail-label";
      label.textContent = messages.commentLabel;
      const value = document.createElement("span");
      value.className = "tracking-status-detail-text";
      value.textContent = entry.comment_summary;
      details.append(label, value);
    }

    const actions = document.createElement("span");
    actions.className = "tracking-success-actions";

    const statusButton = document.createElement("button");
    statusButton.className = entry.accepted_offers_count > 0 ? "button button-small tracking-status-primary-action" : "button button-small";
    statusButton.type = "button";
    statusButton.textContent = entry.accepted_offers_count > 0 ? messages.viewOffers : messages.viewStatus;
    statusButton.addEventListener("click", () => {
      const target = entry.accepted_offers_count > 0 ? container.querySelector(".tracking-offers") : container.querySelector(".tracking-status-summary");
      target?.scrollIntoView({behavior: "smooth", block: "nearest"});
    });

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

    if (!options.hideStatusAction) {
      actions.appendChild(statusButton);
    }

    if (!options.hideShareActions) {
      actions.append(copyButton, whatsappLink);

      const newRequest = document.createElement(options.newRequestHref ? "a" : "button");
      newRequest.className = "button button-small button-secondary";
      if (options.newRequestHref) {
        newRequest.href = options.newRequestHref;
      } else {
        newRequest.type = "button";
        newRequest.dataset.newRequest = "true";
      }
      newRequest.textContent = messages.newRequest;
      actions.appendChild(newRequest);
    }
    card.append(eyebrow, title, text, summary);

    if (entry.item_summary || entry.comment_summary) card.appendChild(details);

    const offers = entry.tracking_snapshot?.accepted_offers || [];
    if (offers.length && !options.hideOffers) {
      const wrap = document.createElement("section");
      wrap.className = "tracking-offers";

      const offersTitle = document.createElement("strong");
      offersTitle.className = "tracking-offers-title";
      offersTitle.textContent = messages.viewOffers;

      const offersList = document.createElement("div");
      offersList.className = "tracking-offers-list";

      offers.forEach((offer) => {
        offersList.appendChild(renderOffer(offer, entry, options, messages));
      });

      wrap.append(offersTitle, offersList);
      card.appendChild(wrap);
    }

    const assignmentActions = renderAssignmentActions(entry, options, messages);
    if (assignmentActions) card.appendChild(assignmentActions);

    card.appendChild(actions);
    container.appendChild(card);
  }

  window.CargoPTTrackingWorkspace = {render, getVisualState};
})();
