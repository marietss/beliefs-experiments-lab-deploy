/* Survey inputs only; no economic values, participant variables or live calls. */
(() => {
    'use strict';
    const button = document.getElementById('survey-continue');
    const scales = Array.from(document.querySelectorAll('[data-survey-scale]'));
    const answered = scale => scale.querySelector('input[type="hidden"]').value !== '';
    const updateClarityFollowup = () => {
        const followup = document.getElementById('clarity-improvement');
        if (!followup) return;
        const field = document.getElementById('id_experiment_clarity');
        const visible = field.value !== '' && Number(field.value) < 5;
        followup.hidden = !visible;
        followup.querySelector('textarea').required = visible;
    };
    const updateButton = () => { button.disabled = !scales.every(answered); };
    for (const scale of scales) {
        const slider = scale.querySelector('input[type="range"]');
        const field = scale.querySelector('input[type="hidden"]');
        const display = scale.querySelector('.survey-selected strong');
        const choose = () => {
            const value = Number(slider.value);
            if (!Number.isInteger(value) || value < 0 || value > 10) return;
            field.value = String(value);
            display.textContent = String(value);
            slider.removeAttribute('data-untouched');
            slider.setAttribute('aria-valuetext', String(value));
            updateButton();
            updateClarityFollowup();
        };
        slider.addEventListener('input', choose);
        slider.addEventListener('change', choose);
        slider.addEventListener('click', choose);
        slider.addEventListener('keydown', event => {
            if (event.key === 'Enter') { event.preventDefault(); choose(); }
        });
    }
    // Retain valid bound values when oTree redisplays another validation error.
    updateButton();
    updateClarityFollowup();
    button.closest('form').addEventListener('submit', event => {
        const missing = scales.find(scale => !answered(scale));
        if (missing) {
            event.preventDefault();
            missing.querySelector('input[type="range"]').focus();
        }
    });
})();
