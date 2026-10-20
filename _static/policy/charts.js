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
    // Before Main the browser receives only support bounds, never the value.
    const thresholdIndicator = {id: 'ambiguityThreshold', afterDraw(chart) {
        const {ctx, scales: {x, y}, chartArea: area} = chart;
        const px = x.getPixelForValue(config.mainPeriod);
        ctx.save();
        ctx.strokeStyle = '#a45b00'; ctx.fillStyle = '#a45b00';
        ctx.font = 'bold 12px sans-serif'; ctx.textAlign = 'left';
        if (config.thresholdRevealed) {
            const py = y.getPixelForValue(config.threshold);
            ctx.setLineDash([6, 4]);
            ctx.beginPath(); ctx.moveTo(area.left, py); ctx.lineTo(area.right, py); ctx.stroke();
            ctx.setLineDash([]); ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2); ctx.fill();
            ctx.fillText(`Soglia dell'accertamento principale ${config.threshold}`, area.left + 6, py - 8);
        } else {
            const top = y.getPixelForValue(config.thresholdHigh);
            const bottom = y.getPixelForValue(config.thresholdLow);
            ctx.fillStyle = 'rgba(164, 91, 0, 0.12)';
            ctx.fillRect(area.left, top, area.right - area.left, bottom - top);
            ctx.strokeRect(px - 3, top, 6, bottom - top);
            ctx.fillStyle = '#a45b00';
            ctx.fillText(`Soglia sconosciuta: ${config.thresholdLow}–${config.thresholdHigh}`, area.left + 6, top - 8);
        }
        ctx.restore();
    }};
    try {
        const equipmentOptions = options('Periodo', 'Attrezzatura dopo le decisioni volontarie');
        equipmentOptions.scales.x.min = 0;
        equipmentOptions.scales.x.max = config.periods;
        equipmentOptions.scales.y.max = 100;
        equipmentChart = new Chart(document.getElementById('equipment-chart'), {
            type: 'line', plugins: [checks, thresholdIndicator], options: equipmentOptions,
            data: {datasets: [
                {label: 'La tua attrezzatura', data: config.ownHistory.map(p => ({x: p.period, y: p.equipment})), borderColor: blue, backgroundColor: blue, pointRadius: 4},
                {label: 'Media effettiva del gruppo di sei partecipanti', data: config.groupHistory.map(p => ({x: p.period, y: p.equipment})), borderColor: grey, backgroundColor: grey, borderDash: [6, 6], pointRadius: 3},
                {label: '', data: [], borderColor: blue, borderDash: [3, 3], pointRadius: 5},
                ...(Object.hasOwn(config, 'publicReportMean') ? [{label: 'Media delle risposte sull’attrezzatura pianificata all\'accertamento principale (inizio blocco)', data: [{x: config.mainPeriod, y: config.publicReportMean}], borderColor: '#7b2cbf', backgroundColor: '#7b2cbf', pointStyle: 'triangle', pointRadius: 8, showLine: false}] : []),
            ]},
        });
        const canvas = document.getElementById('cost-chart');
        if (canvas && (config.equipment > 0 || document.getElementById('retirement-value'))) {
            const costOptions = options('Attrezzatura', 'Costo volontario (punti)');
            costOptions.scales.x.min = 0;
            costOptions.scales.x.max = config.equipment;
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
