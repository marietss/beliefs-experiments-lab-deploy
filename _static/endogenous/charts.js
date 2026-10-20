/* Display-only charts adapted from the pilot's own-blue/group-grey graphs.
   Inputs contain only own history and stored six-human group averages. */
(() => {
    'use strict';
    const unavailable = () => { document.getElementById('chart-unavailable').hidden = false; };
    if (typeof Chart === 'undefined') { unavailable(); return; }
    const config = JSON.parse(document.getElementById('lab-chart-config').textContent);
    const blue = '#007bff', grey = '#5f6368';
    let equipmentChart, costChart;
    const cost = d => config.costMilliPoints * d * d / 1000;
    const options = (xTitle, yTitle) => ({
        responsive: true, maintainAspectRatio: false, animation: false,
        plugins: {legend: {onClick: () => {}, labels: {filter: item => item.datasetIndex !== 2}}, tooltip: {filter: item => item.datasetIndex !== 2, callbacks: {
            label: item => `${item.dataset.label}: ${window.labDisplayNumber(item.parsed.y)}`,
        }}},
        scales: {
            x: {type: 'linear', title: {display: true, text: xTitle}, ticks: {stepSize: 1}},
            y: {min: 0, title: {display: true, text: yTitle}},
        },
    });
    const checks = {id: 'labChecks', afterDraw(chart) {
        const {ctx, scales: {x}, chartArea: area} = chart;
        ctx.save();
        ctx.font = '12px sans-serif';
        ctx.strokeStyle = grey; ctx.fillStyle = grey; ctx.setLineDash([4, 4]);
        for (const [period, label] of [[config.mainPeriod, 'Accertamento principale'], [config.followUpPeriod, 'Accertamento finale']]) {
            const px = x.getPixelForValue(period);
            ctx.beginPath(); ctx.moveTo(px, area.top + 18); ctx.lineTo(px, area.bottom); ctx.stroke();
            ctx.textAlign = period === config.followUpPeriod ? 'right' : 'center';
            ctx.fillText(label, px, area.top + 12);
        }
        ctx.restore();
    }};
    // Known E threshold, supplied by the lab backend. Display only.
    // Pilot comparison marker, adapted to the allowlisted exact-lab display payload.
    const thresholdIndicator = {id: 'knownMainThreshold', afterDraw(chart) {
        const {ctx, scales: {x, y}} = chart;
        const px = x.getPixelForValue(config.mainPeriod);
        const nearRight = px > x.right - 64;
        const labelX = nearRight ? px - 10 : px + 10;
        ctx.save();
        ctx.strokeStyle = '#7652A3'; ctx.fillStyle = '#7652A3';
        ctx.lineWidth = 2.5; ctx.lineCap = 'round';
        ctx.font = '600 16px Arial'; ctx.textAlign = nearRight ? 'right' : 'left';
        ctx.textBaseline = 'middle';
        const py = y.getPixelForValue(config.threshold);
            ctx.beginPath(); ctx.arc(px, py, 6, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
            ctx.fillText(String(config.threshold), labelX, py);
        ctx.restore();
    }};
    try {
        const equipmentOptions = options('Periodo', 'Attrezzatura');
        equipmentOptions.scales.x.min = 0;
        equipmentOptions.scales.x.max = config.periods;
        equipmentOptions.scales.y.max = 100;
        equipmentChart = new Chart(document.getElementById('equipment-chart'), {
            type: 'line', plugins: [checks, thresholdIndicator], options: equipmentOptions,
            data: {datasets: [
                {label: 'La tua attrezzatura', data: config.ownHistory.map(p => ({x: p.period, y: p.equipment})), borderColor: blue, backgroundColor: blue, pointRadius: 4},
                {label: 'Attrezzatura media del gruppo', data: config.groupHistory.map(p => ({x: p.period, y: p.equipment})), borderColor: grey, backgroundColor: grey, borderDash: [6, 6], pointRadius: 3},
                {label: '', data: [], borderColor: blue, borderDash: [3, 3], pointRadius: 5},
            ]},
        });
        const canvas = document.getElementById('cost-chart');
        if (canvas && (config.equipment > 0 || document.getElementById('retirement-value'))) {
            const costOptions = options('Attrezzatura', 'Costo volontario (punti)');
            costOptions.scales.x.min = 0;
            costOptions.scales.x.max = config.equipment;
            costOptions.scales.x.ticks = {stepSize: Math.max(1, Math.ceil(config.equipment / 10)), maxRotation: 0};
            costOptions.plugins.legend.display = false;
            costChart = new Chart(canvas, {type: 'line', options: costOptions, data: {datasets: [
                {label: 'Costo volontario', data: Array.from({length: document.getElementById('retirement-value') ? 101 : config.equipment + 1}, (_, d) => ({x: d, y: cost(d)})), borderColor: blue, pointRadius: 0},
                {label: 'Costo selezionato', data: [], backgroundColor: blue, pointRadius: 6, showLine: false},
            ]}});
        }
    } catch (error) { unavailable(); }
    document.addEventListener('lab-retirement-preview', event => {
        // Chart failures must never interrupt the already-updated form controls.
        try {
            const d = event.detail;
            if (equipmentChart) {
                equipmentChart.data.datasets[2].data = [
                    {x: config.period - 1, y: config.equipment},
                    {x: config.period, y: config.equipment - d},
                ];
                equipmentChart.update('none');
            }
            if (costChart) {
                costChart.data.datasets[1].data = [{x: d, y: cost(d)}];
                costChart.update('none');
            }
        } catch (error) { unavailable(); }
    });
})();
