/*
 * WYW — complemento no navegador (SPEC.md M2).
 *
 * - Rajadas e potencial de tornado vêm do Open-Meteo, chamado daqui, do IP da pessoa
 *   (restrição C-1: o IP compartilhado do Render recebe 429). REQ-WEB-22, 42 e 44.
 * - O nível de risco é recalculado com static/risk.js e a faixa é redesenhada.
 * - Busca por endereço pelo Nominatim; sem resultado, cai na busca de cidades (REQ-WEB-11).
 *   Ao servidor vão só a coordenada arredondada e a cidade (C-2); o endereço fica aqui.
 * - Alerta de tornado dos próximos 7 dias (SPEC.md 4.4), com o mesmo classificador do risco.
 * - App instalável (PWA): service worker, aviso de sem conexão e cartão "Instale o app".
 */
(function () {
    'use strict';

    var OPEN_METEO = 'https://api.open-meteo.com/v1/forecast';
    var NOMINATIM = 'https://nominatim.openstreetmap.org/search';
    var MS_TO_KMH = 3.6;
    var TIMEOUT_MS = 8000;
    var ADDRESS_HINT = /^(rua|r\.|av\.?|avenida|travessa|tv\.?|alameda|al\.|estrada|rodovia|rod\.|praça|praca|largo|calle|street|st\.|road|rd\.)\s/i;

    function fetchJson(url) {
        var controller = window.AbortController ? new AbortController() : null;
        var timer = controller && setTimeout(function () { controller.abort(); }, TIMEOUT_MS);
        return fetch(url, controller ? { signal: controller.signal } : {})
            .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
            .finally(function () { if (timer) clearTimeout(timer); });
    }

    function round(x) { return Math.round(x); }

    /* ---------- Open-Meteo: rajadas e tornado ---------- */

    function openMeteoUrl(d) {
        var p = new URLSearchParams({
            latitude: d.lat, longitude: d.lon, timezone: d.timezone, timeformat: 'unixtime',
            forecast_days: 7, wind_speed_unit: 'ms',
            current: 'wind_gusts_10m',
            hourly: ['wind_gusts_10m', 'cape', 'lifted_index', 'wind_speed_10m', 'wind_direction_10m',
                     'wind_speed_850hPa', 'wind_direction_850hPa', 'wind_speed_500hPa', 'wind_direction_500hPa'].join(','),
            daily: 'wind_gusts_10m_max'
        });
        return OPEN_METEO + '?' + p.toString();
    }

    /* Completa os horários da janela com rajada e potencial de tornado */
    function completeHours(hours, om) {
        var R = window.WYWRisk, h = om.hourly || {}, index = {};
        (h.time || []).forEach(function (t, i) { index[t] = i; });
        return hours.map(function (hour) {
            var copy = Object.assign({}, hour);
            var i = index[Math.floor(Date.parse(hour.time_utc) / 1000)];
            if (i === undefined) return copy;
            var at = function (name) { var s = h[name]; return s ? s[i] : null; };
            var gust = at('wind_gusts_10m');
            copy.gust_kmh = gust === null || gust === undefined ? null : gust * MS_TO_KMH;
            var deep = R.bulkShear(at('wind_speed_10m'), at('wind_direction_10m'), at('wind_speed_500hPa'), at('wind_direction_500hPa'));
            var low = R.bulkShear(at('wind_speed_10m'), at('wind_direction_10m'), at('wind_speed_850hPa'), at('wind_direction_850hPa'));
            copy.tornado = R.tornadoPotential(at('cape'), at('lifted_index'), deep, low);
            return copy;
        });
    }

    function showGusts(scope, d, om, t) {
        var fill = function (template, value) { return template.replace('%(value)s', value); };
        var current = om.current && om.current.wind_gusts_10m;
        var el = scope.querySelector('.gust-current');
        if (el && current !== null && current !== undefined) {
            el.textContent = fill(t.gusts, round(current * MS_TO_KMH));
            el.hidden = false;
        }
        var daily = om.daily || {}, byDate = {};
        (daily.time || []).forEach(function (stamp, i) {
            // Com timeformat=unixtime, cada dia vem como a meia-noite local em segundos
            var local = new Date((stamp + (om.utc_offset_seconds || 0)) * 1000).toISOString().slice(0, 10);
            byDate[local] = (daily.wind_gusts_10m_max || [])[i];
        });
        scope.querySelectorAll('.gust-day').forEach(function (cell) {
            var value = byDate[cell.getAttribute('data-date')];
            if (value === null || value === undefined) return;
            cell.textContent = fill(t.gusts, round(value * MS_TO_KMH));
            cell.hidden = false;
        });
    }

    /* ---------- Faixa de risco (mesma marcação de partials/_risk.html) ---------- */

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = text;
        return node;
    }

    var SVG_NS = 'http://www.w3.org/2000/svg';
    var spriteUrl = null;

    /* Ícone Lucide do sprite (mesma marcação de icon() em app/__init__.py) */
    function icon(name, classes, label) {
        if (spriteUrl === null) {
            try { spriteUrl = JSON.parse(document.getElementById('wyw-icons').textContent).sprite; }
            catch (e) { spriteUrl = '/static/icons.svg'; }
        }
        var svg = document.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('class', 'icon' + (classes ? ' ' + classes : ''));
        svg.setAttribute('focusable', 'false');
        if (label) { svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', label); }
        else svg.setAttribute('aria-hidden', 'true');
        var use = document.createElementNS(SVG_NS, 'use');
        use.setAttribute('href', spriteUrl + '#' + name);
        svg.appendChild(use);
        return svg;
    }

    function renderBanner(result, hours, t) {
        var R = window.WYWRisk;
        var severe = result.level === 'life' || result.level === 'extreme';
        var banner = el('div', 'risk-banner risk-banner-' + result.level);
        banner.setAttribute('role', severe ? 'alert' : 'status');

        var head = el('div', 'risk-banner-head');
        if (severe) {
            head.appendChild(icon('triangle-alert', 'risk-banner-icon'));
            if (result.level === 'extreme') head.appendChild(icon('tornado', 'risk-tornado', t.tornado_icon));
            head.appendChild(el('strong', 'risk-banner-title', t.life));
        } else if (result.level === 'attention') {
            head.appendChild(icon('circle-alert', 'risk-banner-icon'));
            head.appendChild(el('strong', 'risk-banner-title', t.attention));
        } else {
            head.appendChild(icon('circle-check', 'risk-banner-icon'));
            head.appendChild(el('strong', 'risk-banner-title', t.none));
        }
        if (result.tornado_info === 'moderate') {
            var info = el('span', 'risk-info-tornado');
            info.appendChild(icon('tornado'));
            info.appendChild(document.createTextNode(' ' + t.moderate_tornado));
            head.appendChild(info);
        }
        banner.appendChild(head);

        var lines = R.describe(result, hours, t);
        if (lines.length) {
            var ul = el('ul', 'risk-banner-lines');
            lines.forEach(function (line) { ul.appendChild(el('li', null, line)); });
            banner.appendChild(ul);
        }
        var recommendation = R.heatRecommendation(result, t);
        if (recommendation) banner.appendChild(el('p', 'risk-banner-recommendation', recommendation));
        banner.appendChild(el('p', 'risk-banner-note', t.disclaimer));
        return banner;
    }

    /* ---------- Alerta de tornado dos próximos 7 dias ---------- */

    function hourLabel(h) { return (h < 10 ? '0' : '') + h + ':00'; }

    function whenText(day, t) {
        if (day.start === null) return '';
        return day.start === day.end ? fill(t.at, { hour: hourLabel(day.start) })
            : fill(t.between, { start: hourLabel(day.start), end: hourLabel(day.end) });
    }

    function dayName(date) {
        var lang = document.documentElement.lang || 'en';
        try {
            return new Intl.DateTimeFormat(lang, { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })
                .format(new Date(date + 'T12:00:00Z'));
        } catch (e) { return date; }
    }

    function fill(template, values) {
        return template.replace(/%\((\w+)\)s/g, function (_, k) { return values[k] === undefined ? '' : values[k]; });
    }

    function showTornado(scope, outlook, t) {
        var levelText = function (level) { return t['tornado_level_' + level] || level; };
        var warn = outlook.filter(function (d) { return d.level === 'high' || d.level === 'moderate'; });
        var high = warn.some(function (d) { return d.level === 'high'; });

        // Aviso no topo (seção 4.4 do design system: ícone !, motivo em negrito, texto em tinta)
        var slot = scope.querySelector('.tornado-alert');
        if (slot) {
            slot.textContent = '';
            if (warn.length) {
                // Moderado ou alto: aviso em vermelho, para destacar
                var box = el('div', 'notice notice-alert tornado-warn');
                box.setAttribute('role', high ? 'alert' : 'status');
                var icons = el('span', 'tornado-icons');
                icons.appendChild(icon('triangle-alert'));
                icons.appendChild(icon('tornado'));
                box.appendChild(icons);
                var body = el('div');
                var p = el('p');
                p.appendChild(el('strong', null, high ? t.tornado_alert : t.tornado_watch));
                var lines = warn.map(function (d) {
                    var tpl = d.level === 'high' ? t.tornado_day_high : t.tornado_day_moderate;
                    return fill(tpl, { day: dayName(d.date), when: whenText(d, t) }).replace(/\s+\./, '.');
                });
                if (lines.length === 1) {
                    p.appendChild(document.createTextNode(' ' + lines[0]));
                    body.appendChild(p);
                } else {
                    body.appendChild(p);
                    var ul = el('ul');
                    lines.forEach(function (line) { ul.appendChild(el('li', null, line)); });
                    body.appendChild(ul);
                }
                body.appendChild(el('p', 'tornado-method small', t.tornado_method));
                box.appendChild(body);
                slot.appendChild(box);
            } else {
                var quiet = el('p', 'tornado-quiet');
                quiet.appendChild(icon('tornado'));
                quiet.appendChild(document.createTextNode(t.tornado_none));
                slot.appendChild(quiet);
            }
            slot.hidden = false;
        }

        // Ícone na linha do dia e quadro "Potencial de tornado" no painel
        var byDate = {};
        outlook.forEach(function (d) { byDate[d.date] = d; });
        scope.querySelectorAll('.day-tornado').forEach(function (cell) {
            var d = byDate[cell.getAttribute('data-date')];
            cell.textContent = '';
            cell.hidden = !d || (d.level !== 'high' && d.level !== 'moderate');
            if (cell.hidden) return;
            cell.className = 'day-tornado tornado-' + d.level;
            cell.appendChild(icon('tornado', null, t.tornado_potential + ': ' + levelText(d.level)));
            cell.title = t.tornado_potential + ': ' + levelText(d.level);
        });
        scope.querySelectorAll('.tile-tornado').forEach(function (tile) {
            var d = byDate[tile.getAttribute('data-date')];
            if (!d) return;
            tile.className = 'tile tile-tornado tornado-' + d.level;
            var value = tile.querySelector('.tile-value'), sub = tile.querySelector('.tile-sub');
            value.textContent = '';
            if (d.level === 'high' || d.level === 'moderate') value.appendChild(icon('triangle-alert'));
            value.appendChild(document.createTextNode(levelText(d.level)));
            sub.textContent = whenText(d, t);
            tile.hidden = false;
        });
    }

    /* ---------- Entrada: completa uma página de resultados ---------- */

    function enhance(scope) {
        var dataEl = (scope || document).querySelector('script.wyw-data');
        if (!dataEl || !window.WYWRisk || !window.fetch) return;
        var d;
        try { d = JSON.parse(dataEl.textContent); } catch (e) { return; }
        if (!d.hours || !d.hours.length) return;

        fetchJson(openMeteoUrl(d)).then(function (om) {
            var hours = completeHours(d.hours, om);
            var result = window.WYWRisk.evaluate(hours, true);
            var old = scope.querySelector('.risk-banner');
            if (old) old.replaceWith(renderBanner(result, hours, d.strings));
            showGusts(scope, d, om, d.strings);
            showTornado(scope, window.WYWRisk.tornadoOutlook(om.hourly, om.utc_offset_seconds, Date.now() / 1000), d.strings);
        }).catch(function () {
            // Sem Open-Meteo vale a faixa do servidor, que já diz "tornado indisponível" (REQ-WEB-44)
        });
    }

    /* ---------- Busca: endereço (Nominatim) ou cidade ---------- */

    function looksLikeAddress(query) {
        return /\d/.test(query) || ADDRESS_HINT.test(query);
    }

    function cityOf(address) {
        return address.city || address.town || address.village || address.municipality || address.county || '';
    }

    /* Devolve {url, label}: label é o endereço para o título, que não vai ao servidor */
    function resolve(query, action) {
        var cityUrl = { url: action + '?' + new URLSearchParams({ city: query }), label: null };
        if (!looksLikeAddress(query)) return Promise.resolve(cityUrl);
        var params = new URLSearchParams({ q: query, format: 'jsonv2', addressdetails: 1, limit: 1,
                                           'accept-language': document.documentElement.lang || 'pt' });
        return fetchJson(NOMINATIM + '?' + params.toString()).then(function (found) {
            var hit = found && found[0];
            var a = hit && hit.address;
            if (!a || !(a.road || a.house_number || a.pedestrian)) return cityUrl;
            var street = [a.road || a.pedestrian, a.house_number].filter(Boolean).join(', ');
            var city = cityOf(a);
            var params2 = new URLSearchParams({
                lat: Number(hit.lat).toFixed(2), lon: Number(hit.lon).toFixed(2),    // C-2
                city: city, state: a.state || '', cc: a.country_code || ''
            });
            return { url: action + '?' + params2.toString(), label: [street, a.suburb, city].filter(Boolean).join(' · ') };
        }).catch(function () { return cityUrl; });
    }

    /* ---------- App instalável (PWA) ---------- */

    var DISMISS_KEY = 'wyw-install-dismissed';

    function store(key, value) {
        try { if (value === undefined) return localStorage.getItem(key); localStorage.setItem(key, value); }
        catch (e) { return null; }
    }

    function setupApp() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function () {
                navigator.serviceWorker.register('/sw.js').catch(function () { /* o site funciona sem ele */ });
            });
        }

        // Sem conexão: avisa que o que está na tela pode estar desatualizado
        var bar = document.getElementById('offline-bar');
        var sync = function () { if (bar) bar.hidden = navigator.onLine !== false; };
        window.addEventListener('online', sync);
        window.addEventListener('offline', sync);
        sync();

        // Cartão "Instale o app": Android e computador pelo pedido do navegador; iPhone com as instruções
        var card = document.getElementById('install-card');
        if (!card) return;
        var standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
        if (standalone || store(DISMISS_KEY)) return;
        var button = document.getElementById('install-btn');
        var deferred = null;

        window.addEventListener('beforeinstallprompt', function (event) {
            event.preventDefault();
            deferred = event;
            button.hidden = false;
            card.hidden = false;
        });
        button.addEventListener('click', function () {
            if (!deferred) return;
            deferred.prompt();
            deferred.userChoice.then(function () { deferred = null; card.hidden = true; });
        });
        window.addEventListener('appinstalled', function () { card.hidden = true; });
        document.getElementById('install-dismiss').addEventListener('click', function () {
            card.hidden = true;
            store(DISMISS_KEY, '1');
        });

        var ua = navigator.userAgent;
        var ios = /iPhone|iPad|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        if (ios) {
            card.querySelector('[data-platform="ios"]').hidden = false;
            card.hidden = false;
        }
    }

    window.WYW = { enhance: enhance, resolve: resolve, looksLikeAddress: looksLikeAddress, setupApp: setupApp };
})();
