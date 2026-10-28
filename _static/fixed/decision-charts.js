/* Decision-only presentation. Existing charts own data, cost calculations,
   threshold disclosure and preview updates; results never load this script. */
(() => {
    'use strict';
    if (typeof Chart === 'undefined') return;
    try {
        const config = JSON.parse(document.getElementById('lab-chart-config').textContent);
        const prepareCost = cost => {
            cost.config.options.scales.x.title.text = 'Unità di attrezzatura';
            cost.config.options.scales.y.title.text = 'Costo';
            cost.config.options.scales.x.min = 0;
            cost.config.options.scales.x.max = 100;
            cost.config.options.scales.x.ticks = {stepSize: 10, maxRotation: 0};
            cost.config.options.scales.y.min = 0;
            cost.config.options.scales.y.max = 800;
            cost.config.options.scales.y.ticks = {stepSize: 100};
            // Full unchanged cost function; unavailable choices have no tooltip.
            cost.data.datasets[0].segment = {
                borderColor: context => context.p1.parsed.x > config.equipment ? '#b8b8b8' : '#007bff',
            };
            const existingFilter = cost.config.options.plugins.tooltip.filter;
            cost.config.options.plugins.tooltip.filter = item => item.parsed.x <= config.equipment && existingFilter(item);
            cost.data.datasets[0].label = 'Costo della dismissione';
            // Chart.js draws higher-order datasets first: the point stays above the curve.
            cost.data.datasets[0].order = 1;
            cost.data.datasets[1].order = 0;
        };
        const drawSelectedCost = chart => {
            const point = chart.getDatasetMeta(1).data[0];
            if (!point) return;
            // Reuse the exact, already formatted preview shown by the validated controls.
            const text = document.getElementById('selected-cost').textContent.trim();
            const {ctx, chartArea: area} = chart;
            ctx.save();
            ctx.font = 'bold 14px sans-serif';
            const width = ctx.measureText(text).width + 16, height = 25;
            const left = Math.max(area.left, Math.min(point.x + 10, area.right - width));
            const preferredTop = point.y - height - 10;
            const top = Math.max(area.top, Math.min(preferredTop < area.top ? point.y + 10 : preferredTop, area.bottom - height));
            ctx.fillStyle = '#fff'; ctx.fillRect(left, top, width, height);
            ctx.strokeStyle = '#007bff'; ctx.lineWidth = 1; ctx.setLineDash([]);
            ctx.strokeRect(left, top, width, height);
            ctx.fillStyle = '#212529'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
            ctx.fillText(text, left + 8, top + height / 2);
            ctx.restore();
        };
        const formatAmounts = chart => {
            const format = window.labDecisionDisplayNumber;
            if (chart.canvas.id === 'cost-chart') chart.config.options.plugins.tooltip.callbacks.label = item => `${item.dataset.label}: ${format(item.parsed.y)}`;
            for (const axis of Object.values(chart.config.options.scales)) {
                axis.ticks ||= {};
                axis.ticks.callback = value => format(value);
            }
        };
        // Apply labels before the first draw, so technical legend text never flashes.
        Chart.register({
            id: 'labDecisionInterface',
            beforeInit(chart) {
                if (chart.canvas.id === 'cost-chart') prepareCost(chart);
                formatAmounts(chart);
                if (chart.canvas.id === 'cost-chart') window.labGraphLayout(chart);
            },
            afterDatasetsDraw(chart) {
                if (chart.canvas.id === 'cost-chart') drawSelectedCost(chart);
            },
        });
    } catch (error) {
        // Presentation cannot interrupt the independent decision controls.
        document.getElementById('chart-unavailable').hidden = false;
    }
})();
