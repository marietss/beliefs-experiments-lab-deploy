/* Slider/preview only. All settlement and synchronization remain server-side. */
(() => {
    'use strict';
    const config = JSON.parse(document.getElementById('lab-chart-config').textContent);
    const slider = document.getElementById('retirement-slider');
    const field = document.getElementById('retirement-value');
    const confirm = document.getElementById('confirm-retirement');
    let selected = null;
    const displayNumber = window.labDisplayNumber;
    window.labDecisionDisplayNumber = displayNumber;
    // Server-rendered balances already use the same display convention.
    const formatMilli = value => displayNumber(`${value}/1000`);
    if (slider) {
        field.value = '';
        confirm.disabled = true;
        slider.setAttribute('data-untouched', '');
        const select = () => {
            const amount = Number(slider.value);
            if (!Number.isInteger(amount) || amount < 0 || amount > config.equipment) return;
            selected = amount;
            slider.removeAttribute('data-untouched');
            field.value = String(amount);
            const selectedUnits = document.getElementById('selected-unit-count');
            if (selectedUnits) selectedUnits.textContent = String(amount);
            slider.setAttribute('aria-valuetext', `${amount} unità dismesse`);
            document.getElementById('selected-retirement').textContent = `${amount} unità`;
            document.getElementById('remaining-equipment').textContent = `${config.equipment - amount} unità`;
            document.getElementById('selected-cost').textContent = `${formatMilli(config.costMilliPoints * amount * amount)} punti`;
            confirm.disabled = false;
            // Charts may fail or be absent without breaking controls.
            document.dispatchEvent(new CustomEvent('lab-retirement-preview', {detail: amount}));
        };
        slider.addEventListener('input', select);
        slider.addEventListener('change', select);
        // A deliberate click at the minimum counts as choosing 0; untouched has no visible thumb.
        slider.addEventListener('click', select);
        slider.addEventListener('keydown', event => {
            if (event.key === 'Enter') { event.preventDefault(); select(); }
        });
    } else {
        field.value = '0';
        confirm.disabled = false;
    }
    confirm.closest('form').addEventListener('submit', event => {
        if (slider && selected === null) {
            event.preventDefault();
            slider.focus();
        }
    });
    const dialog = document.getElementById('rules-dialog');
    document.getElementById('rules-open').addEventListener('click', () => dialog.showModal());
    document.getElementById('rules-close').addEventListener('click', () => dialog.close());
})();
