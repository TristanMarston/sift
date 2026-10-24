// Sift design-system build.
//   node design-system/build.mjs tokens   tokens.json -> app/tokens.css + app/type.css
//   node design-system/build.mjs bundle   /web components -> project/components/bundle.js + bundle.css
//   node design-system/build.mjs          both
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const web = join(here, '..');
const project = join(here, 'project');
const NOTE = '/* Generated from design-system/project/tokens.json. Edit that file, then run `npm run tokens`. */\n';
const FONTS_URL =
    'https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Figtree:wght@300..900&family=Fraunces:ital,opsz,wght,SOFT@0,9..144,100..900,0..100;1,9..144,100..900,0..100&display=swap';

function tokens() {
    const t = JSON.parse(readFileSync(join(project, 'tokens.json'), 'utf8'));
    const [first, ...rest] = t.color.themes.map((th) => th.id);
    const themed = [...t.color.tokens, ...t.shadow.tokens];
    const val = (tok, theme) => (typeof tok.value === 'string' ? tok.value : (tok.value[theme] ?? tok.value[first]));
    const block = (sel, theme, onlyChanged) =>
        `${sel} {\n  color-scheme: ${theme};\n` +
        themed
            .filter((tok) => !onlyChanged || val(tok, theme) !== val(tok, first))
            .map((tok) => `  --${tok.name}: ${val(tok, theme)};`)
            .join('\n') +
        '\n}\n';

    // In the app, next/font provides the font files; its variables go first in each stack.
    const nextFont = { serif: 'var(--font-fraunces)', sans: 'var(--font-figtree)', mono: 'var(--font-dm-mono)' };
    const fixed = [...t.spacing.tokens, ...t.radius.tokens, ...t.opacity.tokens].map((tok) => `  --${tok.name}: ${tok.value};`);
    const fonts = Object.entries(t.type.families).map(([k, stack]) => `  --font-${k}: ${nextFont[k] ? nextFont[k] + ', ' : ''}${stack};`);

    const css =
        NOTE +
        block(`:root,\n[data-theme="${first}"]`, first) +
        rest.map((id) => block(`.${id},\n[data-theme="${id}"]`, id, true)).join('') +
        `:root {\n${[...fixed, ...fonts].join('\n')}\n}\n`;
    writeFileSync(join(web, 'app/tokens.css'), css);

    const rem = (v) => (/px$/.test(v) ? `${parseFloat(v) / 16}rem` : v);
    const utils = t.type.groups.flatMap((g) =>
        g.styles.map(
            (s) =>
                `@utility ${s.name} {\n  font-family: var(--font-${s.family ?? g.family});\n  font-size: ${rem(s.fontSize)};\n` +
                `  line-height: ${rem(s.lineHeight)};\n  letter-spacing: ${s.letterSpacing ?? '0'};\n  font-weight: ${s.fontWeight ?? 400};\n` +
                (s.fontStyle ? `  font-style: ${s.fontStyle};\n` : '') +
                '}\n',
        ),
    );
    writeFileSync(join(web, 'app/type.css'), NOTE + utils.join('\n'));
    console.log('tokens: wrote app/tokens.css and app/type.css');
}

// React comes from the preview frame's globals (React 18), so the bundle maps imports onto them.
const JSX_SHIM = `const R = window.React;
export const Fragment = R.Fragment;
export function jsx(type, props, key) { return R.createElement(type, key === undefined ? props : { ...props, key }); }
export const jsxs = jsx, jsxDEV = jsx;`;
const GLOBALS = { react: 'React', 'react-dom': 'ReactDOM', 'react-dom/client': 'ReactDOM' };

async function bundle() {
    const { build } = await import('esbuild');
    const entry = join(here, 'entry.tsx');
    const names = [...readFileSync(entry, 'utf8').split('// Helpers')[0].matchAll(/^export \{ (\w+) \}/gm)].map((m) => m[1]);
    const header = `/* @ds-bundle: ${JSON.stringify({ format: 4, namespace: 'Sift', components: names.map((name) => ({ name })) })} */`;

    const result = await build({
        entryPoints: [entry],
        bundle: true,
        write: false,
        format: 'iife',
        globalName: 'Sift',
        minify: true,
        target: 'es2020',
        jsx: 'automatic',
        banner: { js: header },
        define: { 'process.env.NODE_ENV': '"production"' },
        logLevel: 'error',
        plugins: [
            {
                name: 'react-globals',
                setup(b) {
                    b.onResolve({ filter: /^react(-dom)?(\/client)?$|^react\/jsx(-dev)?-runtime$/ }, (a) => ({ path: a.path, namespace: 'g' }));
                    b.onLoad({ filter: /.*/, namespace: 'g' }, (a) => ({
                        contents: a.path.includes('jsx') ? JSX_SHIM : `module.exports = window.${GLOBALS[a.path]};`,
                        loader: 'js',
                    }));
                },
            },
        ],
    });
    let js = result.outputFiles[0].text.replaceAll('</script', '<\\/script').replaceAll('<!--', '\\x3C!--');
    writeFileSync(join(project, 'components/bundle.js'), js);

    const out = join(project, 'components/bundle.css');
    execFileSync(join(web, 'node_modules/.bin/tailwindcss'), ['-i', join(here, 'bundle.entry.css'), '-o', out, '--minify'], { cwd: web, stdio: 'pipe' });
    const css = readFileSync(out, 'utf8');
    if (/<\/style/i.test(css)) throw new Error('bundle.css contains </style');
    writeFileSync(out, `@import url("${FONTS_URL}");\n${css}`);
    console.log(`bundle: ${names.length} components, ${(js.length / 1024).toFixed(0)} KB js, ${(css.length / 1024).toFixed(0)} KB css`);
}

const cmd = process.argv[2];
if (!cmd || cmd === 'tokens') tokens();
if (!cmd || cmd === 'bundle') await bundle();
