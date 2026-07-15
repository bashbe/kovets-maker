const STORAGE_KEY = "kovets-maker-cover-v5";

const PDF_TEXT = Object.freeze({
  header: "ספרי׳ — אוצר החסידים — ליובאוויטש",
  publisherIntro: "יוצא לאור על ידי מערכת",
});

const DEFAULTS = Object.freeze({
  presetChoice: "hanochos",
  rebbeFormula: "full",
  title: "התוועדות",
  titleFont: "hitvaadut",
  eventDate: "ש״פ ואתחנן, חמשה עשר באב, ה׳תשל״ז",
  publication: "חלק א – יוצא לאור לש״פ דברים, ד׳ מנחם־אב, ה׳תשפ״ו",
  publisherName: "אוצר החסידים",
  publisherStreet: "770 איסטערן \uFB44א\u05B7רקוויי",
  publisherCity: "ברוקלין, נ.י.",
  publicationYear: "5786",
  commemoration: "שבעים ושש שנה לנשיאות כ״ק אדמו״ר זי״ע",
});

const COVER_PRESETS = Object.freeze({
  hanochos: {
    rebbeFormula: "full",
    title: "התוועדות",
    titleFont: "hitvaadut",
    eventDate: "ש״פ ואתחנן, חמשה עשר באב, ה׳תשל״ז",
    publication: "חלק א – יוצא לאור לש״פ דברים, ד׳ מנחם־אב, ה׳תשפ״ו",
    publicationYear: "5786",
    commemoration: "שבעים ושש שנה לנשיאות כ״ק אדמו״ר זי״ע",
  },
  "likkutei-vaad": {
    rebbeFormula: "shlita",
    title: "לקוטי שיחות",
    titleFont: "likkutei",
    eventDate: "פינחס",
    publication: "",
    publicationYear: "5754",
    commemoration: "",
  },
  "likkutei-kehot": {
    rebbeFormula: "full",
    title: "לקוטי שיחות",
    titleFont: "likkutei",
    eventDate: "בראשית (חלק ו – שיחה ב)",
    publication: "יוצא לאור למחזור הראשון מלימוד הלקוטי שיחות",
    publicationYear: "5786",
    commemoration: "",
  },
});

const PRESET_SUMMARIES = Object.freeze({
  hanochos: "Hanochos belahak : cadre et mise en page du התוועדות original.",
  "likkutei-vaad": "Likoutei Sichot - Vaad : style du PDF פינחס.",
  "likkutei-kehot": "Likoutei Sichot - Kehot : style du PDF Kehot fourni.",
});

const TEMPLATE_ASSETS = Object.freeze({
  hanochos: {
    png: "assets/cover-style-hanochos.png?v=20260715-1",
    pdf: "assets/cover-style-hanochos.pdf",
  },
  "likkutei-vaad": {
    png: "assets/cover-style-vaad.png?v=20260715-1",
    pdf: "assets/cover-style-vaad.pdf",
  },
  "likkutei-kehot": {
    png: "assets/cover-style-kehot.png?v=20260715-2",
    pdf: "assets/cover-style-kehot.pdf",
  },
});

const REBBE_FORMULA_ASSETS = Object.freeze({
  full: "assets/rebbe-formula-full.png?v=20260715-2",
  clean: "assets/rebbe-formula-clean.png?v=20260715-2",
  shlita: "assets/rebbe-formula-shlita.png?v=20260715-2",
});

// Maximum dimensions in PDF points, measured from the formula's source cover.
// A formula may shrink to fit another style, but it must never be enlarged
// beyond the size at which it appears in its original PDF.
const REBBE_FORMULA_SOURCE_SIZE = Object.freeze({
  full: Object.freeze([189.5, 88.75]),
  clean: Object.freeze([190, 82.5]),
  shlita: Object.freeze([233, 77]),
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

const STYLE_LAYOUTS = Object.freeze({
  hanochos: Object.freeze({
    title: { box: [90, 458, 252, 58], baseline: 477 },
    attribution: { box: [76, 357, 280, 104] },
    event: { box: [90, 289, 252, 28], baseline: 299 },
    publication: { box: [90, 262, 252, 23], baseline: 270 },
  }),
  "likkutei-vaad": Object.freeze({
    title: { box: [90, 458, 252, 58], baseline: 477 },
    attribution: { box: [72, 333, 288, 94] },
    event: { box: [90, 289, 252, 28], baseline: 299 },
    publication: { box: [90, 262, 252, 23], baseline: 270 },
  }),
  "likkutei-kehot": Object.freeze({
    title: { box: [70, 438, 292, 52], baseline: 456 },
    attribution: { box: [72, 305, 288, 94] },
    event: { box: [100, 266, 232, 28], baseline: 278 },
    publication: { box: [80, 229, 272, 35], baseline: 250 },
  }),
});

const COMMON_PDF_BLOCKS = Object.freeze([
  pdfBlock("publisher-name", "#publisher-text", 100, 111, 232, 18),
  pdfBlock("address", "#publisher-text", 65, 98, 302, 14),
  pdfBlock("publication-year", "#publication-year-text", 65, 82, 302, 18),
  pdfBlock("commemoration", "#chronology-text", 100, 69, 232, 16),
]);

function currentLayout() {
  return STYLE_LAYOUTS[state.presetChoice] || STYLE_LAYOUTS.hanochos;
}

function currentPdfBlocks() {
  const layout = currentLayout();
  return [
    pdfBlock("title", "#main-title", ...layout.title.box),
    pdfBlock("rebbe-formula", "#rebbe-formula-image", ...layout.attribution.box),
    pdfBlock("event-date", "#event-date-text", ...layout.event.box),
    pdfBlock("publication", "#publication-text", ...layout.publication.box),
    ...COMMON_PDF_BLOCKS,
  ];
}

const form = document.querySelector("#cover-form");
const cover = document.querySelector("#cover");
const overlayRoot = document.querySelector("#overlay-root");
const coverFrame = document.querySelector("#cover-frame");
const previewStage = document.querySelector("#preview-stage");
const saveStatus = document.querySelector("#save-status");
const toast = document.querySelector("#toast");
const zoomOutput = document.querySelector("#zoom-output");
const presetSummary = document.querySelector("#preset-summary");
const rebbeFormulaNote = document.querySelector("#rebbe-formula-note");
const presetGate = document.querySelector("#preset-gate");
const staticText = {
  publisherIntro: document.querySelector("#fixed-publisher-value"),
  publicationYearPreview: document.querySelector("#fixed-publication-year-preview"),
};

const elements = {
  templateImage: document.querySelector("#cover-template-image"),
  attributionImage: document.querySelector("#rebbe-formula-image"),
  titleMask: document.querySelector("#title-mask"),
  eventDateMask: document.querySelector("#event-date-mask"),
  publicationMask: document.querySelector("#publication-mask"),
  title: document.querySelector("#main-title"),
  eventDate: document.querySelector("#event-date-text"),
  publication: document.querySelector("#publication-text"),
  publisher: document.querySelector("#publisher-text"),
  publicationYear: document.querySelector("#publication-year-text"),
  chronology: document.querySelector("#chronology-text"),
};

let state = loadState();
let saveTimer;
let toastTimer;
let zoom = 0.72;
let zoomWasAdjusted = false;

function hebrewNumberWords(value) {
  const ones = ["", "אחת", "שתים", "שלש", "ארבע", "חמש", "שש", "שבע", "שמונה", "תשע"];
  const teens = {
    10: "עשר",
    11: "אחת עשרה",
    12: "שתים עשרה",
    13: "שלש עשרה",
    14: "ארבע עשרה",
    15: "חמש עשרה",
    16: "שש עשרה",
    17: "שבע עשרה",
    18: "שמונה עשרה",
    19: "תשע עשרה",
  };
  const tens = {
    20: "עשרים",
    30: "שלשים",
    40: "ארבעים",
    50: "חמשים",
    60: "ששים",
    70: "שבעים",
    80: "שמונים",
    90: "תשעים",
  };
  if (value < 10) return ones[value];
  if (value < 20) return teens[value];
  const tensValue = Math.floor(value / 10) * 10;
  const unit = value % 10;
  return unit ? `${tens[tensValue]} ו${ones[unit]}` : tens[tensValue];
}

function publicationYearWords(yearValue) {
  const year = Number(yearValue);
  if (!Number.isInteger(year) || year < 5000 || year >= 6000) return "";
  const remainder = year % 1000;
  const hundreds = Math.floor(remainder / 100);
  const finalValue = remainder % 100;
  const hundredWords = {
    0: "",
    1: "מאה",
    2: "מאתים",
    3: "שלש מאות",
    4: "ארבע מאות",
    5: "חמש מאות",
    6: "שש מאות",
    7: "שבע מאות",
    8: "שמונה מאות",
    9: "תשע מאות",
  };
  return `שנת חמשת אלפים ${[hundredWords[hundreds], hebrewNumberWords(finalValue)].filter(Boolean).join(" ")} לבריאה`;
}

function hebrewYearShort(yearValue) {
  const year = Number(yearValue);
  if (!Number.isInteger(year)) return "";
  let remainder = year % 1000;
  let letters = "";
  const values = [
    [400, "ת"],
    [300, "ש"],
    [200, "ר"],
    [100, "ק"],
    [90, "צ"],
    [80, "פ"],
    [70, "ע"],
    [60, "ס"],
    [50, "נ"],
    [40, "מ"],
    [30, "ל"],
    [20, "כ"],
  ];
  for (const [numericValue, letter] of values) {
    while (remainder >= numericValue) {
      letters += letter;
      remainder -= numericValue;
    }
  }
  if (remainder === 15) {
    letters += "טו";
    remainder = 0;
  } else if (remainder === 16) {
    letters += "טז";
    remainder = 0;
  }
  if (remainder >= 10) {
    letters += "י";
    remainder -= 10;
  }
  const units = ["", "א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט"];
  letters += units[remainder] || "";
  const punctuated =
    letters.length <= 1 ? `${letters}׳` : `${letters.slice(0, -1)}״${letters.slice(-1)}`;
  return `ה׳${punctuated}`;
}

function populatePublicationYears() {
  const select = form.elements.namedItem("publicationYear");
  select.replaceChildren();
  for (let year = 5700; year <= 5800; year += 1) {
    const option = document.createElement("option");
    option.value = String(year);
    option.textContent = `${hebrewYearShort(year)} · ${year}`;
    select.append(option);
  }
}

function enforceYearCompatibility(next, notify = false) {
  if (next.rebbeFormula === "shlita" && Number(next.publicationYear) > 5754) {
    if (notify) showToast("La formule שליט״א n’est pas disponible après 5754");
    return { ...next, rebbeFormula: "full" };
  }
  return next;
}

function loadState() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    const merged = stored ? { ...DEFAULTS, ...stored } : { ...DEFAULTS };
    if (!COVER_PRESETS[merged.presetChoice]) merged.presetChoice = "hanochos";
    if (!REBBE_FORMULA_ASSETS[merged.rebbeFormula]) merged.rebbeFormula = "full";
    return enforceYearCompatibility(merged);
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
  syncConditionalControls();
}

function populateStaticText() {
  staticText.publisherIntro.textContent = PDF_TEXT.publisherIntro;
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
  const baseline = (648 - currentLayout().publication.baseline) * PDF_TO_SVG;
  elements.publication.replaceChildren();
  lines.slice(0, 1).forEach((line, index) => {
    const match = line.match(/^(חלק\s+[אב])(\s+[–—-]\s+.+)$/u);
    const span = appendTspan(elements.publication, "", {
      y: baseline + index * 20,
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

function syncConditionalControls() {
  const shlitaOption = form.elements.namedItem("rebbeFormula").querySelector('option[value="shlita"]');
  const shlitaUnavailable = Number(state.publicationYear) > 5754;
  shlitaOption.disabled = shlitaUnavailable;
  rebbeFormulaNote.textContent = shlitaUnavailable
    ? "שליט״א est désactivé pour une année supérieure à 5754."
    : "Les trois formules sont disponibles pour cette année.";
  presetSummary.textContent = PRESET_SUMMARIES[state.presetChoice];
}

function setSvgBox(element, box) {
  const [x, y, width, height] = box;
  element.setAttribute("x", String(x * PDF_TO_SVG));
  element.setAttribute("y", String((648 - y - height) * PDF_TO_SVG));
  element.setAttribute("width", String(width * PDF_TO_SVG));
  element.setAttribute("height", String(height * PDF_TO_SVG));
}

function centeredFormulaBox(containerBox) {
  const [containerX, containerY, containerWidth, containerHeight] = containerBox;
  const [sourceWidth, sourceHeight] =
    REBBE_FORMULA_SOURCE_SIZE[state.rebbeFormula] || REBBE_FORMULA_SOURCE_SIZE.full;
  const scale = Math.min(1, containerWidth / sourceWidth, containerHeight / sourceHeight);
  const width = sourceWidth * scale;
  const height = sourceHeight * scale;
  return [
    containerX + (containerWidth - width) / 2,
    containerY + (containerHeight - height) / 2,
    width,
    height,
  ];
}

function configureLayout() {
  const layout = currentLayout();
  setSvgBox(elements.titleMask, layout.title.box);
  setSvgBox(elements.attributionImage, centeredFormulaBox(layout.attribution.box));
  elements.attributionImage.setAttribute("preserveAspectRatio", "xMidYMid meet");
  setSvgBox(elements.eventDateMask, layout.event.box);
  setSvgBox(elements.publicationMask, layout.publication.box);
  elements.title.setAttribute("y", String((648 - layout.title.baseline) * PDF_TO_SVG));
  elements.eventDate.setAttribute("y", String((648 - layout.event.baseline) * PDF_TO_SVG));
  elements.publication.setAttribute("y", String((648 - layout.publication.baseline) * PDF_TO_SVG));
}

function render() {
  const template = TEMPLATE_ASSETS[state.presetChoice] || TEMPLATE_ASSETS.hanochos;
  configureLayout();
  elements.templateImage.setAttribute("href", template.png);
  elements.attributionImage.setAttribute("href", REBBE_FORMULA_ASSETS[state.rebbeFormula]);
  const likkuteiTitle = state.titleFont === "likkutei";
  elements.title.classList.toggle("title-font-likkutei", likkuteiTitle);
  setSingleLine(elements.title, state.title, {
    size: likkuteiTitle ? 53 : 66.67,
    maxWidth: likkuteiTitle ? 420 : 330,
    weight: 700,
    preserveHeight: likkuteiTitle,
  });
  setSingleLine(elements.eventDate, state.eventDate, {
    size: 22.22,
    maxWidth: 293,
    weight: 700,
    preserveHeight: true,
  });
  setPublication(state.publication);
  setPublisher();
  setSingleLine(elements.publicationYear, publicationYearWords(state.publicationYear), {
    size: 14.5,
    maxWidth: 405,
    weight: 400,
    preserveHeight: true,
  });
  setSingleLine(elements.chronology, state.commemoration, { size: 15, maxWidth: 300, weight: 700 });
  staticText.publicationYearPreview.textContent = publicationYearWords(state.publicationYear);
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
      showToast("La sauvegarde locale a échoué");
    }
  }, 450);
}

function showToast(message) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.add("is-visible");
  toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 2800);
}

function applyPreset(presetKey) {
  const preset = COVER_PRESETS[presetKey];
  if (!preset) return;
  state = enforceYearCompatibility(
    {
      ...DEFAULTS,
      ...preset,
      presetChoice: presetKey,
    },
    true,
  );
  populateForm();
  render();
  queueSave();
  presetGate.hidden = true;
  showToast("Préréglage appliqué");
}

function handleFormInput(event) {
  if (event.target.type === "file") return;
  if (event.target.name === "presetChoice") {
    applyPreset(event.target.value);
    return;
  }
  const next = readForm();
  state = enforceYearCompatibility(
    next,
    event.target.name === "publicationYear" || event.target.name === "rebbeFormula",
  );
  if (state.rebbeFormula !== next.rebbeFormula) {
    form.elements.namedItem("rebbeFormula").value = state.rebbeFormula;
  }
  render();
  queueSave();
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
  const presetChoice = state.presetChoice;
  state = { ...DEFAULTS, ...COVER_PRESETS[presetChoice], presetChoice };
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
      ["PDF JNarkis Rebuilt", "assets/fonts/PDF-narkis-regular.ttf?v=20260714-7", 400, "truetype"],
      ["PDF JNarkis Rebuilt", "assets/fonts/PDF-narkis-bold.ttf?v=20260714-7", 700, "truetype"],
      ["PDF JNarkis Digits", "assets/fonts/PDF-narkis-digits.ttf?v=20260714-4", 400, "truetype"],
      ["PDF JDavid Rebuilt", "assets/fonts/PDF-david-regular.ttf?v=20260714-7", 400, "truetype"],
      ["PDF JDavid Rebuilt", "assets/fonts/PDF-david-bold.ttf?v=20260714-7", 700, "truetype"],
      ["PDF MHatzvi Rebuilt", "assets/fonts/PDF-hatzvi-bold.ttf?v=20260715-1", 700, "truetype"],
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
    .main-title.title-font-likkutei{font-family:'PDF MHatzvi Rebuilt','PDF JNarkis Rebuilt','Narkiss Yair Local','David Libre Local',serif;font-weight:700}
    .attribution-text{font-family:'PDF JNarkis Rebuilt','Narkiss Yair Local','David Libre Local',serif}
    .publication-text{font-family:'PDF JDavid Rebuilt','David Libre Local',serif;font-weight:400}
    .publication-lead{font-family:'PDF JDavid Rebuilt','David Libre Local',serif;font-weight:700}
    .address-line{font-family:'PDF JNarkis Rebuilt','Narkiss Yair Local','David Libre Local',serif;font-weight:400}
    .address-digits{font-family:'PDF JNarkis Digits',sans-serif;font-weight:400}
  `;
}

async function inlineSvgImages(element) {
  const images = element.matches?.("image")
    ? [element, ...element.querySelectorAll("image")]
    : [...element.querySelectorAll("image")];
  await Promise.all(
    images.map(async (imageElement) => {
      const href = imageElement.getAttribute("href");
      if (href && !href.startsWith("data:")) {
        imageElement.setAttribute("href", await assetDataUrl(href));
      }
    }),
  );
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
  sourceElement.removeAttribute("hidden");
  await inlineSvgImages(sourceElement);
  svg.append(style);
  svg.append(background);
  svg.append(sourceElement);

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

    const blocks = currentPdfBlocks();
    const templateAsset = (TEMPLATE_ASSETS[state.presetChoice] || TEMPLATE_ASSETS.hanochos).pdf;
    const [templateBytes, ...blockImages] = await Promise.all([
      assetBytes(templateAsset),
      ...blocks.map((block) => renderPdfBlockPngBytes(block)),
    ]);
    const pdfDocument = await window.PDFLib.PDFDocument.load(templateBytes);
    const page = pdfDocument.getPage(0);
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
document.querySelectorAll("[data-preset]").forEach((button) => {
  button.addEventListener("click", () => applyPreset(button.dataset.preset));
});
document.querySelector("#change-preset").addEventListener("click", () => {
  presetGate.hidden = false;
});
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

populatePublicationYears();
populateForm();
document.fonts.ready.then(() => {
  render();
  fitZoom();
});
render();
fitZoom();
