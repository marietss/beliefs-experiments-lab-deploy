/* Only server acknowledgements change allocations and earnings. */
(() => {
    'use strict';
    const ball = document.getElementById('active-ball');
    const connection = document.getElementById('bucket-connection');
    const targets = [...document.querySelectorAll('[data-bucket]')];
    const form = document.getElementById('form');
    let current = null, pending = null, drag = null, expiresAt = 0, submitting = false;
    let syncing = false, lastRequestAt = 0, returning = false;
    const euro = cents => '€' + (cents / 100).toFixed(2).replace('.', ',');
    const send = data => {
        if (typeof liveSend === 'function') { lastRequestAt = Date.now(); liveSend(data); }
    };
    const atBall = () => {
        const ballRect = ball.getBoundingClientRect();
        const x = ballRect.left + ballRect.width / 2;
        const y = ballRect.top + ballRect.height / 2;
        return targets.find(el => {
            const r = el.getBoundingClientRect();
            return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
        });
    };
    function sendPending() {
        if (!pending || pending.sent || syncing) return;
        pending.sent = true;
        pending.message.expected_index = current.balls_placed + 1;
        send(pending.message);
    }
    function sync() {
        if (syncing || submitting) return;
        syncing = true;
        send({action: 'sync'});
    }
    function render(data, acknowledged = true) {
        if (!data || typeof data.balls_placed !== 'number') { syncing = false; sync(); return; }
        // Never roll the display/index back to an older state.
        if (current && data.balls_placed < current.balls_placed) return;
        current = data;
        if (acknowledged) {
            syncing = false;
            if (pending && (pending.sent || data.done)) {
                // A current-state reply may reject a duplicate/malformed request.
                // It still ends this interaction; the next index comes from data.
                pending = null;
                resetDrag();
            }
        }
        expiresAt = Date.now() + data.seconds_remaining * 1000;
        document.getElementById('balls-remaining').textContent = data.balls_remaining;
        for (const [color, count, cents] of [['blue', data.balls_blue, data.blue_earnings_cents], ['yellow', data.balls_yellow, data.yellow_earnings_cents]]) {
            document.getElementById(color + '-summary').textContent = (color === 'blue' ? 'Blu' : 'Giallo') + ': ' + count + ' palline — ' + euro(cents);
            const container = document.getElementById(color + '-balls');
            container.replaceChildren(...Array.from({length: count}, () => {
                const dot = document.createElement('span'); dot.className = 'placed-ball'; return dot;
            }));
        }
        document.getElementById('bucket-earnings').textContent = euro(data.total_earnings_cents);
        connection.textContent = pending ? 'Registrazione…' : '';
        ball.disabled = !!pending || data.done || returning;
        if (data.done && !submitting) { resetDrag(); submitting = true; ball.hidden = true; form.requestSubmit(); }
        if (!data.done) sendPending();
    }
    window.liveRecv = render;
    ball.addEventListener('pointerdown', event => {
        if (ball.disabled || !current || current.done || event.button !== 0) return;
        event.preventDefault();
        ball.classList.remove('returning');
        drag = {x: event.clientX, y: event.clientY, pointerId: event.pointerId};
        ball.classList.add('dragging');
    });
    function moveBall(event) {
        if (!drag || event.pointerId !== drag.pointerId) return;
        ball.style.transform = `translate(${event.clientX-drag.x}px, ${event.clientY-drag.y}px)`;
        const target = atBall();
        targets.forEach(el => el.classList.toggle('drop-target', el === target));
    }
    window.addEventListener('pointermove', moveBall);
    function resetDrag(animate = false) {
        drag = null;
        if (animate) {
            returning = true;
            ball.disabled = true;
            ball.classList.add('returning');
            window.setTimeout(() => {
                ball.classList.remove('returning');
                returning = false;
                ball.disabled = !!pending || !!current.done;
            }, 180);
        }
        ball.style.transform = '';
        ball.classList.remove('dragging');
        targets.forEach(el => el.classList.remove('drop-target'));
    }
    window.addEventListener('pointerup', event => {
        if (!drag || event.pointerId !== drag.pointerId) return;
        moveBall(event); // Chrome may deliver the release without a final move.
        const target = atBall();
        resetDrag(!target);
        if (!target || pending || !current || current.done) return;
        pending = {message: {action: 'allocate', bucket: target.dataset.bucket, expected_index: current.balls_placed + 1}, sent: false};
        ball.disabled = true; connection.textContent = 'Registrazione…'; sendPending();
    });
    window.addEventListener('pointercancel', resetDrag);
    window.addEventListener('blur', resetDrag);
    form.addEventListener('submit', event => {
        if (!current || !current.done) {
            // The native persisted-deadline timeout is allowed through at expiry.
            const timeout = form.querySelector('input[name="timeout_happened"]');
            if (!(timeout && timeout.value === '1')) { event.preventDefault(); sync(); }
        }
    });
    setInterval(() => {
        const seconds = Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000));
        document.getElementById('bucket-clock').textContent = String(Math.floor(seconds / 60)).padStart(2, '0') + ':' + String(seconds % 60).padStart(2, '0');
    }, 200);
    // Only one request is outstanding: queue a drop behind an earlier sync.
    // Polls must not masquerade as an allocation acknowledgement or interrupt drag.
    setInterval(() => {
        if (submitting || drag) return;
        if ((syncing || (pending && pending.sent)) && Date.now() - lastRequestAt >= 3000) {
            // Recover a lost acknowledgement using server state, never a new
            // allocation. Accepted drops remain persisted and cannot be paid twice.
            syncing = false;
            sync();
        } else if (!pending) sync();
    }, 1500);
    window.addEventListener('online', () => { if (!pending) sync(); });
    if (typeof liveSocket !== 'undefined' && liveSocket.addEventListener) {
        let opened = liveSocket.readyState === 1;
        liveSocket.addEventListener('open', () => {
            if (opened) { syncing = false; sync(); }
            opened = true;
        });
    }
    render(js_vars.bucket, false);
    sync();
})();
