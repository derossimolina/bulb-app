// Gera app/static/icons.svg (sprite com os ícones Lucide usados no site; design system, seção 2.6).
// Uso: node scripts/build_icons.js caminho/para/lucide.js > app/static/icons.svg
// (lucide.js: https://unpkg.com/lucide@0.460.0/dist/umd/lucide.js). Ao usar um ícone novo, inclua-o em ICONS.
const ICONS = ['sun', 'moon', 'cloud', 'cloud-sun', 'cloud-fog', 'cloud-drizzle', 'cloud-rain', 'cloud-rain-wind', 'cloud-sun-rain',
    'cloud-lightning', 'snowflake', 'thermometer', 'skull', 'leaf', 'droplet', 'wind', 'gauge', 'megaphone', 'chevron-down',
    'tornado', 'triangle-alert', 'circle-alert', 'circle-check', 'circle-x', 'info', 'plug', 'download', 'smartphone',
    'share', 'square-plus', 'wifi-off', 'x', 'github', 'linkedin'];
const lucide = require(process.argv[2]);
const names = ICONS;
const pascal = (n) => n.split('-').map((p) => p[0].toUpperCase() + p.slice(1)).join('');
const attrs = (o) => Object.entries(o).map(([k, v]) => `${k}="${v}"`).join(' ');
let out = '<svg xmlns="http://www.w3.org/2000/svg">\n<!-- Lucide 0.460.0 (ISC License, https://lucide.dev/license); gerado por scripts/build_icons.js -->\n';
for (const n of names) {
  const node = lucide.icons[pascal(n)];
  if (!node) throw new Error('missing ' + n);
  const children = (Array.isArray(node[2]) ? node[2] : node).map(([tag, a]) => `<${tag} ${attrs(a)}/>`).join('');
  out += `<symbol id="${n}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${children}</symbol>\n`;
}
process.stdout.write(out + '</svg>\n');
