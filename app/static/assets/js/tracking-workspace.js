
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
    confirmationCompleted: "A confirmação de ambas as partes foi registada. O transporte está confirmado.",
    completionPrompt: "O transporte foi concluído?",
    completionConfirm: "Transporte concluído",
    completionProblem: "Existe um problema",
    completionRecorded: "A sua resposta foi guardada. Aguardamos a confirmação do transportador.",
    completionProblemRecorded: "O problema foi registado. A CargoPT irá verificar a situação.",
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
    selectedOfferLabel: "Oferta selecionada",
    priceLabel: "Preço",
    vehicleDetailsLabel: "Veículo e capacidade",
    vehicleLabel: "Veículo",
    payloadLabel: "Carga",
    volumeLabel: "Volume",
    equipmentLabel: "Equipamento",
    carrierContactLabel: "Contacto do transportador",
    carrierNoteLabel: "Nota do transportador",
    shortLeadTimeWarning: "Faltam menos de três dias para o transporte. O tempo para encontrar um transportador pode não ser suficiente. Considere alterar a data do transporte ou esteja preparado para poucas respostas dos transportadores."
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

  function createOfferSection(className, title) {
    const section = document.createElement("section");
    section.className = `tracking-offer-section ${className}`;

    const heading = document.createElement("h4");
    heading.className = "tracking-offer-section-title";
    heading.textContent = title;

    section.appendChild(heading);
    return section;
  }

  function appendOfferDefinition(list, label, value) {
    if (
      value === null
      || value === undefined
      || value === ""
    ) return;

    const item = document.createElement("div");
    item.className = "tracking-offer-definition";

    const term = document.createElement("dt");
    term.textContent = label;

    const description = document.createElement("dd");
    description.textContent = String(value);

    item.append(term, description);
    list.appendChild(item);
  }

  function renderOffer(offer, entry, options, messages) {
    const card = document.createElement("article");
    card.className = "tracking-offer-card";

    const top = document.createElement("div");
    top.className = "tracking-offer-top";

    const identity = document.createElement("div");
    identity.className = "tracking-offer-identity";

    const companyName = offer.company_name || messages.defaultCarrier;

    const avatar = document.createElement("div");
    avatar.className = "tracking-offer-avatar";

    if (offer.logo_url) {
      const image = document.createElement("img");
      image.className = "tracking-offer-logo";
      image.src = offer.logo_url;
      image.alt = "";
      image.loading = "lazy";
      avatar.appendChild(image);
    } else {
      const initials = companyName
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part.charAt(0).toUpperCase())
        .join("") || "C";
      avatar.textContent = initials;
      avatar.setAttribute("aria-hidden", "true");
    }

    const identityText = document.createElement("div");
    identityText.className = "tracking-offer-identity-text";

    const company = document.createElement("strong");
    company.className = "tracking-offer-company";
    company.textContent = companyName;

    identityText.appendChild(company);

    const profileMeta = [];
    if (offer.operating_regions) {
      const regionText = offer.operating_regions === "all_portugal"
        ? messages.allPortugalLabel
        : offer.operating_regions.split(",").join(", ");
      profileMeta.push(regionText);
    }
    if (offer.experience_since_year) {
      profileMeta.push(
        messages.experienceSinceLabel.replace(
          "{year}",
          String(offer.experience_since_year)
        )
      );
    }

    if (profileMeta.length) {
      const meta = document.createElement("span");
      meta.className = "tracking-offer-profile-meta";
      meta.textContent = profileMeta.join(" · ");
      identityText.appendChild(meta);
    }

    identity.append(avatar, identityText);

    const priceBlock = document.createElement("div");
    priceBlock.className = "tracking-offer-price-block";

    const priceLabel = document.createElement("span");
    priceLabel.className = "tracking-offer-price-label";
    priceLabel.textContent = messages.priceLabel;

    const price = document.createElement("strong");
    price.className = "tracking-offer-price";
    price.textContent = formatPrice(
      offer.price_cents,
      options.locale
    );

    priceBlock.append(priceLabel, price);
    top.append(identity, priceBlock);
    card.appendChild(top);

    const vehicleSection = createOfferSection(
      "tracking-offer-vehicle-section",
      messages.vehicleDetailsLabel
    );

    if (offer.vehicle_type) {
      const vehicleType = document.createElement("strong");
      vehicleType.className = "tracking-offer-vehicle-type";
      vehicleType.textContent = offer.vehicle_type;
      vehicleSection.appendChild(vehicleType);
    }

    const specifications = document.createElement("dl");
    specifications.className = "tracking-offer-spec-list";

    appendOfferDefinition(
      specifications,
      messages.payloadLabel,
      offer.payload_kg ? `${offer.payload_kg} kg` : null
    );

    appendOfferDefinition(
      specifications,
      messages.volumeLabel,
      offer.volume_m3 ? `${offer.volume_m3} m³` : null
    );

    appendOfferDefinition(
      specifications,
      messages.loadersLabel,
      offer.max_loaders || null
    );

    if (specifications.children.length) {
      vehicleSection.appendChild(specifications);
    }

    const equipment = [
      offer.has_tail_lift ? messages.tailLiftLabel : null,
      offer.has_crane ? messages.craneLabel : null,
      offer.has_mobile_lift
        ? messages.mobileLiftLabel
        : null
    ].filter(Boolean);

    if (equipment.length) {
      const equipmentBlock = document.createElement("div");
      equipmentBlock.className =
        "tracking-offer-equipment";

      const equipmentLabel = document.createElement("span");
      equipmentLabel.className =
        "tracking-offer-equipment-label";
      equipmentLabel.textContent = messages.equipmentLabel;

      const equipmentList = document.createElement("div");
      equipmentList.className =
        "tracking-offer-equipment-list";

      equipment.forEach((label) => {
        const chip = document.createElement("span");
        chip.className = "tracking-offer-equipment-chip";
        chip.textContent = label;
        equipmentList.appendChild(chip);
      });

      equipmentBlock.append(
        equipmentLabel,
        equipmentList
      );
      vehicleSection.appendChild(equipmentBlock);
    }

    card.appendChild(vehicleSection);

    const shouldShowCarrierContacts =
      entry.tracking_snapshot?.status !== "offered";

    const hasCarrierContacts =
      shouldShowCarrierContacts
      && (
        offer.contact_name
        || offer.phone
        || offer.telegram_username
      );

    if (hasCarrierContacts) {
      const contactSection = createOfferSection(
        "tracking-offer-contact-section",
        messages.carrierContactLabel
      );

      const contactList = document.createElement("dl");
      contactList.className =
        "tracking-offer-contact-list";

      appendOfferDefinition(
        contactList,
        messages.contactLabel,
        offer.contact_name
      );

      appendOfferDefinition(
        contactList,
        messages.phoneLabel,
        offer.phone
      );

      appendOfferDefinition(
        contactList,
        messages.telegramLabel,
        offer.telegram_username
          ? `@${offer.telegram_username}`
          : null
      );

      contactSection.appendChild(contactList);
      card.appendChild(contactSection);
    }

    if (offer.carrier_note) {
      const noteSection = createOfferSection(
        "tracking-offer-note-section",
        messages.carrierNoteLabel
      );

      const note = document.createElement("p");
      note.className = "tracking-offer-note";
      note.textContent = offer.carrier_note;

      noteSection.appendChild(note);
      card.appendChild(noteSection);
    }

    if (
      entry.tracking_snapshot?.status === "offered"
      && options.onSelectOffer
    ) {
      const button = document.createElement("button");
      button.className =
        "button button-small tracking-select-button";
      button.type = "button";
      button.textContent = messages.selectOffer;
      button.addEventListener(
        "click",
        () => options.onSelectOffer(
          offer.offer_id,
          button
        )
      );
      card.appendChild(button);
    }

    if (
      ["assigned_pending_confirmation", "assigned"].includes(
        entry.tracking_snapshot?.status
      )
      && options.onAssignmentAction
    ) {
      const failButton = document.createElement("button");
      failButton.className =
        "button button-small button-secondary "
        + "tracking-select-button tracking-assignment-fail";
      failButton.type = "button";
      failButton.textContent = messages.failDealShort;
      failButton.addEventListener(
        "click",
        () => options.onAssignmentAction(
          "fail",
          failButton
        )
      );
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

    const bothConfirmed =
      snapshot.client_confirmation_status === "confirmed"
      && snapshot.carrier_confirmation_status === "confirmed";

    const actions = document.createElement("div");
    actions.className = "tracking-assignment-actions";

    const note = document.createElement("p");
    note.className = "tracking-assignment-note";
    note.textContent = bothConfirmed
      ? messages.confirmationCompleted
      : messages.confirmationRecorded;
    actions.appendChild(note);
    return actions;
  }

  function renderCompletionActions(entry, options, messages) {
    const snapshot = entry.tracking_snapshot || {};
    if (
      !["assigned", "in_progress"].includes(snapshot.status)
      || !snapshot.completion_prompted_at
    ) return null;

    const actions = document.createElement("div");
    actions.className = "tracking-assignment-actions";

    const note = document.createElement("p");
    note.className = "tracking-assignment-note";

    if (snapshot.client_completion_status === "problem") {
      note.textContent = messages.completionProblemRecorded;
      actions.appendChild(note);
      return actions;
    }
    if (snapshot.client_completion_status === "confirmed") {
      note.textContent = messages.completionRecorded;
      actions.appendChild(note);
      return actions;
    }
    if (!options.onCompletionAction) return null;

    note.textContent = messages.completionPrompt;
    actions.appendChild(note);

    const completionConfirmButton = document.createElement("button");
    completionConfirmButton.type = "button";
    completionConfirmButton.className = "button button-small tracking-select-button";
    completionConfirmButton.textContent = messages.completionConfirm;
    completionConfirmButton.addEventListener(
      "click",
      () => options.onCompletionAction("confirm", completionConfirmButton)
    );

    const problemButton = document.createElement("button");
    problemButton.type = "button";
    problemButton.className = "button button-small button-secondary tracking-select-button";
    problemButton.textContent = messages.completionProblem;
    problemButton.addEventListener(
      "click",
      () => options.onCompletionAction("problem", problemButton)
    );

    actions.append(completionConfirmButton, problemButton);
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

    if (entry.tracking_snapshot?.short_lead_time_warning) {
      const warning = document.createElement("aside");
      warning.className = "tracking-short-lead-warning";
      warning.setAttribute("role", "status");
      warning.textContent = messages.shortLeadTimeWarning;
      workspace.appendChild(warning);
    }

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

    const completionActions = renderCompletionActions(
      entry,
      options,
      messages
    );

    if (completionActions) {
      workspace.appendChild(completionActions);
    }

    container.appendChild(workspace);
  }

  window.CargoPTTrackingWorkspace = {render, getVisualState};
})();
