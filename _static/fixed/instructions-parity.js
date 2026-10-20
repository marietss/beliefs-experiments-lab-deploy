/* Local instruction navigation only; no model fields, economic data or requests. */
(() => {
    'use strict';
    for (const deck of document.querySelectorAll('[data-instruction-deck]')) {
        const panels = Array.from(deck.querySelectorAll('[data-instruction-panel]'));
        if (!panels.length) continue;
        const next = deck.querySelector('[data-instruction-next]');
        const back = deck.querySelector('[data-instruction-back]');
        const finish = deck.querySelector('[data-instruction-finish]');
        const progress = deck.querySelector('[data-instruction-progress]');
        let current = 0;
        const show = () => {
            panels.forEach((panel, index) => { panel.hidden = index !== current; });
            back.hidden = current === 0;
            next.hidden = current === panels.length - 1;
            finish.hidden = current !== panels.length - 1;
            progress.textContent = `Istruzioni ${current + 1} / ${panels.length}`;
        };
        next.addEventListener('click', () => { current++; show(); window.scrollTo(0, 0); });
        back.addEventListener('click', () => { current--; show(); window.scrollTo(0, 0); });
        const form = deck.closest('form');
        if (form) form.addEventListener('submit', event => {
            if (current < panels.length - 1) { event.preventDefault(); current++; show(); window.scrollTo(0, 0); }
        });
        show();
    }
    for (const button of document.querySelectorAll('[data-comparable-review]')) {
        const dialog = document.getElementById(button.dataset.comparableReview);
        button.addEventListener('click', () => dialog.showModal());
        dialog.querySelector('[data-comparable-close]').addEventListener('click', () => dialog.close());
    }
})();
