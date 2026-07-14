(function () {
  const DEFAULT_STEPS = Object.freeze([
    {id: "received", label: "Recebido"},
    {id: "searching", label: "À procura"},
    {id: "offers", label: "Propostas"},
    {id: "selection", label: "Escolha"},
    {id: "confirmed", label: "Confirmado"}
  ]);

  function getProgressState(entry) {
    const snapshot = entry?.tracking_snapshot || {};
    const acceptedOffers = Array.isArray(snapshot.accepted_offers)
      ? snapshot.accepted_offers
      : [];

    const status = String(snapshot.status || "");
    const bothConfirmed =
      snapshot.client_confirmation_status === "confirmed"
      && snapshot.carrier_confirmation_status === "confirmed";

    if (status === "cancelled") {
      return {
        activeIndex: 0,
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
    if (progressState.finalComplete) return "complete";
    if (index < progressState.activeIndex) return "complete";

    if (index === progressState.activeIndex) {
      if (progressState.tone === "error") return "error";
      if (progressState.tone === "cancelled") return "cancelled";
      return "current";
    }

    return "future";
  }

  function render(entry, options = {}) {
    const container = options.container;

    if (!container) {
      throw new Error("progress header container is required");
    }

    const steps = Array.isArray(options.steps) && options.steps.length
      ? options.steps
      : DEFAULT_STEPS;

    const progressState = getProgressState(entry);
    const activeStep =
      steps[progressState.activeIndex]
      || steps[0];

    container.textContent = "";
    container.dataset.tone = progressState.tone;

    const inner = document.createElement("div");
    inner.className = "progress-header";

    const currentLabel = document.createElement("strong");
    currentLabel.className = "progress-header-current-label";
    currentLabel.textContent = activeStep.label;
    currentLabel.setAttribute("aria-live", "polite");

    const list = document.createElement("ol");
    list.className = "progress-header-list";

    steps.forEach((stepDefinition, index) => {
      const state = getStepState(index, progressState);

      const step = document.createElement("li");
      step.className =
        `progress-header-step progress-header-step-${state}`;
      step.dataset.step = stepDefinition.id;
      step.dataset.state = state;

      if (state === "current") {
        step.setAttribute("aria-current", "step");
      }

      const marker = document.createElement("span");
      marker.className = "progress-header-marker";
      marker.setAttribute("aria-hidden", "true");

      if (state === "complete") {
        marker.textContent = "✓";
      }

      const label = document.createElement("span");
      label.className = "progress-header-label";
      label.textContent = stepDefinition.label;

      step.append(marker, label);
      list.appendChild(step);
    });

    inner.append(currentLabel, list);
    container.appendChild(inner);
  }

  window.CargoPTProgressHeader = {
    render,
    getProgressState,
    steps: DEFAULT_STEPS
  };
})();

// CANCELLED_PROGRESS_LABEL_V2
(function () {
  const api = window.CargoPTProgressHeader;

  if (!api || typeof api.render !== "function") {
    throw new Error("CargoPTProgressHeader.render is unavailable");
  }

  const originalRender = api.render.bind(api);

  api.render = function (entry, options = {}) {
    const result = originalRender(entry, options);
    const status = String(entry?.tracking_snapshot?.status || "");

    if (status === "cancelled") {
      const label = options.container?.querySelector(
        ".progress-header-current-label"
      );

      if (label) label.textContent = "Cancelado";
    }

    return result;
  };
})();
