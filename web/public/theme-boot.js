// Runs before hydration (see app/layout.tsx).
// Applies the saved theme: light is the default and the OS setting is ignored.
try {
    if (localStorage.getItem('sift-theme') === 'dark') document.documentElement.classList.add('dark');
} catch {}
// Lets :active press states fire on iOS Safari.
document.addEventListener('touchstart', function () {}, { passive: true });
