/* Browser-local unpaid illustration. No experimental form fields or requests. */
(() => {
    'use strict';
    const slider = document.getElementById('retirement-slider');
    const confirm = document.getElementById('confirm-retirement');
    const field = document.getElementById('retirement-value');
    const config = JSON.parse(document.getElementById('lab-chart-config').textContent);
    window.labDecisionDisplayNumber = window.labDisplayNumber;
    let selected = null;
    const preview = () => {
        const amount = Number(slider.value);
        if (!Number.isInteger(amount) || amount < 0 || amount > config.equipment) return;
        selected = amount;
        field.value = String(amount);
        slider.removeAttribute('data-untouched');
        slider.setAttribute('aria-valuetext', `${amount} unità dismesse`);
        document.getElementById('selected-unit-count').textContent = String(amount);
        document.getElementById('selected-retirement').textContent = `${amount} unità`;
        document.getElementById('remaining-equipment').textContent = `${config.equipment - amount} unità`;
        document.getElementById('selected-cost').textContent = `${window.labDisplayNumber(`${config.costMilliPoints * amount * amount}/1000`)} punti`;
        document.getElementById('practice-feedback').textContent = '';
        confirm.disabled = false;
        document.dispatchEvent(new CustomEvent('lab-retirement-preview', {detail: amount}));
    };
    slider.addEventListener('input', preview);
    slider.addEventListener('change', preview);
    slider.addEventListener('click', preview);
    slider.addEventListener('keydown', event => {
        if (event.key === 'Enter') { event.preventDefault(); preview(); }
    });
    confirm.addEventListener('click', () => {
        if (selected === null) return;
        document.getElementById('practice-feedback').textContent = 'Scelta di prova confermata. Non ha alcun effetto sul tuo portafoglio sperimentale. Puoi provare un’altra scelta o continuare.';
    });
    const dialog = document.getElementById('rules-dialog');
    document.getElementById('rules-open').addEventListener('click', () => dialog.showModal());
    document.getElementById('rules-close').addEventListener('click', () => dialog.close());
})();
