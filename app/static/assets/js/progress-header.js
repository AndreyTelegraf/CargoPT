(function () {
  const DEFAULT_STEPS = Object.freeze([
    {id: "received", label: "Recebido"},
    {id: "searching", label: "À procura"},
    {id: "offers", label: "Propostas"},
    {id: "selection", label: "Escolha"},
    {id: "confirmed", label: "Confirmado"}
  ]);

  const CANCELLED_STAGE_INDEX = Object.freeze({
    draft: 0,
    ready_for_matching: 1,
    matching: 1,
    unmatched: 1,
    no_carriers_found: 1,
    offers_exhausted: 1,
    expired_without_response: 1,
    manual_review_required: 1,
    offered: 2,
    assigned_pending_confirmation: 3,
    assigned: 3,
    in_progress: 4,
    completed: 4
  });

  const CANCELLED_LABELS = Object.freeze({
    pt: "Cancelado",
    en: "Cancelled",
    ru: "Отменено"
  });

  function getLocale() {
    return (
      document.body?.dataset.locale
      || document.documentElement.lang
      || "pt"
    )
      .toLowerCase()
      .split("-")[0];
  }

  function getCancelledLabel() {
    return (
      CANCELLED_LABELS[getLocale()]
      || CANCELLED_LABELS.pt
    );
  }

  function getCancelledActiveIndex(snapshot) {
    const fromStatus = String(
      snapshot?.cancelled_from_status || ""
    );

    if (
      Object.prototype.hasOwnProperty.call(
        CANCELLED_STAGE_INDEX,
        fromStatus
      )
    ) {
      return CANCELLED_STAGE_INDEX[fromStatus];
    }

    return 0;
  }

  function getProgressState(entry) {
    const snapshot = entry?.tracking_snapshot || {};

    const acceptedOffers = Array.isArray(
      snapshot.accepted_offers
    )
      ? snapshot.accepted_offers
      : [];

    const status = String(snapshot.status || "");

    const bothConfirmed =
      snapshot.client_confirmation_status === "confirmed"
      && snapshot.carrier_confirmation_status
        === "confirmed";

    if (status === "cancelled") {
      return {
        activeIndex:
          getCancelledActiveIndex(snapshot),
        finalComplete: false,
        tone: "cancelled"
      };
    }

    if (
      status === "offers_exhausted"
      || status === "expired_without_response"
    ) {
      return {
        activeIndex: 1,
        finalComplete: false,
        tone: "error"
      };
    }

    if (
      bothConfirmed
      || status === "in_progress"
      || status === "completed"
    ) {
      return {
        activeIndex: 4,
        finalComplete: true,
        tone: "success"
      };
    }

    if (
      status === "assigned_pending_confirmation"
      || status === "assigned"
    ) {
      return {
        activeIndex: 3,
        finalComplete: false,
        tone: "default"
      };
    }

    if (acceptedOffers.length > 0) {
      return {
        activeIndex: 2,
        finalComplete: false,
        tone: "default"
      };
    }

    if (
      status === "ready_for_matching"
      || status === "matching"
      || status === "offered"
      || status === "manual_review_required"
    ) {
      return {
        activeIndex: 1,
        finalComplete: false,
        tone: "default"
      };
    }

    return {
      activeIndex: 0,
      finalComplete: false,
      tone: "default"
    };
  }

  function getStepState(index, progressState) {
    if (progressState.tone === "cancelled") {
      if (index < progressState.activeIndex) {
        return "cancelled-complete";
      }

      if (index === progressState.activeIndex) {
        return "cancelled";
      }

      return "future";
    }

    if (progressState.finalComplete) {
      return "complete";
    }

    if (index < progressState.activeIndex) {
      return "complete";
    }

    if (index === progressState.activeIndex) {
      if (progressState.tone === "error") {
        return "error";
      }

      return "current";
    }

    return "future";
  }

  function render(entry, options = {}) {
    const container = options.container;

    if (!container) {
      throw new Error(
        "progress header container is required"
      );
    }

    const steps =
      Array.isArray(options.steps)
      && options.steps.length
        ? options.steps
        : DEFAULT_STEPS;

    const snapshot =
      entry?.tracking_snapshot || {};

    const progressState = getProgressState(entry);

    const activeStep =
      steps[progressState.activeIndex]
      || steps[0];

    const cancelledLabel = getCancelledLabel();

    const activeLabel =
      progressState.tone === "cancelled"
        ? cancelledLabel
        : activeStep.label;

    container.textContent = "";
    container.dataset.tone = progressState.tone;

    if (progressState.tone === "cancelled") {
      container.dataset.cancelledFromStatus =
        String(
          snapshot.cancelled_from_status || ""
        );
    } else {
      delete container.dataset.cancelledFromStatus;
    }

    const inner = document.createElement("div");
    inner.className = "progress-header";

    const currentLabel =
      document.createElement("strong");

    currentLabel.className =
      "progress-header-current-label";

    currentLabel.textContent = activeLabel;
    currentLabel.setAttribute(
      "aria-live",
      "polite"
    );

    const list = document.createElement("ol");
    list.className = "progress-header-list";

    steps.forEach((stepDefinition, index) => {
      const state = getStepState(
        index,
        progressState
      );

      const step = document.createElement("li");

      step.className =
        `progress-header-step `
        + `progress-header-step-${state}`;

      step.dataset.step = stepDefinition.id;
      step.dataset.state = state;

      if (
        state === "current"
        || state === "cancelled"
      ) {
        step.setAttribute(
          "aria-current",
          "step"
        );
      }

      const marker =
        document.createElement("span");

      marker.className =
        "progress-header-marker";

      marker.setAttribute(
        "aria-hidden",
        "true"
      );

      if (state === "complete") {
        marker.textContent = "✓";
      }

      const label =
        document.createElement("span");

      label.className =
        "progress-header-label";

      label.textContent =
        state === "cancelled"
          ? cancelledLabel
          : stepDefinition.label;

      step.append(marker, label);
      list.appendChild(step);
    });

    inner.append(currentLabel, list);
    container.appendChild(inner);
  }

  window.CargoPTProgressHeader = {
    render,
    getProgressState,
    getCancelledActiveIndex,
    steps: DEFAULT_STEPS
  };
})();
