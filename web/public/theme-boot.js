// Runs before hydration (see app/layout.tsx).
// Applies the saved theme: light is the default and the OS setting is ignored.
try {
    if (localStorage.getItem('sift-theme') === 'dark') document.documentElement.classList.add('dark');
    // Landing palette under comparison: "ink" (default) or "forest".
    // The light "Ink" landing is only for the /landing comparison pages; the home page is always forest.
    if (localStorage.getItem('sift-palette') === 'ink' && location.pathname.indexOf('/landing') === 0) {
        document.documentElement.dataset.palette = 'ink';
        var meta = document.querySelector('meta[name="theme-color"]');
        if (meta) meta.content = '#f3f4f2';
    }
} catch {}
// Lets :active press states fire on iOS Safari.
document.addEventListener('touchstart', function () {}, { passive: true });
