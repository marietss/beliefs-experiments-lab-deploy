/* Presentation only: both existing report fields require a deliberate choice. */
(() => {
    'use strict';
    const button = document.getElementById('reports-continue');
    const selected = [null, null];
    const controls = [
        ['report-own-slider', 'report-own-value', 'report-own-selected'],
        ['report-group-slider', 'report-group-value', 'report-group-selected'],
    ];
    button.disabled = true;
    controls.forEach(([sliderId, fieldId, displayId], index) => {
        const slider = document.getElementById(sliderId);
        const field = document.getElementById(fieldId);
        const display = document.getElementById(displayId);
        field.value = '';
        slider.setAttribute('data-untouched', '');
        display.textContent = '—';
        const choose = () => {
            const value = Number(slider.value);
            if (!Number.isInteger(value) || value < 0 || value > 100) return;
            selected[index] = value;
            field.value = String(value);
            display.textContent = String(value);
            slider.removeAttribute('data-untouched');
            slider.setAttribute('aria-valuetext', String(value));
            button.disabled = selected.some(answer => answer === null);
        };
        slider.addEventListener('input', choose);
        slider.addEventListener('change', choose);
        slider.addEventListener('click', choose);
        slider.addEventListener('keydown', event => {
            if (event.key === 'Enter') { event.preventDefault(); choose(); }
        });
    });
    button.closest('form').addEventListener('submit', event => {
        const missing = selected.findIndex(answer => answer === null);
        if (missing !== -1) {
            event.preventDefault();
            document.getElementById(controls[missing][0]).focus();
        }
    });
})();
