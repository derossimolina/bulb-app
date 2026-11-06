// Executa o motor em JavaScript nos casos recebidos pela entrada padrão (usado por tests/test_risk_js.py).
const path = require('path');
const risk = require(path.join(__dirname, '..', '..', 'app', 'static', 'risk.js'));

let input = '';
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
    const { cases, strings } = JSON.parse(input);
    const out = cases.map((c) => {
        const result = risk.evaluate(c.hours, c.open_meteo !== undefined ? c.open_meteo : true);
        return {
            id: c.id,
            level: result.level,
            indicators: Object.keys(result.indicators).sort(),
            heat_variant: result.indicators['IND-CALOR'] ? result.indicators['IND-CALOR'].variant : null,
            life_hours: result.life_hours,
            tornado_info: result.tornado_info,
            tornado_available: result.tornado_available,
            lines: risk.describe(result, c.hours, strings),
            recommendation: risk.heatRecommendation(result, strings),
        };
    });
    process.stdout.write(JSON.stringify(out));
});
