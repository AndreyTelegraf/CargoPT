(() => {
  "use strict";

  const META_PIXEL_ID = "2752503925200185";
  const CONSENT_STORAGE_KEY = "cargopt_meta_consent_v1";
  const LEAD_STORAGE_PREFIX = "cargopt_meta_lead_v1:";
  const VALID_CHOICES = new Set(["granted", "denied"]);
  const inMemoryLeadKeys = new Set();
  let pixelInitialized = false;
  let activeBanner = null;
  let sessionConsent = null;

  const pageLocale = document.body.dataset.locale
    || document.documentElement.lang
    || "pt";
  const localeKey = pageLocale === "pt-PT" ? "pt" : pageLocale.slice(0, 2);

  const COPY = {
    pt: {
      label: "Preferências de cookies",
      message: "Utilizamos cookies opcionais da Meta para avaliar a eficácia da publicidade. O site funciona da mesma forma independentemente da sua escolha.",
      reject: "Recusar",
      allow: "Permitir",
      details: "Mais informações",
      detailsHref: "/cookies/",
      settings: "Preferências de cookies"
    },
    en: {
      label: "Cookie preferences",
      message: "We use optional Meta cookies to measure advertising effectiveness. The site works the same regardless of your choice.",
      reject: "Reject",
      allow: "Allow",
      details: "More information",
      detailsHref: "/en/cookies/",
      settings: "Cookie preferences"
    },
    ru: {
      label: "Настройки cookies",
      message: "Используем необязательные cookies Meta для оценки эффективности рекламы. Сайт одинаково работает при любом выборе.",
      reject: "Отклонить",
      allow: "Разрешить",
      details: "Подробнее",
      detailsHref: "/ru/cookies/",
      settings: "Настройки cookies"
    }
  };

  const copy = COPY[localeKey] || COPY.pt;

  function sixMonthsFromNow() {
    const expiresAt = new Date();
    expiresAt.setMonth(expiresAt.getMonth() + 6);
    return expiresAt.getTime();
  }

  function readConsent() {
    try {
      const raw = window.localStorage.getItem(CONSENT_STORAGE_KEY);
      if (!raw) return null;

      const stored = JSON.parse(raw);
      if (
        !stored
        || !VALID_CHOICES.has(stored.choice)
        || !Number.isFinite(stored.expiresAt)
        || stored.expiresAt <= Date.now()
      ) {
        window.localStorage.removeItem(CONSENT_STORAGE_KEY);
        return null;
      }

      return stored.choice;
    } catch {
      return null;
    }
  }

  function writeConsent(choice) {
    try {
      window.localStorage.setItem(
        CONSENT_STORAGE_KEY,
        JSON.stringify({choice, expiresAt: sixMonthsFromNow()})
      );
    } catch {
      // A blocked storage API must not prevent the user from using the site.
    }
  }

  function consentChoice() {
    return sessionConsent || readConsent();
  }

  function ensureFbq() {
    if (typeof window.fbq === "function") return window.fbq;

    const fbq = function () {
      if (fbq.callMethod) {
        fbq.callMethod.apply(fbq, arguments);
      } else {
        fbq.queue.push(arguments);
      }
    };

    if (!window._fbq) window._fbq = fbq;
    fbq.push = fbq;
    fbq.loaded = true;
    fbq.version = "2.0";
    fbq.queue = [];
    window.fbq = fbq;
    return fbq;
  }

  function loadPixel(force = false) {
    if (!force && consentChoice() !== "granted") return;

    if (pixelInitialized) {
      window.fbq("consent", "grant");
      window.fbq("track", "PageView");
      return;
    }

    pixelInitialized = true;

    const fbq = ensureFbq();
    fbq("init", META_PIXEL_ID);
    fbq("track", "PageView");

    const script = document.createElement("script");
    script.async = true;
    script.src = "https://connect.facebook.net/en_US/fbevents.js";
    script.dataset.cargoptMetaPixel = "true";
    document.head.appendChild(script);
  }

  function revokePixelConsent() {
    if (typeof window.fbq === "function") {
      window.fbq("consent", "revoke");
    }

    ["_fbp", "_fbc"].forEach((name) => {
      document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax`;
      document.cookie = `${name}=; Max-Age=0; Path=/; Domain=.cargopt.pt; SameSite=Lax`;
    });
  }

  function removeBanner() {
    if (!activeBanner) return;
    activeBanner.remove();
    activeBanner = null;
  }

  function choose(choice) {
    const previousChoice = consentChoice();
    sessionConsent = choice;
    writeConsent(choice);
    removeBanner();

    if (choice === "granted" && previousChoice !== "granted") {
      loadPixel(true);
    } else if (choice === "denied" && previousChoice !== "denied") {
      revokePixelConsent();
    }
  }

  function makeButton(text, className, choice) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = text;
    button.addEventListener("click", () => choose(choice));
    return button;
  }

  function showBanner() {
    if (activeBanner) return;

    const banner = document.createElement("section");
    banner.className = "meta-consent-banner";
    banner.setAttribute("role", "region");
    banner.setAttribute("aria-label", copy.label);

    const inner = document.createElement("div");
    inner.className = "meta-consent-inner";

    const text = document.createElement("p");
    text.className = "meta-consent-message";
    text.append(document.createTextNode(`${copy.message} `));

    const details = document.createElement("a");
    details.href = copy.detailsHref;
    details.textContent = copy.details;
    text.appendChild(details);

    const actions = document.createElement("div");
    actions.className = "meta-consent-actions";
    actions.append(
      makeButton(copy.reject, "meta-consent-button meta-consent-reject", "denied"),
      makeButton(copy.allow, "meta-consent-button meta-consent-allow", "granted")
    );

    inner.append(text, actions);
    banner.appendChild(inner);

    const main = document.querySelector("main");
    if (main) {
      main.before(banner);
    } else {
      document.body.prepend(banner);
    }

    activeBanner = banner;
  }

  function openPreferences() {
    showBanner();
    activeBanner?.scrollIntoView({behavior: "smooth", block: "start"});
  }

  function trackLeadOnce(requestId) {
    if (consentChoice() !== "granted" || typeof window.fbq !== "function") {
      return false;
    }

    const leadKey = `${LEAD_STORAGE_PREFIX}${requestId || "current-submission"}`;
    if (inMemoryLeadKeys.has(leadKey)) return false;

    try {
      if (window.sessionStorage.getItem(leadKey)) return false;
      window.sessionStorage.setItem(leadKey, "1");
    } catch {
      // The in-memory guard still prevents duplicate events during this page view.
    }

    inMemoryLeadKeys.add(leadKey);
    window.fbq("track", "Lead");
    return true;
  }

  document.querySelectorAll("[data-meta-consent-settings]").forEach((button) => {
    button.textContent = copy.settings;
    button.addEventListener("click", openPreferences);
  });

  const storedChoice = consentChoice();
  const preferencesRequested = new URLSearchParams(window.location.search)
    .get("cookie-preferences") === "1";

  if (preferencesRequested) {
    showBanner();
    const cleanUrl = new URL(window.location.href);
    cleanUrl.searchParams.delete("cookie-preferences");
    window.history.replaceState({}, "", `${cleanUrl.pathname}${cleanUrl.search}${cleanUrl.hash}`);
  }

  if (storedChoice === "granted") {
    loadPixel();
  } else if (storedChoice === null && !preferencesRequested) {
    showBanner();
  }

  window.CargoPTMeta = Object.freeze({
    hasConsent: () => consentChoice() === "granted",
    openPreferences,
    trackLeadOnce
  });
})();
