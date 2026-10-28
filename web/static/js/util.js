const R_ZEME_KM = 6371.0;

export function haversineKm(lat1, lon1, lat2, lon2) {
  const rad = Math.PI / 180;
  const a =
    Math.sin(((lat2 - lat1) * rad) / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(((lon2 - lon1) * rad) / 2) ** 2;
  return 2 * R_ZEME_KM * Math.asin(Math.sqrt(a));
}

const desatinne1 = new Intl.NumberFormat("sk-SK", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const desatinne2 = new Intl.NumberFormat("sk-SK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const cele = new Intl.NumberFormat("sk-SK");
const percento = new Intl.NumberFormat("sk-SK", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });

export function formatKm(km) {
  if (km === null || km === undefined) return "–";
  return km < 0.5 ? "< 0,5 km" : desatinne1.format(km) + " km";
}

export function formatNa10k(hodnota) {
  return desatinne2.format(hodnota);
}

export function formatCislo(hodnota) {
  return cele.format(hodnota);
}

export function formatPercento(podiel) {
  return percento.format(podiel);
}

export function formatDatum(iso) {
  const [rok, mesiac, den] = iso.split("-").map(Number);
  return `${den}. ${mesiac}. ${rok}`;
}

export function bezDiakritiky(text) {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[-–—]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function el(tag, moznosti, ...deti) {
  const uzol = document.createElement(tag);
  const m = moznosti || {};
  if (m.trieda) uzol.className = m.trieda;
  if (m.text !== undefined) uzol.textContent = m.text;
  if (m.atributy) {
    for (const [nazov, hodnota] of Object.entries(m.atributy)) uzol.setAttribute(nazov, hodnota);
  }
  for (const dieta of deti) {
    if (dieta) uzol.append(dieta);
  }
  return uzol;
}

const pamat = new Map();

export function nacitajJson(url) {
  if (!pamat.has(url)) {
    pamat.set(
      url,
      fetch(url).then((odpoved) => {
        if (!odpoved.ok) throw new Error(`${url}: HTTP ${odpoved.status}`);
        return odpoved.json();
      }),
    );
  }
  return pamat.get(url);
}
