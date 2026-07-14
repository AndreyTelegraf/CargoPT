
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
    failDeal: "Não chegámos a acordo com o transportador",
    confirmationRecorded: "A sua confirmação foi registada. Aguardamos a confirmação do transportador.",
    offersAvailable: "{count} oferta(s) disponível(eis)",
    defaultRoute: "Pedido CargoPT",
    waitingOffers: "A aguardar ofertas",
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

  function render(entry, options = {}) {
    const container = options.container;
    if (!container) throw new Error("tracking workspace container is required");

    const messages = {...DEFAULT_MESSAGES, ...(options.messages || {})};
    container.textContent = "";

    const card = document.createElement("section");
    const visualState = entry.tracking_visual_state || getVisualState(entry);
    card.className = "hero-workspace";
    card.dataset.state = visualState;
    card.classList.toggle("has-offers", (entry.accepted_offers_count || 0) > 0);

    const eyebrow = document.createElement("span");
    eyebrow.className = "tracking-status-eyebrow";
    eyebrow.textContent = messages.trackingEyebrow;

    const title = document.createElement("strong");
    title.className = "tracking-status-title";
    title.textContent = entry.status_title || messages.trackingTitle;

    const text = document.createElement("span");
    text.className = "tracking-status-text";
    text.textContent = entry.status_text || messages.trackingText;

    const summary = document.createElement("span");
    summary.className = "tracking-status-summary";

    const route = document.createElement("strong");
    const routeLabel = entry.route_summary || messages.defaultRoute;
    route.textContent = entry.job_id ? `#${entry.job_id} · ${routeLabel}` : routeLabel;

    const status = document.createElement("span");
    status.className = "tracking-status-line";

    const statusDot = document.createElement("span");
    statusDot.className = `tracking-status-dot tracking-status-dot-${entry.status_dot_state || visualState || "searching"}`;
    statusDot.setAttribute("aria-hidden", "true");

    const statusLabel = document.createElement("span");
    statusLabel.textContent = entry.status_label || messages.waitingOffers;

    status.append(statusDot, statusLabel);

    summary.append(route, status);

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

      clearTimeout(copyButton._copyResetTimer);
      copyButton._copyResetTimer = setTimeout(() => {
        if (copyButton.isConnected) {
          copyButton.textContent = messages.copyLink;
        }
      }, 3000);
    });

    const whatsappLink = document.createElement("a");
    whatsappLink.className = "button button-small button-secondary";
    whatsappLink.href = `https://wa.me/?text=${encodeURIComponent(absoluteUrl(entry.tracking_url))}`;
    whatsappLink.target = "_blank";
    whatsappLink.rel = "noopener noreferrer";
    whatsappLink.textContent = messages.shareWhatsApp;

    card.append(eyebrow, title, text, summary);

    if (entry.selected_offer_summary) {
      const selectedOffer = document.createElement("span");
      selectedOffer.className = "tracking-status-selected-offer";

      const selectedLabel = document.createElement("span");
      selectedLabel.className = "tracking-status-selected-label";
      selectedLabel.textContent = messages.selectedOfferLabel;

      const selectedCompany = document.createElement("strong");
      selectedCompany.textContent = entry.selected_offer_summary.company_name || messages.defaultCarrier;

      const selectedMeta = document.createElement("span");
      selectedMeta.textContent = [
        entry.selected_offer_summary.price_label,
        entry.selected_offer_summary.vehicle_label
      ].filter(Boolean).join(" · ");

      selectedOffer.append(selectedLabel, selectedCompany, selectedMeta);
      card.appendChild(selectedOffer);
    }

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
