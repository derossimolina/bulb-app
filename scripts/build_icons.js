// Gera app/static/icons.svg: sprite com os ícones usados no site (design system, seção 2.6).
//   - Interface: Lucide 0.460.0 (ISC), em contorno, https://unpkg.com/lucide@0.460.0/dist/umd/lucide.js
//   - Marcas das redes sociais: Simple Icons 13.21.0 (CC0), preenchidos, com id "brand-<nome>",
//     de https://unpkg.com/simple-icons@13.21.0/icons/<nome>.svg (o Lucide não tem TikTok nem X)
// Uso: node scripts/build_icons.js caminho/para/lucide.js pasta/com/simple-icons > app/static/icons.svg
// Ao usar um ícone novo, inclua-o em ICONS ou em BRANDS.
const fs = require('fs');
const path = require('path');

const ICONS = ['sun', 'moon', 'cloud', 'cloud-sun', 'cloud-fog', 'cloud-drizzle', 'cloud-rain', 'cloud-rain-wind', 'cloud-sun-rain',
    'cloud-lightning', 'snowflake', 'thermometer', 'skull', 'leaf', 'droplet', 'wind', 'gauge', 'megaphone', 'chevron-down',
    'tornado', 'triangle-alert', 'circle-alert', 'circle-check', 'circle-x', 'info', 'plug', 'download', 'smartphone',
    'share', 'square-plus', 'wifi-off', 'x', 'globe', 'arrow-left'];
const BRANDS = ['instagram', 'youtube', 'tiktok', 'x', 'facebook', 'github', 'linkedin'];

const lucide = require(path.resolve(process.argv[2]));
const brandDir = process.argv[3];
const pascal = (n) => n.split('-').map((p) => p[0].toUpperCase() + p.slice(1)).join('');
const attrs = (o) => Object.entries(o).map(([k, v]) => `${k}="${v}"`).join(' ');

let out = '<svg xmlns="http://www.w3.org/2000/svg">\n'
    + '<!-- Lucide 0.460.0 (ISC, https://lucide.dev/license) e Simple Icons 13.21.0 (CC0, https://simpleicons.org);'
    + ' gerado por scripts/build_icons.js -->\n';
for (const n of ICONS) {
    const node = lucide.icons[pascal(n)];
    if (!node) throw new Error('Lucide sem o ícone ' + n);
    const children = node[2].map(([tag, a]) => `<${tag} ${attrs(a)}/>`).join('');
    out += `<symbol id="${n}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${children}</symbol>\n`;
}
for (const n of BRANDS) {
    const svg = fs.readFileSync(path.join(brandDir, n + '.svg'), 'utf8');
    const d = (svg.match(/<path d="([^"]+)"/) || [])[1];
    if (!d) throw new Error('Simple Icons sem o ícone ' + n);
    out += `<symbol id="brand-${n}" viewBox="0 0 24 24" fill="currentColor"><path d="${d}"/></symbol>\n`;
}
process.stdout.write(out + '</svg>\n');
