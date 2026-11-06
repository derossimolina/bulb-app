/*
 * WYW — modelo de risco à vida em JavaScript (SPEC.md seção 4).
 * Mesma lógica de app/meteo/risk.py; os dois motores passam em spec/risk-cases.json.
 * Funciona no navegador (window.WYWRisk) e no Node (module.exports), para os testes.
 */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.WYWRisk = factory();
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    var HEAT_SUN_C = 35, HEAT_SHADE_C = 38, SUN_MAX_CLOUD = 75, WET_BULB_C = 31, WIND_KMH = 60;
    var STRONG_ALERT = ['perigo', 'grande perigo'];
    var SEVERITY_RANK = { 'perigo potencial': 1, 'perigo': 2, 'grande perigo': 3 };
    var HEAT = 'IND-CALOR', WET_BULB = 'IND-TW', STORM = 'IND-TEMP', WIND = 'IND-VENTO', TORNADO = 'IND-TORNADO';
    var ORDER = [TORNADO, WET_BULB, HEAT, STORM, WIND];

    function present(v) { return v !== undefined && v !== null; }

    function normalize(text) {
        return String(text || '').normalize('NFKD').replace(/[̀-ͯ]/g, '')
            .replace(/'/g, '').replace(/-/g, ' ').toLowerCase().split(/\s+/).filter(Boolean).join(' ');
    }

    /* Bulbo úmido, fórmula de Stull (2011), como app/meteo/wetbulb.py */
    function wetBulb(temp, rh) {
        if (!present(temp) || !present(rh)) return null;
        rh = Math.min(Math.max(rh, 5), 99);
        var tw = temp * Math.atan(0.151977 * Math.sqrt(rh + 8.313659)) + Math.atan(temp + rh)
            - Math.atan(rh - 1.676331) + 0.00391838 * Math.pow(rh, 1.5) * Math.atan(0.023101 * rh) - 4.686035;
        return Math.round(tw * 10) / 10;
    }

    /* Cisalhamento vetorial do vento entre dois níveis (m/s) */
    function bulkShear(speedLow, dirLow, speedHigh, dirHigh) {
        if (![speedLow, dirLow, speedHigh, dirHigh].every(present)) return null;
        function vec(s, d) { var r = d * Math.PI / 180; return [-s * Math.sin(r), -s * Math.cos(r)]; }
        var a = vec(speedLow, dirLow), b = vec(speedHigh, dirHigh);
        return Math.hypot(b[0] - a[0], b[1] - a[1]);
    }

    /* Potencial de tornado por horário (SPEC.md 4.4; WMAXSHEAR, Taszarek et al., 2020) */
    function tornadoPotential(cape, liftedIndex, deepShear, lowShear) {
        if (!present(cape) || !present(deepShear)) return 'very_low';
        var wmaxshear = Math.sqrt(2 * Math.max(cape, 0)) * deepShear;
        var low = lowShear || 0, li = present(liftedIndex) ? liftedIndex : 0;
        if (cape < 100 || wmaxshear < 400) return 'very_low';
        if (wmaxshear >= 1200 && low >= 12 && li <= -4) return 'high';
        if (wmaxshear >= 800 && low >= 8) return 'moderate';
        return 'low';
    }

    function alertsOf(hour, events) {
        return (hour.alerts || []).filter(function (a) { return events.indexOf(normalize(a.event)) !== -1; });
    }

    function heatVariant(hour) {
        if (!present(hour.temp)) return null;
        if (hour.temp > HEAT_SHADE_C) return 'sombra';
        var cloud = present(hour.cloud) ? hour.cloud : 0;
        return hour.temp > HEAT_SUN_C && hour.sun_up && cloud < SUN_MAX_CLOUD ? 'sol' : null;
    }

    function wind(hour) {
        var speeds = [hour.wind_kmh, hour.gust_kmh].filter(present);
        var top = speeds.length ? Math.max.apply(null, speeds) : null;
        var strong = function (a) { return STRONG_ALERT.indexOf(normalize(a.severity)) !== -1; };
        var alerts = alertsOf(hour, ['vendaval']).filter(strong)
            .concat(alertsOf(hour, ['ventos costeiros']).filter(function (a) { return strong(a) && a.inside_polygon; }));
        return { active: (top !== null && top > WIND_KMH) || alerts.length > 0, top: top, alert: alerts[0] || null };
    }

    function evaluate(hours, openMeteo) {
        if (openMeteo === undefined) openMeteo = true;
        var indicators = {}, lifeHours = [], tornadoInfo = null;

        function mark(ind, i, details) {
            var entry = indicators[ind] || (indicators[ind] = { hours: [] });
            entry.hours.push(i);
            Object.keys(details || {}).forEach(function (key) {
                var value = details[key];
                if (!present(value)) return;
                if (key.indexOf('max_') === 0) entry[key] = present(entry[key]) ? Math.max(entry[key], value) : value;
                else if (!present(entry[key])) entry[key] = value;
            });
        }

        hours.forEach(function (hour, i) {
            var active = 0;

            var variant = heatVariant(hour);
            if (variant) {
                active++;
                mark(HEAT, i, { max_temp: hour.temp });
                if (variant === 'sombra' || !indicators[HEAT].variant) indicators[HEAT].variant = variant;
            }

            var tw = present(hour.tw) ? hour.tw : wetBulb(hour.temp, hour.rh);
            if (present(tw) && tw >= WET_BULB_C) { active++; mark(WET_BULB, i, { max_tw: tw }); }

            var storm = alertsOf(hour, ['tempestade']);
            if (hour.thunder || storm.length) {
                active++;
                var severity = storm.map(function (a) { return a.severity || ''; })
                    .sort(function (a, b) { return (SEVERITY_RANK[normalize(b)] || 0) - (SEVERITY_RANK[normalize(a)] || 0); })[0];
                mark(STORM, i, { alert_severity: severity || null });
            }

            var w = wind(hour);
            if (w.active) {
                active++;
                mark(WIND, i, {
                    max_kmh: present(w.top) && w.top > WIND_KMH ? w.top : null,
                    alert: w.alert ? w.alert.event + ' (' + w.alert.severity + ')' : null
                });
            }

            if (hour.tornado === 'high') mark(TORNADO, i, {});
            else if (hour.tornado === 'moderate') tornadoInfo = 'moderate';

            if (active >= 2) lifeHours.push(i);
        });

        var level = indicators[TORNADO] ? 'extreme' : lifeHours.length ? 'life'
            : Object.keys(indicators).length ? 'attention' : 'none';
        if (indicators[TORNADO]) tornadoInfo = null;
        return { level: level, indicators: indicators, life_hours: lifeHours,
                 tornado_info: tornadoInfo, tornado_available: !!openMeteo };
    }

    /* Preenche "%(nome)s" como o gettext do Python */
    function fill(template, values) {
        return template.replace(/%\((\w+)\)s/g, function (_, key) { return present(values[key]) ? values[key] : ''; });
    }

    function pyRound(x) {
        // round() do Python arredonda .5 para o par mais próximo
        var r = Math.round(x);
        return (Math.abs(x % 1) === 0.5 && r % 2 !== 0) ? r - 1 : r;
    }

    /* Uma linha por indicador ativo (SPEC.md 4.5); t = textos traduzidos vindos do servidor */
    function describe(result, hours, t) {
        function when(idx) {
            var labels = idx.map(function (i) { return hours[i].label || ('h' + i); });
            return labels.length === 1 ? fill(t.at, { hour: labels[0] })
                : fill(t.between, { start: labels[0], end: labels[labels.length - 1] });
        }
        var lines = [];
        ORDER.forEach(function (ind) {
            var e = result.indicators[ind];
            if (!e) return;
            var w = when(e.hours);
            if (ind === TORNADO) lines.push(fill(t.tornado, { when: w }));
            else if (ind === WET_BULB) lines.push(fill(t.wet_bulb, { value: pyRound(e.max_tw), when: w }));
            else if (ind === HEAT) lines.push(fill(t.heat, { value: pyRound(e.max_temp), when: w }));
            else if (ind === STORM) lines.push(e.alert_severity ? fill(t.storm_alert, { when: w, severity: e.alert_severity }) : fill(t.storm, { when: w }));
            else if (ind === WIND) lines.push(present(e.max_kmh) ? fill(t.wind, { value: pyRound(e.max_kmh), when: w }) : fill(t.wind_alert, { when: w, alert: e.alert }));
        });
        return lines;
    }

    function heatRecommendation(result, t) {
        var e = result.indicators[HEAT];
        if (!e) return null;
        return e.variant === 'sombra' ? t.heat_shade : t.heat_sun;
    }

    return { evaluate: evaluate, describe: describe, heatRecommendation: heatRecommendation,
             wetBulb: wetBulb, bulkShear: bulkShear, tornadoPotential: tornadoPotential, normalize: normalize };
});
