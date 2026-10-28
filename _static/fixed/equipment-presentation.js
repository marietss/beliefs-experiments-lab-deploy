/* Shared equipment-graph presentation for Decision and Results only.
   Data and treatment-specific threshold/message plugins stay with each app. */
(() => {
    'use strict';
    if (typeof Chart === 'undefined') return;
    try {
        const config = JSON.parse(document.getElementById('lab-chart-config').textContent);
        const prepareEquipment = equipment => {
            equipment.config.options.scales.x.title.text = 'Periodo';
            equipment.config.options.scales.y.title.text = 'Unità di attrezzatura';
            equipment.data.datasets[0].label = 'La tua attrezzatura';
            equipment.data.datasets[1].label = 'Attrezzatura media del tuo gruppo';
            equipment.data.datasets[0].pointStyle = 'circle';
            equipment.data.datasets[1].pointStyle = 'circle';
            const group = equipment.data.datasets[1];
            // Every firm starts at 100; anchor the displayed group trajectory
            // there without adding observations to the stored group history.
            group.data = [{x: 0, y: 100}, ...group.data.filter(point => point.x !== 0)];
            group.showLine = true;
            group.borderColor = '#5f6368';
            group.borderDash = [2, 4];
            group.borderWidth = 2;
            // Keep the existing preview dataset/index, without a legend or tooltip entry.
            equipment.data.datasets[2].label = '';
            equipment.config.options.plugins.legend.labels ||= {};
            equipment.config.options.plugins.legend.labels.usePointStyle = true;
            equipment.config.options.plugins.legend.labels.filter = item => item.datasetIndex !== 2;
            equipment.config.options.plugins.tooltip.filter = item => item.datasetIndex !== 2;
            const hasBounds = Number.isFinite(config.thresholdLow) && Number.isFinite(config.thresholdHigh);
            const revealedThreshold = config.thresholdRevealed === true && Number.isFinite(config.threshold);
            const showRange = hasBounds && !revealedThreshold;
            const reference = equipment.config.plugins.find(plugin => plugin.id === 'knownMainThreshold' || plugin.id === 'ambiguityThreshold');
            if (reference) {
                // Change hooks on the existing plugin object so cached Chart.js
                // descriptors retain the same object and treatment identity.
                delete reference.afterDraw;
                reference.beforeDatasetsDraw = chart => {
                    const {ctx, scales: {x, y}} = chart;
                    const px = x.getPixelForValue(config.mainPeriod);
                    const values = showRange ? [config.thresholdLow, config.thresholdHigh] : [config.threshold];
                    ctx.save();
                    ctx.strokeStyle = '#7652A3'; ctx.fillStyle = '#7652A3';
                    ctx.lineWidth = 2.5; ctx.lineCap = 'round'; ctx.setLineDash([]);
                    ctx.font = '600 12px sans-serif'; ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';
                    if (showRange) {
                        const top = y.getPixelForValue(config.thresholdHigh);
                        const bottom = y.getPixelForValue(config.thresholdLow);
                        ctx.fillRect(px - 8, top, 16, bottom - top);
                    }
                    for (const value of values) {
                        const py = y.getPixelForValue(value);
                        ctx.beginPath();
                        ctx.moveTo(px - 16, py); ctx.lineTo(px + 16, py); ctx.stroke();
                        ctx.fillText(window.labDisplayNumber(value), px + 22, py);
                    }
                    ctx.restore();
                };
                delete reference.afterDatasetsDraw;
            }
            if (Object.hasOwn(config, 'publicReportMean') && equipment.data.datasets[3]) {
                const planned = equipment.data.datasets[3];
                // Keep the public mean distinct from the anonymous individual plans.
                planned.label = 'Attrezzatura media prevista';
                planned.pointStyle = 'rect';
                planned.pointRadius = 6;
                planned.pointHoverRadius = 8;
                planned.showLine = false;
                planned.order = -1;
                if (Array.isArray(config.publicReportPlans)) {
                    equipment.data.datasets.push({
                        label: 'Attrezzatura individuale prevista',
                        data: config.publicReportPlans.map(value => ({x: config.mainPeriod, y: value})),
                        showLine: false,
                        pointStyle: 'rect',
                        pointRadius: 4,
                        pointHoverRadius: 5,
                        pointBackgroundColor: 'rgba(95, 99, 104, 0.45)',
                        pointBorderColor: 'rgba(95, 99, 104, 0.45)',
                        pointBorderWidth: 1,
                        order: 0,
                    });
                }
                equipment.config.options.plugins.legend.labels.usePointStyle = true;
            }
            const checks = equipment.config.plugins.findIndex(plugin => plugin.id === 'labChecks');
            if (checks !== -1) Object.assign(equipment.config.plugins[checks], {
                id: 'labChecks',
                beforeDatasetsDraw(chart) {
                    if (!Object.hasOwn(config, 'publicReportMean')) return;
                    const {ctx, scales: {x, y}, chartArea: area} = chart;
                    ctx.save();
                    ctx.strokeStyle = '#5f6368';
                    ctx.setLineDash([4, 4]);
                    for (const period of [config.mainPeriod, config.followUpPeriod]) {
                        const px = x.getPixelForValue(period);
                        // Leave a small clear footprint behind each public plan
                        // square. Its translucent grey stays unchanged, but the
                        // reference line cannot show through it.
                        const gaps = period === config.mainPeriod && Object.hasOwn(config, 'publicReportMean')
                            ? chart.data.datasets.slice(3).flatMap(dataset => dataset.data.map(point => {
                                const py = y.getPixelForValue(point.y);
                                const radius = dataset.pointRadius + 1;
                                return [py - radius, py + radius];
                            })).sort((a, b) => a[0] - b[0]) : [];
                        let start = area.top + 30;
                        ctx.beginPath();
                        for (const [top, bottom] of gaps) {
                            if (bottom <= start || top >= area.bottom) continue;
                            if (top > start) {ctx.moveTo(px, start); ctx.lineTo(px, top);}
                            start = Math.max(start, bottom);
                        }
                        if (start < area.bottom) {ctx.moveTo(px, start); ctx.lineTo(px, area.bottom);}
                        ctx.stroke();
                    }
                    ctx.restore();
                },
                afterDraw(chart) {
                    const {ctx, scales: {x}, chartArea: area} = chart;
                    ctx.save();
                    ctx.font = '11px sans-serif';
                    ctx.strokeStyle = '#5f6368'; ctx.fillStyle = '#5f6368';
                    ctx.setLineDash([4, 4]);
                    for (const [period, label] of [[config.mainPeriod, ['Accertamento', 'principale']], [config.followUpPeriod, ['Accertamento', 'finale']]]) {
                        const px = x.getPixelForValue(period);
                        if (!Object.hasOwn(config, 'publicReportMean')) {
                            ctx.beginPath(); ctx.moveTo(px, area.top + 30); ctx.lineTo(px, area.bottom); ctx.stroke();
                        }
                        ctx.textAlign = 'center';
                        label.forEach((line, index) => ctx.fillText(line, px, area.top + 10 + index * 13));
                    }
                    ctx.restore();
                },
            });
        };
        const prepareLayout = chart => {
            // Leave numerical limits intact. Allow boundary dots to extend into
            // a small internal margin instead of clipping at the plot edge.
            chart.config.options.layout ||= {};
            chart.config.options.layout.padding = {top: 8, right: chart.canvas.id === 'equipment-chart' ? 44 : 12, bottom: 8, left: 12};
            for (const dataset of chart.data.datasets) dataset.clip = 10;
            for (const axis of Object.values(chart.config.options.scales)) {
                axis.title.font = {...axis.title.font, size: 16};
                axis.ticks ||= {};
                axis.ticks.font = {...axis.ticks.font, size: 16};
            }
        };
        window.labGraphLayout = prepareLayout;
        Chart.register({
            id: 'labEquipmentPresentation',
            beforeInit(chart) {
                if (chart.canvas.id !== 'equipment-chart') return;
                prepareEquipment(chart);
                prepareLayout(chart);
                // Display only: use the same compact precision as Decision.
                const format = window.labDisplayNumber;
                chart.config.options.plugins.tooltip.callbacks.title = items => items.length ? `Periodo: ${format(items[0].parsed.x)}` : '';
                chart.config.options.plugins.tooltip.callbacks.label = item =>
                    item.datasetIndex === 3 && Object.hasOwn(config, 'publicReportMean')
                        ? `Attrezzatura media prevista al Periodo ${config.mainPeriod}: ${format(item.parsed.y)} unità`
                        : `${item.dataset.label}: ${format(item.parsed.y)}`;
                for (const axis of Object.values(chart.config.options.scales)) {
                    axis.ticks ||= {};
                    axis.ticks.callback = value => format(value);
                }
            },
        });
    } catch (error) {
        const unavailable = document.getElementById('chart-unavailable');
        if (unavailable) unavailable.hidden = false;
    }
})();
