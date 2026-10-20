/* Display only. Integer values stay integers; fractions show two decimals.
   Exact rational/decimal text is rounded half-up without changing its source. */
(() => {
    'use strict';
    window.labDisplayNumber = value => {
        const text = String(value);
        let numerator, denominator;
        if (/^-?\d+\/\d+$/.test(text)) {
            [numerator, denominator] = text.split('/').map(BigInt);
        } else if (/^-?\d+(?:\.\d+)?$/.test(text)) {
            const digits = (text.split('.')[1] || '').length;
            numerator = BigInt(text.replace('.', ''));
            denominator = 10n ** BigInt(digits);
        } else {
            const number = Number(value);
            if (!Number.isFinite(number)) return text;
            return Number.isInteger(number) ? String(number) : number.toFixed(2);
        }
        if (numerator % denominator === 0n) return String(numerator / denominator);
        const negative = numerator < 0n;
        const absolute = negative ? -numerator : numerator;
        const cents = (absolute * 200n + denominator) / (2n * denominator);
        return (negative && cents ? '-' : '') + String(cents / 100n) + '.' + String(cents % 100n).padStart(2, '0');
    };
})();
