const STORAGE_KEY = "kovets-maker-cover-v4";

const PDF_TEXT = Object.freeze({
  header: "ספרי׳ — אוצר החסידים — ליובאוויטש",
  publisherIntro: "יוצא לאור על ידי מערכת",
  attribution: {
    "rebbe-full": [
      "כבוד קדושת",
      "אדמו״ר מנחם מענדל",
      "זצוקללה״ה נבג״מ זי״ע",
      "שניאורסאהן",
      "מליובאוויטש",
    ],
  },
  publicationYears: {
    5786: "שנת חמשת אלפים שבע מאות שמונים ושש לבריאה",
  },
});

const ATTRIBUTION_PRESETS = Object.freeze({
  "rebbe-full": PDF_TEXT.attribution["rebbe-full"].join("\n"),
});

const PUBLICATION_YEAR_PRESETS = Object.freeze(PDF_TEXT.publicationYears);

const DEFAULTS = Object.freeze({
  frame: "rebbe",
  showHeader: true,
  title: "התוועדות",
  attributionPreset: "rebbe-full",
  eventDate: "ש״פ ואתחנן, חמשה עשר באב, ה׳תשל״ז",
  publication: "חלק א – יוצא לאור לש״פ דברים, ד׳ מנחם־אב, ה׳תשפ״ו",
  publisherName: "אוצר החסידים",
  publisherStreet: "770 איסטערן \uFB44א\u05B7רקוויי",
  publisherCity: "ברוקלין, נ.י.",
  publicationYear: "5786",
  commemoration: "שבעים ושש שנה לנשיאות כ״ק אדמו״ר זי״ע",
  logoChoice: "kehot",
  customLogoData: "",
  customLogoName: "",
});

const PDF_TO_SVG = 600 / 432;

function pdfBlock(id, selector, x, y, width, height) {
  return Object.freeze({
    id,
    selector,
    pdf: { x, y, width, height },
    svg: {
      x: x * PDF_TO_SVG,
      y: (648 - y - height) * PDF_TO_SVG,
      width: width * PDF_TO_SVG,
      height: height * PDF_TO_SVG,
    },
  });
}

const PDF_BLOCKS = Object.freeze([
  pdfBlock("title", "#main-title", 90, 458, 252, 58),
  pdfBlock("event-date", "#event-date-text", 90, 289, 252, 28),
  pdfBlock("publication", "#publication-text", 90, 262, 252, 23),
  pdfBlock("publisher-name", "#publisher-text", 100, 111, 232, 18),
  pdfBlock("address", "#publisher-text", 65, 98, 302, 14),
  pdfBlock("commemoration", "#chronology-text", 100, 69, 232, 16),
]);

const PDF_LOGO_BLOCK = pdfBlock("custom-logo", "#custom-logo-preview", 186, 166, 61, 75);

const form = document.querySelector("#cover-form");
const cover = document.querySelector("#cover");
const overlayRoot = document.querySelector("#overlay-root");
const coverFrame = document.querySelector("#cover-frame");
const previewStage = document.querySelector("#preview-stage");
const saveStatus = document.querySelector("#save-status");
const toast = document.querySelector("#toast");
const zoomOutput = document.querySelector("#zoom-output");
const logoUpload = document.querySelector("#logo-upload");
const customLogoField = document.querySelector("#custom-logo-field");
const customLogoName = document.querySelector("#custom-logo-name");
const staticText = {
  header: document.querySelector("#fixed-header-value"),
  publisherIntro: document.querySelector("#fixed-publisher-value"),
  attributionPreview: document.querySelector("#fixed-attribution-preview"),
  attributionOption: document.querySelector("#attribution-rebbe-full-option"),
  publicationYearPreview: document.querySelector("#fixed-publication-year-preview"),
  publicationYearOption: document.querySelector("#publication-year-5786-option"),
};

const elements = {
  headerMask: document.querySelector("#header-mask-layer"),
  title: document.querySelector("#main-title"),
  eventDate: document.querySelector("#event-date-text"),
  publication: document.querySelector("#publication-text"),
  publisher: document.querySelector("#publisher-text"),
  chronology: document.querySelector("#chronology-text"),
  customLogoLayer: document.querySelector("#custom-logo-layer"),
  customLogo: document.querySelector("#custom-logo-preview"),
};

let state = loadState();
let saveTimer;
let toastTimer;
let zoom = 0.72;
let zoomWasAdjusted = false;

function loadState() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    return stored ? { ...DEFAULTS, ...stored } : { ...DEFAULTS };
  } catch {
    return { ...DEFAULTS };
  }
}

function populateForm() {
  populateStaticText();
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

function populateStaticText() {
  staticText.header.textContent = PDF_TEXT.header;
  staticText.publisherIntro.textContent = PDF_TEXT.publisherIntro;
  staticText.attributionPreview.textContent = ATTRIBUTION_PRESETS["rebbe-full"];
  staticText.attributionOption.textContent = ATTRIBUTION_PRESETS["rebbe-full"].replace(/\n/g, " · ");
  staticText.publicationYearPreview.textContent = PUBLICATION_YEAR_PRESETS[5786];
  staticText.publicationYearOption.textContent = `ה׳תשפ״ו · 5786 · ${PUBLICATION_YEAR_PRESETS[5786]}`;
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

function fitText(element, maxWidth, preferredSize, preserveHeight = false) {
  if (!maxWidth || !preferredSize || !element.textContent) return;
  element.removeAttribute("textLength");
  element.removeAttribute("lengthAdjust");
  element.style.fontSize = `${preferredSize}px`;
  const measured = element.getComputedTextLength();
  if (measured > maxWidth) {
    if (preserveHeight) {
      element.setAttribute("textLength", String(maxWidth));
      element.setAttribute("lengthAdjust", "spacingAndGlyphs");
    } else {
      const fitted = Math.max(10, preferredSize * (maxWidth / measured));
      element.style.fontSize = `${fitted.toFixed(2)}px`;
    }
  }
}

function setSingleLine(element, value, { size, maxWidth, weight, preserveHeight } = {}) {
  element.replaceChildren();
  element.textContent = String(value).trim();
  if (size) element.style.fontSize = `${size}px`;
  if (weight) element.style.fontWeight = String(weight);
  fitText(element, maxWidth, size, preserveHeight);
}

function appendTspan(parent, text, options) {
  const span = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
  span.textContent = text;
  span.setAttribute("x", String(options.x ?? 300));
  span.setAttribute("y", String(options.y));
  span.style.fontSize = `${options.size}px`;
  span.style.fontWeight = String(options.weight ?? 400);
  parent.append(span);
  fitText(span, options.maxWidth ?? 430, options.size, options.preserveHeight);
  return span;
}

function setPublication(value) {
  const lines = cleanLines(value);
  elements.publication.replaceChildren();
  lines.slice(0, 1).forEach((line, index) => {
    const match = line.match(/^(חלק\s+[אב])(\s+[–—-]\s+.+)$/u);
    const span = appendTspan(elements.publication, "", {
      y: 525 + index * 20,
      size: index === 0 ? 18.06 : 15,
      weight: 400,
      maxWidth: 303,
      preserveHeight: true,
    });
    if (match) {
      const lead = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
      lead.textContent = match[1];
      lead.classList.add("publication-lead");
      const remainder = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
      remainder.textContent = match[2];
      span.append(lead, remainder);
    } else {
      span.textContent = line;
    }
    fitText(span, 303, index === 0 ? 18.06 : 15, true);
  });
}

function setPublisher() {
  elements.publisher.replaceChildren();
  appendTspan(elements.publisher, `„${state.publisherName.trim()}״`, {
    y: 738,
    size: 18.06,
    weight: 700,
    maxWidth: 300,
  }).classList.add("publisher-name-line");
  const street = state.publisherStreet.trim();
  const streetLine = appendTspan(elements.publisher, "", {
    x: 445,
    y: 759,
    size: 14,
    maxWidth: 225,
  });
  streetLine.classList.add("address-line");
  const streetMatch = street.match(/^(770)(\s+)(.+)$/u);
  if (streetMatch) {
    const digits = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
    digits.textContent = streetMatch[1];
    digits.classList.add("address-digits");
    streetLine.append(digits, document.createTextNode(`${streetMatch[2]}${streetMatch[3]}`));
  } else {
    streetLine.textContent = street;
  }
  fitText(streetLine, 225, 14);
  appendTspan(elements.publisher, state.publisherCity.trim(), {
    x: 131,
    y: 759,
    size: 14,
    maxWidth: 190,
  }).classList.add("address-line");
}

function renderLogo() {
  const useCustom = state.logoChoice === "custom" && state.customLogoData;
  elements.customLogoLayer.hidden = !useCustom;
  if (useCustom) elements.customLogo.setAttribute("href", state.customLogoData);
}

function syncConditionalControls() {
  const customSelected = state.logoChoice === "custom";
  customLogoField.hidden = !customSelected;
  customLogoName.textContent = state.customLogoName
    ? `Logo chargé : ${state.customLogoName}`
    : "PNG, JPG, WebP ou SVG · 2 Mo maximum";
}

function render() {
  elements.headerMask.style.display = state.showHeader ? "none" : "";
  setSingleLine(elements.title, state.title, { size: 66.67, maxWidth: 330, weight: 700 });
  setSingleLine(elements.eventDate, state.eventDate, {
    size: 22.22,
    maxWidth: 293,
    weight: 700,
    preserveHeight: true,
  });
  setPublication(state.publication);
  setPublisher();
  setSingleLine(elements.chronology, state.commemoration, { size: 15, maxWidth: 300, weight: 700 });
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
  toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 2800);
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
  if (!response.ok) throw new Error(`Ressource inaccessible : ${url}`);
  return dataUrlFromBlob(await response.blob());
}

async function assetBytes(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Ressource inaccessible : ${url}`);
  return new Uint8Array(await response.arrayBuffer());
}

let embeddedFontCssPromise;
function embeddedFontCss() {
  if (!embeddedFontCssPromise) {
    const fonts = [
      ["PDF JNarkis Rebuilt", "assets/fonts/PDF-narkis-regular.ttf?v=20260714-5", 400, "truetype"],
      ["PDF JNarkis Rebuilt", "assets/fonts/PDF-narkis-bold.ttf?v=20260714-5", 700, "truetype"],
      ["PDF JNarkis Digits", "assets/fonts/PDF-narkis-digits.ttf?v=20260714-4", 400, "truetype"],
      ["PDF JDavid Rebuilt", "assets/fonts/PDF-david-regular.ttf?v=20260714-5", 400, "truetype"],
      ["PDF JDavid Rebuilt", "assets/fonts/PDF-david-bold.ttf?v=20260714-5", 700, "truetype"],
      ["Narkiss Yair Local", "assets/fonts/NarkissYair-Regular.woff2", 400, "woff2"],
      ["Narkiss Yair Local", "assets/fonts/NarkissYair-Bold.woff2", 700, "woff2"],
      ["David Libre Local", "assets/fonts/DavidLibre-Regular.ttf", 400, "truetype"],
      ["David Libre Local", "assets/fonts/DavidLibre-Bold.ttf", 700, "truetype"],
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

function exportFontStyles(fontCss) {
  return `${fontCss}
    text{direction:rtl;unicode-bidi:plaintext;text-anchor:middle;fill:#211f1d;font-family:'PDF JNarkis Rebuilt','Narkiss Yair Local','David Libre Local',serif}
    .main-title,.event-date-text,.publisher-name-line,.chronology-text{font-family:'PDF JNarkis Rebuilt','Narkiss Yair Local','David Libre Local',serif;font-weight:700}
    .publication-text{font-family:'PDF JDavid Rebuilt','David Libre Local',serif;font-weight:400}
    .publication-lead{font-family:'PDF JDavid Rebuilt','David Libre Local',serif;font-weight:700}
    .address-line{font-family:'PDF JNarkis Rebuilt','Narkiss Yair Local','David Libre Local',serif;font-weight:400}
    .address-digits{font-family:'PDF JNarkis Digits',sans-serif;font-weight:400}
  `;
}

async function renderPdfBlockPngBytes(block) {
  await document.fonts.ready;
  const fontCss = await embeddedFontCss();
  const { x, y, width, height } = block.svg;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  svg.setAttribute("viewBox", `${x} ${y} ${width} ${height}`);
  svg.setAttribute("width", String(Math.ceil(width * 3)));
  svg.setAttribute("height", String(Math.ceil(height * 3)));

  const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
  style.textContent = exportFontStyles(fontCss);
  const background = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  background.setAttribute("x", String(x));
  background.setAttribute("y", String(y));
  background.setAttribute("width", String(width));
  background.setAttribute("height", String(height));
  background.setAttribute("fill", "#fff");
  const sourceElement = document.querySelector(block.selector).cloneNode(true);
  svg.append(style, background, sourceElement);

  const markup = new XMLSerializer().serializeToString(svg);
  const source = URL.createObjectURL(new Blob([markup], { type: "image/svg+xml;charset=utf-8" }));
  try {
    const image = new Image();
    await new Promise((resolve, reject) => {
      image.onload = resolve;
      image.onerror = reject;
      image.src = source;
    });

    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(width * 3);
    canvas.height = Math.ceil(height * 3);
    const context = canvas.getContext("2d");
    context.fillStyle = "#fff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png", 1));
    if (!blob) throw new Error(`Le navigateur n’a pas produit le bloc ${block.id}.`);
    return new Uint8Array(await blob.arrayBuffer());
  } finally {
    URL.revokeObjectURL(source);
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

function safeFilename() {
  return "couverture-kovets";
}

function forcePdf14Header(pdfBytes) {
  const header = new TextEncoder().encode("%PDF-1.4");
  pdfBytes.set(header, 0);
  return pdfBytes;
}

async function exportPdf() {
  const button = document.querySelector("#export-pdf");
  const originalLabel = button.textContent;
  try {
    button.disabled = true;
    button.textContent = "Préparation…";
    showToast("Création du PDF à partir de la page originale…");
    if (!window.PDFLib) throw new Error("PDF-Lib n’est pas chargé.");

    const blocks = [...PDF_BLOCKS];
    if (state.logoChoice === "custom" && state.customLogoData) blocks.push(PDF_LOGO_BLOCK);
    const [templateBytes, ...blockImages] = await Promise.all([
      assetBytes("assets/cover-template.pdf"),
      ...blocks.map((block) => renderPdfBlockPngBytes(block)),
    ]);
    const pdfDocument = await window.PDFLib.PDFDocument.load(templateBytes);
    const page = pdfDocument.getPage(0);
    if (!state.showHeader) {
      page.drawRectangle({ x: 70, y: 552, width: 292, height: 23, color: window.PDFLib.rgb(1, 1, 1) });
    }
    for (const [index, block] of blocks.entries()) {
      const image = await pdfDocument.embedPng(blockImages[index]);
      page.drawImage(image, block.pdf);
    }
    const pdfBytes = forcePdf14Header(await pdfDocument.save({ useObjectStreams: false }));

    downloadBlob(new Blob([pdfBytes], { type: "application/pdf" }), `${safeFilename()}.pdf`);
    showToast("PDF créé avec le gabarit original");
  } catch (error) {
    console.error(error);
    showToast("L’export PDF a échoué");
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

form.addEventListener("input", handleFormInput);
form.addEventListener("change", handleFormInput);
logoUpload.addEventListener("change", handleLogoUpload);
document.querySelector("#reset-button").addEventListener("click", resetCover);
document.querySelector("#export-pdf").addEventListener("click", exportPdf);
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
document.fonts.ready.then(() => {
  render();
  fitZoom();
});
render();
fitZoom();
