const STORAGE_KEY = "kovets-maker-cover-v2";

const FIXED_HEADER = "ספרי׳ — אוצר החסידים — ליובאוויטש";
const FIXED_PUBLISHER_LINE = "יוצא לאור על ידי מערכת";

const ATTRIBUTION_PRESETS = Object.freeze({
  "rebbe-full": [
    "כבוד קדושת",
    "אדמו״ר מנחם מענדל",
    "זצוקללה״ה נבג״מ זי״ע",
    "שניאורסאהן",
    "מליובאוויטש",
  ].join("\n"),
});

const PUBLICATION_YEAR_PRESETS = Object.freeze({
  5786: "שנת חמשת אלפים שבע מאות שמונים ושש לבריאה",
});

const DEFAULTS = Object.freeze({
  frame: "rebbe",
  showHeader: true,
  title: "התוועדות",
  attributionPreset: "rebbe-full",
  eventDate: "ש״פ ואתחנן, חמשה עשר באב, ה׳תשל״ז",
  publication: "חלק א — יוצא לאור לש״פ דברים, ד׳ מנחם־אב, ה׳תשפ״ו",
  publisherName: "אוצר החסידים",
  publisherStreet: "770 איסטערן פארקוויי",
  publisherCity: "ברוקלין, נ.י.",
  publicationYear: "5786",
  commemoration: "שבעים ושש שנה לנשיאות כ״ק אדמו״ר זי״ע",
  logoChoice: "kehot",
  customLogoData: "",
  customLogoName: "",
  paperColor: "#fffefb",
  inkColor: "#211f1d",
  fontStyle: "heritage",
});

const form = document.querySelector("#cover-form");
const cover = document.querySelector("#cover");
const paper = document.querySelector("#paper");
const coverFrame = document.querySelector("#cover-frame");
const previewStage = document.querySelector("#preview-stage");
const saveStatus = document.querySelector("#save-status");
const toast = document.querySelector("#toast");
const zoomOutput = document.querySelector("#zoom-output");
const logoUpload = document.querySelector("#logo-upload");
const customLogoField = document.querySelector("#custom-logo-field");
const customLogoName = document.querySelector("#custom-logo-name");

const elements = {
  headerLayer: document.querySelector("#header-layer"),
  header: document.querySelector("#header-text"),
  title: document.querySelector("#main-title"),
  attribution: document.querySelector("#attribution-text"),
  eventDate: document.querySelector("#event-date-text"),
  publication: document.querySelector("#publication-text"),
  publisher: document.querySelector("#publisher-text"),
  chronology: document.querySelector("#chronology-text"),
  logo: document.querySelector("#kehot-logo"),
  ornament: document.querySelector("#ornament"),
};

let state = loadState();
let saveTimer;
let toastTimer;
let zoom = 0.72;
let zoomWasAdjusted = false;
let ornamentReady;

function loadState() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    return stored ? { ...DEFAULTS, ...stored } : { ...DEFAULTS };
  } catch {
    return { ...DEFAULTS };
  }
}

function populateForm() {
  Object.entries(state).forEach(([key, value]) => {
    const field = form.elements.namedItem(key);
    if (!field || field.type === "file") return;
    if (field.type === "checkbox") {
      field.checked = Boolean(value);
    } else {
      field.value = value;
    }
  });
  logoUpload.value = "";
  syncConditionalControls();
}

function readForm() {
  const next = { ...state };
  Object.keys(DEFAULTS).forEach((key) => {
    const field = form.elements.namedItem(key);
    if (!field || field.type === "file") return;
    next[key] = field.type === "checkbox" ? field.checked : field.value;
  });
  return next;
}

function cleanLines(value) {
  return String(value)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function setSingleLine(element, value, { size, maxWidth, weight } = {}) {
  element.replaceChildren();
  element.textContent = value.trim();
  if (size) element.style.fontSize = `${size}px`;
  if (weight) element.style.fontWeight = weight;
  fitText(element, maxWidth, size);
}

function fitText(element, maxWidth, preferredSize) {
  if (!maxWidth || !preferredSize || !element.textContent) return;
  element.style.fontSize = `${preferredSize}px`;
  const measured = element.getComputedTextLength();
  if (measured > maxWidth) {
    const fitted = Math.max(10, preferredSize * (maxWidth / measured));
    element.style.fontSize = `${fitted.toFixed(2)}px`;
  }
}

function appendTspan(parent, text, options) {
  const span = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
  span.textContent = text;
  span.setAttribute("x", String(options.x ?? 300));
  span.setAttribute("y", String(options.y));
  span.style.fontSize = `${options.size}px`;
  span.style.fontWeight = String(options.weight ?? 400);
  if (options.anchor) span.setAttribute("text-anchor", options.anchor);
  parent.append(span);
  fitText(span, options.maxWidth ?? 430, options.size);
  return span;
}

function setAttribution(value) {
  const lines = cleanLines(value);
  const layout = [
    { y: 282, size: 16, weight: 700, maxWidth: 340 },
    { y: 316, size: 31, weight: 400, maxWidth: 430 },
    { y: 342, size: 15, weight: 700, maxWidth: 390 },
    { y: 369, size: 19, weight: 700, maxWidth: 350 },
    { y: 393, size: 17, weight: 400, maxWidth: 350 },
  ];
  elements.attribution.replaceChildren();
  lines.slice(0, 7).forEach((line, index) => {
    const fallback = { y: 282 + index * 25, size: 18, weight: 400, maxWidth: 430 };
    appendTspan(elements.attribution, line, layout[index] || fallback);
  });
}

function setPublication(value) {
  const lines = cleanLines(value);
  elements.publication.replaceChildren();
  lines.slice(0, 3).forEach((line, index) => {
    appendTspan(elements.publication, line, {
      y: 535 + index * 22,
      size: index === 0 ? 16 : 15,
      weight: index === 0 ? 400 : 700,
      maxWidth: 445,
    });
  });
}

function setPublisher(lines) {
  elements.publisher.replaceChildren();
  appendTspan(elements.publisher, lines[0], { y: 707, size: 16, maxWidth: 360 });
  appendTspan(elements.publisher, lines[1], { y: 731, size: 20, weight: 700, maxWidth: 360 });
  appendTspan(elements.publisher, lines[2], { x: 432, y: 755, size: 14, maxWidth: 235 });
  appendTspan(elements.publisher, lines[3], { x: 168, y: 755, size: 14, maxWidth: 200 });
}

function setChronology(lines) {
  elements.chronology.replaceChildren();
  lines.filter(Boolean).slice(0, 3).forEach((line, index, filtered) => {
    appendTspan(elements.chronology, line, {
      y: 780 + index * 20,
      size: index === filtered.length - 1 ? 16 : 14,
      weight: index === filtered.length - 1 ? 700 : 400,
      maxWidth: 450,
    });
  });
}

function renderLogo() {
  const useCustom = state.logoChoice === "custom" && state.customLogoData;
  elements.logo.setAttribute("href", useCustom ? state.customLogoData : "assets/kehot-logo.png");
}

function syncConditionalControls() {
  const customSelected = state.logoChoice === "custom";
  customLogoField.hidden = !customSelected;
  customLogoName.textContent = state.customLogoName
    ? `Logo chargé : ${state.customLogoName}`
    : "PNG, JPG, WebP ou SVG · 2 Mo maximum";
}

function render() {
  paper.setAttribute("fill", state.paperColor);
  cover.style.setProperty("--cover-ink", state.inkColor);
  cover.classList.remove("font-heritage", "font-david", "font-frank");
  cover.classList.add(`font-${state.fontStyle}`);

  elements.ornament.style.display = state.frame === "rebbe" ? "" : "none";
  elements.headerLayer.style.display = state.showHeader ? "" : "none";
  setSingleLine(elements.header, FIXED_HEADER, { size: 17, maxWidth: 390, weight: 700 });
  setSingleLine(elements.title, state.title, { size: 54, maxWidth: 420, weight: 700 });
  setAttribution(ATTRIBUTION_PRESETS[state.attributionPreset] || ATTRIBUTION_PRESETS["rebbe-full"]);
  setSingleLine(elements.eventDate, state.eventDate, { size: 20, maxWidth: 440, weight: 700 });
  setPublication(state.publication);
  setPublisher([
    FIXED_PUBLISHER_LINE,
    `״${state.publisherName.trim()}״`,
    state.publisherStreet.trim(),
    state.publisherCity.trim(),
  ]);
  setChronology([
    PUBLICATION_YEAR_PRESETS[state.publicationYear] || PUBLICATION_YEAR_PRESETS[5786],
    state.commemoration.trim(),
  ]);
  renderLogo();
  syncConditionalControls();

  document.querySelector("#cover-title").textContent = state.title || "Couverture personnalisée";
}

function queueSave() {
  saveStatus.textContent = "Modification…";
  saveStatus.classList.remove("is-saved");
  clearTimeout(saveTimer);
  saveTimer = window.setTimeout(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      saveStatus.textContent = "Enregistré";
      saveStatus.classList.add("is-saved");
    } catch {
      saveStatus.textContent = "Non enregistré";
      showToast("Le logo est trop volumineux pour la sauvegarde locale");
    }
  }, 450);
}

function showToast(message) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.add("is-visible");
  toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 2600);
}

function handleFormInput(event) {
  if (event.target.type === "file") return;
  state = readForm();
  render();
  queueSave();
}

function handleLogoUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    event.target.value = "";
    showToast("Choisis un fichier image");
    return;
  }
  if (file.size > 2 * 1024 * 1024) {
    event.target.value = "";
    showToast("Le logo doit peser moins de 2 Mo");
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    state = {
      ...readForm(),
      logoChoice: "custom",
      customLogoData: String(reader.result),
      customLogoName: file.name,
    };
    form.elements.namedItem("logoChoice").value = "custom";
    render();
    queueSave();
    showToast("Logo personnalisé chargé");
  };
  reader.onerror = () => showToast("Le logo n’a pas pu être lu");
  reader.readAsDataURL(file);
}

async function loadOrnament() {
  const response = await fetch("assets/ornament.svg");
  if (!response.ok) throw new Error("Impossible de charger l’ornement.");
  const markup = await response.text();
  const parsed = new DOMParser().parseFromString(markup, "image/svg+xml");
  [...parsed.documentElement.children].forEach((node) => {
    elements.ornament.append(document.importNode(node, true));
  });
}

function setZoom(next, userInitiated = true) {
  zoom = Math.min(1.08, Math.max(0.38, next));
  if (userInitiated) zoomWasAdjusted = true;
  coverFrame.style.width = `${Math.round(600 * zoom)}px`;
  zoomOutput.value = `${Math.round(zoom * 100)} %`;
}

function fitZoom() {
  if (zoomWasAdjusted) return;
  const widthScale = (previewStage.clientWidth - 48) / 600;
  const availableHeight = Math.max(560, window.innerHeight - 178);
  const heightScale = (availableHeight - 35) / 900;
  setZoom(Math.min(0.82, widthScale, heightScale), false);
}

function resetCover() {
  if (!window.confirm("Revenir au texte et aux réglages de la couverture d’origine ?")) return;
  state = { ...DEFAULTS };
  localStorage.removeItem(STORAGE_KEY);
  populateForm();
  render();
  queueSave();
  showToast("Couverture réinitialisée");
}

function dataUrlFromBlob(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function assetDataUrl(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Asset inaccessible: ${url}`);
  return dataUrlFromBlob(await response.blob());
}

let embeddedFontCssPromise;
function embeddedFontCss() {
  if (!embeddedFontCssPromise) {
    const fonts = [
      ["David Libre Local", "assets/fonts/DavidLibre-Regular.ttf", 400, "truetype"],
      ["David Libre Local", "assets/fonts/DavidLibre-Bold.ttf", 700, "truetype"],
      ["Frank Ruhl Local", "assets/fonts/FrankRuhlHofshi-Regular.otf", 400, "opentype"],
      ["Frank Ruhl Local", "assets/fonts/FrankRuhlHofshi-Bold.otf", 700, "opentype"],
    ];
    embeddedFontCssPromise = Promise.all(
      fonts.map(async ([family, url, weight, format]) => {
        const dataUrl = await assetDataUrl(url);
        return `@font-face{font-family:'${family}';src:url('${dataUrl}') format('${format}');font-weight:${weight};font-style:normal;}`;
      }),
    ).then((rules) => rules.join(""));
  }
  return embeddedFontCssPromise;
}

async function resolvedLogoDataUrl() {
  if (state.logoChoice === "custom" && state.customLogoData) return state.customLogoData;
  return assetDataUrl("assets/kehot-logo.png");
}

async function buildExportSvg() {
  await ornamentReady;
  await document.fonts.ready;
  const [fontCss, logoDataUrl] = await Promise.all([embeddedFontCss(), resolvedLogoDataUrl()]);

  const clone = cover.cloneNode(true);
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", "6in");
  clone.setAttribute("height", "9in");
  clone.style.setProperty("--cover-ink", state.inkColor);
  clone.querySelector("#kehot-logo").setAttribute("href", logoDataUrl);

  const exportStyles = document.createElementNS("http://www.w3.org/2000/svg", "style");
  exportStyles.textContent = `${fontCss}
    .cover-ink{fill:${state.inkColor};color:${state.inkColor}}
    .cover-ink-stroke{stroke:${state.inkColor}}
    text{direction:rtl;unicode-bidi:plaintext;font-family:'David Libre Local',serif}
    .font-frank text{font-family:'Frank Ruhl Local',serif}
    .header-text,.main-title{font-family:'Frank Ruhl Local','David Libre Local',serif}
  `;
  clone.insertBefore(exportStyles, clone.firstChild);
  return clone;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function safeFilename() {
  const fallback = "couverture-kovets";
  const title = state.title.trim();
  if (!title) return fallback;
  return `${fallback}-${title.replace(/[\\/:*?"<>|\s]+/g, "-").replace(/^-|-$/g, "")}`;
}

async function exportSvg() {
  try {
    showToast("Préparation du SVG…");
    const svg = await buildExportSvg();
    const markup = new XMLSerializer().serializeToString(svg);
    downloadBlob(new Blob([markup], { type: "image/svg+xml;charset=utf-8" }), `${safeFilename()}.svg`);
    showToast("SVG exporté");
  } catch (error) {
    console.error(error);
    showToast("L’export SVG a échoué");
  }
}

async function exportPng() {
  const button = document.querySelector("#export-png");
  const originalLabel = button.textContent;
  try {
    button.disabled = true;
    button.textContent = "Préparation…";
    const svg = await buildExportSvg();
    svg.setAttribute("width", "1800");
    svg.setAttribute("height", "2700");
    const markup = new XMLSerializer().serializeToString(svg);
    const source = URL.createObjectURL(new Blob([markup], { type: "image/svg+xml;charset=utf-8" }));
    const image = new Image();
    await new Promise((resolve, reject) => {
      image.onload = resolve;
      image.onerror = reject;
      image.src = source;
    });

    const canvas = document.createElement("canvas");
    canvas.width = 1800;
    canvas.height = 2700;
    const context = canvas.getContext("2d");
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    URL.revokeObjectURL(source);

    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png", 1));
    if (!blob) throw new Error("Le navigateur n’a pas produit le PNG.");
    downloadBlob(blob, `${safeFilename()}.png`);
    showToast("PNG 1800 × 2700 exporté");
  } catch (error) {
    console.error(error);
    showToast("L’export PNG a échoué");
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

form.addEventListener("input", handleFormInput);
form.addEventListener("change", handleFormInput);
logoUpload.addEventListener("change", handleLogoUpload);
document.querySelector("#reset-button").addEventListener("click", resetCover);
document.querySelector("#export-svg").addEventListener("click", exportSvg);
document.querySelector("#export-png").addEventListener("click", exportPng);
document.querySelector("#zoom-out").addEventListener("click", () => setZoom(zoom - 0.08));
document.querySelector("#zoom-in").addEventListener("click", () => setZoom(zoom + 0.08));
document.querySelector("#collapse-all").addEventListener("click", () => {
  const sections = [...form.querySelectorAll("details")];
  const shouldOpen = sections.every((section) => !section.open);
  sections.forEach((section) => {
    section.open = shouldOpen;
  });
  document.querySelector("#collapse-all").textContent = shouldOpen ? "−" : "+";
  document.querySelector("#collapse-all").setAttribute(
    "aria-label",
    shouldOpen ? "Replier les sections" : "Déplier les sections",
  );
});

window.addEventListener("resize", fitZoom);

populateForm();
ornamentReady = loadOrnament().catch((error) => {
  console.error(error);
  showToast("L’ornement n’a pas pu être chargé");
});

document.fonts.ready.then(() => {
  render();
  fitZoom();
});
render();
fitZoom();
