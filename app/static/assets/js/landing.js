const STORAGE_KEY = "cargopt_landing_request_v2";
const pageLocale = document.body.dataset.locale || document.documentElement.lang || "ru";
const form = document.querySelector("#requestForm");
const steps = Array.from(document.querySelectorAll(".form-step"));
const stepLabel = document.querySelector("#stepLabel");
const progressFill = document.querySelector("#progressFill");
const formMessage = document.querySelector("#formMessage");
let currentStep = 1;

const MESSAGES = {
  pt: {
    required: "Preencha os campos obrigatórios deste passo.",
    contact: "Indique pelo menos um contacto: telefone, WhatsApp ou email.",
    submitting: "A enviar o pedido...",
    success: "Pedido enviado. Vamos encaminhá-lo para transportadores.",
    failure: "Não foi possível enviar o pedido. Verifique os campos ou tente mais tarde."
  },
  en: {
    required: "Fill in the required fields for this step.",
    contact: "Add at least one contact: phone, WhatsApp or email.",
    submitting: "Sending request...",
    success: "Request sent. We will forward it to carriers.",
    failure: "Could not send the request. Check the fields or try again later."
  },
  ru: {
    required: "Заполните обязательные поля этого шага.",
    contact: "Укажите хотя бы один контакт: телефон, WhatsApp или email.",
    submitting: "Отправляем заявку...",
    success: "Заявка отправлена. Мы передадим её перевозчикам.",
    failure: "Не удалось отправить заявку. Проверьте поля или попробуйте позже."
  }
};

const localeKey = pageLocale === "pt-PT" ? "pt" : pageLocale.slice(0, 2);
const messages = MESSAGES[localeKey] || MESSAGES.pt;

function setMessage(text, type) {
  formMessage.textContent = text || "";
  formMessage.classList.toggle("is-error", type === "error");
  formMessage.classList.toggle("is-success", type === "success");
}

function setStep(step) {
  currentStep = Math.min(Math.max(step, 1), steps.length);
  steps.forEach((item) => {
    item.classList.toggle("is-active", Number(item.dataset.step) === currentStep);
  });
  const template = form.dataset.stepTemplate || "Passo {current} de {total}";
  stepLabel.textContent = template
    .replace("{current}", currentStep)
    .replace("{total}", steps.length);
  progressFill.style.width = `${(currentStep / steps.length) * 100}%`;
  setMessage("", "");
}

function parseOptionalInt(value) {
  if (value === "") return null;
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseOptionalFloat(value) {
  if (value === "") return null;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseOptionalBool(value) {
  if (value === "") return null;
  return value === "true";
}

function getFormData() {
  return Object.fromEntries(new FormData(form).entries());
}

function saveDraft() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(getFormData()));
}

function restoreDraft() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;

  try {
    const data = JSON.parse(raw);
    Object.entries(data).forEach(([name, value]) => {
      const field = form.elements[name];
      if (field) field.value = value;
    });
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function validateStep(step) {
  const activeStep = steps[step - 1];
  const requiredFields = Array.from(activeStep.querySelectorAll("[required]"));
  for (const field of requiredFields) {
    if (!field.value.trim()) {
      field.focus();
      setMessage(messages.required, "error");
      return false;
    }
  }

  if (step === 2) {
    const data = getFormData();
    if (!data.client_phone.trim() && !data.client_whatsapp.trim() && !data.customer_email.trim()) {
      setMessage(messages.contact, "error");
      return false;
    }
  }

  return true;
}

function buildPayload() {
  const data = getFormData();
  const requestedDate = data.requested_date ? `${data.requested_date}T12:00:00+00:00` : null;

  return {
    source_locale: localeKey,
    customer_name: data.customer_name || null,
    customer_email: data.customer_email || null,
    preferred_contact: data.client_whatsapp ? "whatsapp" : data.client_phone ? "phone" : data.customer_email ? "email" : null,
    client_phone: data.client_phone || null,
    client_whatsapp: data.client_whatsapp || null,
    utm_source: new URLSearchParams(window.location.search).get("utm_source"),
    utm_campaign: new URLSearchParams(window.location.search).get("utm_campaign"),
    landing_version: "landing_static_v2",
    requested_date: requestedDate,
    addresses: [
      {
        kind: "pickup",
        raw_text: data.pickup,
        floor: parseOptionalInt(data.pickup_floor),
        has_elevator: parseOptionalBool(data.pickup_elevator)
      },
      {
        kind: "dropoff",
        raw_text: data.dropoff,
        floor: parseOptionalInt(data.dropoff_floor),
        has_elevator: parseOptionalBool(data.dropoff_elevator)
      }
    ],
    items: [
      {
        description: data.items,
        quantity: null
      }
    ],
    required_loaders: parseOptionalInt(data.required_loaders),
    estimated_volume_m3: parseOptionalFloat(data.estimated_volume_m3),
    comment: data.comment || null
  };
}

async function submitRequest() {
  if (!validateStep(2)) return;

  setMessage(messages.submitting, "");
  const submitButton = form.querySelector("button[type=\"submit\"]");
  submitButton.disabled = true;

  try {
    const response = await fetch("/api/v1/requests", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(buildPayload())
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }

    localStorage.removeItem(STORAGE_KEY);
    form.reset();
    setStep(1);
    setMessage(messages.success, "success");
  } catch (error) {
    setMessage(messages.failure, "error");
    console.error(error);
  } finally {
    submitButton.disabled = false;
  }
}

form.addEventListener("input", saveDraft);
form.addEventListener("change", saveDraft);

form.addEventListener("click", (event) => {
  const next = event.target.closest("[data-next]");
  const prev = event.target.closest("[data-prev]");

  if (next && validateStep(currentStep)) {
    saveDraft();
    setStep(currentStep + 1);
  }

  if (prev) {
    setStep(currentStep - 1);
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitRequest();
});

restoreDraft();
setStep(1);
