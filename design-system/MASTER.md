# Whiteboard Coach - Design System (MASTER)

Source of truth for visual + interaction design. Page-specific overrides live in
`design-system/pages/<page>.md` and take precedence over this file when present.

Stack: Next.js 16 (App Router), React 19, Tailwind v4 (CSS-first `@theme`),
`next/font/google`. Tailwind v4 means **no `tailwind.config.js`** - tokens go
directly in `app/globals.css` under `@theme` / `@theme inline`.

---

## 1. Product framing

- Socratic interview-prep coach for FAANG-tier algorithm rounds.
- Audience: working/aspiring SWEs preparing for technical interviews. Adult,
  technically literate, time-pressured. Not children.
- Voice: warm, encouraging, slightly playful, never patronizing. Think
  "smart friend who's been through this" - not "kids' learning app".
- Two anchor surfaces: the topic-DAG roadmap (`/`) and the per-question
  practice session (`/practice/[id]`).

---

## 2. Visual style: Soft Claymorphism (toned for adults)

Soft, rounded, tactile - but pulled back from "toy-like". Cards feel like
pressable physical objects via double shadows, never via thick outlines.

Style rules:

| Concern | Rule |
|---------|------|
| Corner radius | 12-20px on cards (`rounded-xl` / `rounded-2xl`). Buttons 12px. Pills 9999px. |
| Border | Thin (1px), low-contrast tint (e.g. `border-indigo-100` light, `border-indigo-900/40` dark). No 3-4px chunky borders. |
| Shadow | Double-layer: tight near-shadow + diffuse far-shadow. Indigo-tinted, not pure black. See `--shadow-clay` token below. |
| Press feedback | Translate 1-2px on hover, 1px down on `:active`, 200ms ease-out. No scale transforms (cause layout shift). |
| Inner highlight | Optional `inset 0 -2px 0 rgba(0,0,0,.04)` for tactile lip on key surfaces. Use sparingly. |
| Density | Generous padding (16-24px on cards). Don't try to be IDE-dense. |

**Avoid:** hard outlines, neon glows, gradient overload, clay extremes (puffy
3D cartoony shapes), "kid-app" mascots/illustrations.

---

## 3. Color palette

"Learning indigo + progress green" - indigo for surfaces and primary, green
reserved for forward momentum (CTAs, mastered, correct).

### Light mode (default)

| Role | Hex | Tailwind ref | Usage |
|------|-----|--------------|-------|
| Primary | `#4F46E5` | indigo-600 | Brand, links, primary buttons, focus ring |
| Primary hover | `#4338CA` | indigo-700 | Primary button hover |
| Secondary | `#818CF8` | indigo-400 | Soft accents, secondary chips |
| Tint | `#EEF2FF` | indigo-50 | Tinted card backgrounds, hover surfaces |
| CTA | `#22C55E` | green-500 | "Start session", "Submit", forward actions |
| CTA hover | `#16A34A` | green-600 | CTA hover |
| Background | `#FAFAF9` | stone-50 | App background (warmer than zinc) |
| Surface | `#FFFFFF` | white | Cards, elevated surfaces |
| Surface muted | `#F5F3FF` | violet-50 | Subtle inset surfaces |
| Line | `#E4E4E7` | zinc-200 | Default borders |
| Line accent | `#C7D2FE` | indigo-200 | Indigo-tinted borders on primary cards |
| Text | `#312E81` | indigo-900 | Headings, primary text |
| Text body | `#1F2937` | gray-800 | Body text (slightly less dark than indigo-900 - easier reading) |
| Text muted | `#475569` | slate-600 | Captions, helper text. **Minimum** for muted - never go lighter. |
| Success | `#16A34A` | green-600 | Mastered, correct |
| Warn | `#F59E0B` | amber-500 | In-progress, needs review |
| Error | `#DC2626` | red-600 | Wrong, blocked |

### Dark mode

| Role | Hex | Notes |
|------|-----|-------|
| Primary | `#A5B4FC` | indigo-300 - lighter, lift contrast on dark |
| Background | `#0B0B0E` | Near-black, warm |
| Surface | `#161620` | Slightly lifted |
| Surface muted | `#1E1B30` | Indigo-tinted |
| Line | `#2A2A35` | Subtle |
| Line accent | `#3730A3` | indigo-800 |
| Text | `#F4F4F5` | zinc-100 |
| Text muted | `#A1A1AA` | zinc-400 - **minimum**. Never go lighter than this. |
| CTA | `#4ADE80` | green-400 - lifted for dark |

### Difficulty / status semantic colors

Used in question pills, topic status, etc.

| State | Light bg | Light text | Dark bg | Dark text |
|-------|----------|------------|---------|-----------|
| Easy / mastered | `#DCFCE7` (green-100) | `#166534` (green-800) | `#14532D` (green-900) | `#86EFAC` (green-300) |
| Medium / in-progress | `#FEF3C7` (amber-100) | `#92400E` (amber-800) | `#78350F` (amber-900) | `#FCD34D` (amber-300) |
| Hard / blocked | `#FEE2E2` (red-100) | `#991B1B` (red-800) | `#7F1D1D` (red-900) | `#FCA5A5` (red-300) |
| Locked | `#F1F5F9` (slate-100) | `#475569` (slate-600) | `#1E293B` (slate-800) | `#94A3B8` (slate-400) |

---

## 4. Typography

Headings rounded and warm; body humanist and readable at long sessions.

- **Heading:** Fredoka (weights 400/500/600/700)
- **Body:** Nunito (weights 400/500/600/700)
- **Mono:** keep Geist Mono (already loaded) for code blocks in chat / hints.

### Type scale

| Token | Size / Line | Weight | Use |
|-------|-------------|--------|-----|
| `text-display` | 48 / 56 | Fredoka 600 | Marketing hero only (likely unused) |
| `text-h1` | 32 / 40 | Fredoka 600 | Page titles (topic name, question title) |
| `text-h2` | 24 / 32 | Fredoka 600 | Section heads |
| `text-h3` | 18 / 28 | Fredoka 500 | Card titles |
| `text-body` | 16 / 26 | Nunito 400 | Default body. **Minimum mobile body.** |
| `text-small` | 14 / 22 | Nunito 400 | Helper, meta |
| `text-caption` | 12 / 18 | Nunito 500 (uppercase, tracking-wide) | Labels above values, pills |
| `text-mono` | 14 / 22 | Geist Mono 400 | Code in chat, hints |

### Rules

- Body line-height 1.5-1.65 (we use 1.625 = `leading-relaxed`).
- Limit prose lines to 65-75ch (use `max-w-prose` on long blocks).
- Use Fredoka 600 for headings, **never** 700 except for the rare display.
  700 reads as kids-app shouty.
- Body text on light surfaces: `text-gray-800`, never anything lighter than
  `text-slate-600`.
- Code in body uses `font-mono text-[0.92em]` with `bg-indigo-50` /
  `dark:bg-indigo-950/40` inline highlight.

---

## 5. Effects, motion, elevation

| Token | Value | Use |
|-------|-------|-----|
| `--shadow-clay-sm` | `0 2px 6px -2px rgba(79,70,229,.10), 0 1px 2px -1px rgba(79,70,229,.06)` | Buttons, pills |
| `--shadow-clay` | `0 8px 24px -6px rgba(79,70,229,.18), 0 2px 6px -2px rgba(79,70,229,.12), inset 0 -2px 0 rgba(0,0,0,.04)` | Cards |
| `--shadow-clay-lg` | `0 16px 40px -10px rgba(79,70,229,.22), 0 4px 10px -3px rgba(79,70,229,.14), inset 0 -2px 0 rgba(0,0,0,.05)` | Modal, hovered roadmap nodes |
| `--shadow-focus` | `0 0 0 3px rgba(79,70,229,.35)` | Focus ring |

Motion:

- Micro-interactions: 150-200ms `ease-out`.
- Page/route transitions: 250ms.
- Easing: prefer `cubic-bezier(.2,.8,.2,1)` for press / lift.
- **Always** wrap any non-trivial motion in `@media (prefers-reduced-motion: no-preference)` or use the `motion-safe:` Tailwind variant.
- Layout-shifting transforms (`scale`, `width`, `height`) are banned for hover. Use `translate-y` and shadow.

---

## 6. Spacing, radii, layout

- Spacing scale: Tailwind default (4px base). No custom spacing tokens.
- Radii: 8 (`rounded-lg` - inputs), 12 (`rounded-xl` - buttons), 16 (`rounded-2xl` - cards), 9999 (pills).
- Container: `max-w-6xl` for marketing, `max-w-7xl` for app shells. Pick one per surface and stick with it.
- Z-index scale: `10` (sticky bars), `20` (dropdowns), `30` (drawers), `40` (toasts), `50` (modals). Don't invent new layers.
- Floating elements (toolbars, navbars) get edge spacing: `top-4 left-4 right-4`. Never glued to viewport edge.

---

## 7. Component primitives

Cheat sheet for the recurring elements. Use these classes verbatim where possible.

### Card (default)
```
rounded-2xl bg-white border border-indigo-100
shadow-[var(--shadow-clay)]
p-5 sm:p-6
transition-shadow duration-200
hover:shadow-[var(--shadow-clay-lg)]
dark:bg-[#161620] dark:border-indigo-900/40
```

### Card (interactive / clickable)
```
[card classes]
+ cursor-pointer
+ hover:-translate-y-0.5 active:translate-y-0
+ transition-[transform,box-shadow] duration-200
+ focus-visible:outline-none focus-visible:shadow-[var(--shadow-focus)]
```

### Primary button
```
inline-flex items-center justify-center gap-2
rounded-xl px-4 h-10
bg-indigo-600 text-white font-semibold
shadow-[var(--shadow-clay-sm)]
hover:bg-indigo-700 active:translate-y-px
disabled:opacity-50 disabled:cursor-not-allowed
focus-visible:outline-none focus-visible:shadow-[var(--shadow-focus)]
transition-[background,transform] duration-150
```

### CTA button (forward action - "Start session")
```
[primary button structure]
bg-green-500 hover:bg-green-600
```

### Difficulty pill
```
inline-flex items-center gap-1.5
rounded-full px-2.5 h-6
text-[12px] font-semibold tracking-wide
[difficulty-state colors from §3]
```

### Input
```
h-10 rounded-lg px-3
bg-white border border-zinc-200
text-gray-800 placeholder:text-slate-400
focus:outline-none focus:border-indigo-400 focus:shadow-[var(--shadow-focus)]
dark:bg-[#1E1B30] dark:border-indigo-900/40 dark:text-zinc-100
```

### Chat message bubble
- User: `bg-indigo-600 text-white rounded-2xl rounded-br-md` (ear bottom-right).
- Assistant: `bg-white border border-indigo-100 text-gray-800 rounded-2xl rounded-bl-md` (ear bottom-left).
- Both: `px-4 py-3 max-w-[42rem] shadow-[var(--shadow-clay-sm)]`.

---

## 8. Tailwind v4 wiring (for `app/globals.css`)

Drop-in replacement skeleton. **Do not** create a `tailwind.config.js`.

The pattern: light values on `:root`, dark overrides via `@media
(prefers-color-scheme: dark)`, then `@theme inline` aliases each `--var` as
`--color-*` / `--shadow-*` / `--font-*`. The `inline` keyword is the key bit:
it makes Tailwind utilities resolve `var(--color-*)` at runtime instead of
baking the value, which is what lets dark mode flip without a class toggle.

```css
@import "tailwindcss";

:root {
  /* Light values */
  --bg: #FAFAF9;
  --surface: #FFFFFF;
  --surface-muted: #F5F3FF;
  --line: #E4E4E7;
  --line-accent: #C7D2FE;

  --text: #312E81;
  --text-body: #1F2937;
  --text-muted: #475569;

  --primary: #4F46E5;
  --primary-hover: #4338CA;
  --secondary: #818CF8;
  --tint: #EEF2FF;

  --cta: #22C55E;
  --cta-hover: #16A34A;

  --ok: #16A34A;
  --warn: #F59E0B;
  --err: #DC2626;

  --shadow-clay-sm:
    0 2px 6px -2px rgba(79,70,229,.10),
    0 1px 2px -1px rgba(79,70,229,.06);
  --shadow-clay:
    0 8px 24px -6px rgba(79,70,229,.18),
    0 2px 6px -2px rgba(79,70,229,.12),
    inset 0 -2px 0 rgba(0,0,0,.04);
  --shadow-clay-lg:
    0 16px 40px -10px rgba(79,70,229,.22),
    0 4px 10px -3px rgba(79,70,229,.14),
    inset 0 -2px 0 rgba(0,0,0,.05);
  --shadow-focus: 0 0 0 3px rgba(79,70,229,.35);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0B0B0E;
    --surface: #161620;
    --surface-muted: #1E1B30;
    --line: #2A2A35;
    --line-accent: #3730A3;
    --text: #F4F4F5;
    --text-body: #E4E4E7;
    --text-muted: #A1A1AA;
    --primary: #A5B4FC;
    --primary-hover: #C7D2FE;
    --tint: #1E1B30;
    --cta: #4ADE80;
    --cta-hover: #22C55E;
    /* Shadows also flip to black-tinted on dark - see globals.css */
  }
}

@theme inline {
  --color-bg: var(--bg);
  --color-surface: var(--surface);
  --color-surface-muted: var(--surface-muted);
  --color-line: var(--line);
  --color-line-accent: var(--line-accent);
  --color-text: var(--text);
  --color-text-body: var(--text-body);
  --color-text-muted: var(--text-muted);
  --color-primary: var(--primary);
  --color-primary-hover: var(--primary-hover);
  --color-secondary: var(--secondary);
  --color-tint: var(--tint);
  --color-cta: var(--cta);
  --color-cta-hover: var(--cta-hover);
  --color-ok: var(--ok);
  --color-warn: var(--warn);
  --color-err: var(--err);

  --shadow-clay-sm: var(--shadow-clay-sm);
  --shadow-clay: var(--shadow-clay);
  --shadow-clay-lg: var(--shadow-clay-lg);
  --shadow-focus: var(--shadow-focus);

  --font-heading: var(--font-fredoka);
  --font-sans: var(--font-nunito);
  --font-mono: var(--font-geist-mono);
}

body {
  background: var(--bg);
  color: var(--text-body);
  font-family: var(--font-nunito), ui-sans-serif, system-ui, sans-serif;
}

h1, h2, h3, h4 {
  font-family: var(--font-fredoka), system-ui, sans-serif;
  color: var(--text);
}
```

**Resulting utility classes** (all generated automatically by Tailwind v4
from the `@theme inline` block - no config file needed):

- Colors: `bg-primary`, `text-primary`, `border-primary`, `bg-tint`,
  `text-text-muted`, `bg-surface`, `border-line-accent`, etc.
- Shadows: `shadow-clay-sm`, `shadow-clay`, `shadow-clay-lg`. (For
  `--shadow-focus`, use the arbitrary form: `shadow-[var(--shadow-focus)]`,
  since it's a focus-only effect, not a base shadow utility.)
- Fonts: `font-heading`, `font-sans`, `font-mono`.

### `app/layout.tsx` font wiring

Replace the existing Geist setup (keep Geist_Mono):

```tsx
import { Fredoka, Nunito, Geist_Mono } from "next/font/google";

const fredoka = Fredoka({
  variable: "--font-fredoka",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});
const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

// <html className={`${fredoka.variable} ${nunito.variable} ${geistMono.variable} ...`}>
```

---

## 9. Accessibility (non-negotiable)

These are CRITICAL and must hold across every page:

- **Contrast 4.5:1** minimum for body text. Verify both modes. Muted text floor is `slate-600` (light) / `zinc-400` (dark).
- **Focus ring** visible on all interactive elements (`focus-visible:shadow-[var(--shadow-focus)]`). Never `outline-none` without a replacement.
- **Touch targets 44x44px** minimum. Buttons height 40px + adequate padding gets you there; pills smaller than 44px need a parent hit area.
- **Keyboard nav**: tab order must match visual order. The roadmap DAG nodes must be focusable and Enter-activatable.
- **Form labels**: every input has a `<label htmlFor>`. Icon-only buttons need `aria-label`.
- **Reduced motion**: gate any non-essential motion behind `motion-safe:` or `@media (prefers-reduced-motion: no-preference)`.
- **Color is never the only signal**: pair difficulty color with the word ("Easy", "Medium", "Hard") or an icon.
- **Alt text** on meaningful images; `alt=""` on decorative ones.

---

## 10. Anti-patterns (do not do)

- Comic Neue, Comic Sans, anything that reads as a kids' app on the body.
- Emoji as primary UI icons. Use Lucide / Heroicons SVGs. Emoji is OK in
  coach chat copy where it's clearly content.
- Scale-on-hover (`hover:scale-105`) - causes layout shift; use translate.
- Glass / `bg-white/10` cards in light mode (invisible). Glass needs >= 70%
  opacity in light mode or skip it.
- Random max-widths per page. Pick `max-w-7xl` for the app and stick with it.
- Hard-coding hex values inline - read from the `--color-*` tokens.
- Adding `tailwind.config.js`. v4 is CSS-first; tokens belong in `@theme`.
- Toast over a modal over a dropdown layered without using the z-index scale.
- Confetti / heavy animation on every correct answer. Reserve big celebrations
  (mastered a topic, finished a streak) - daily microwins get a subtle pulse.

---

## 11. Pre-delivery checklist

Before opening a PR for any UI change:

- [ ] No emoji icons (SVGs from Lucide or Heroicons only).
- [ ] All clickable elements have `cursor-pointer` + visible hover state.
- [ ] Hover transitions 150-300ms; no layout-shifting transforms.
- [ ] Light + dark mode both verified at the actual contrast ratios.
- [ ] Focus ring visible via keyboard tab.
- [ ] `motion-safe:` guard on non-essential motion.
- [ ] Responsive verified at 375 / 768 / 1024 / 1440px.
- [ ] No horizontal scroll on mobile.
- [ ] Forms: labels present, errors near the field, button disabled while async.
- [ ] Reads tokens from `--color-*` / `--shadow-*`, not raw hex.

---

## 12. Page overrides

Per-page tweaks (e.g. `/practice/[id]` chat density rules, roadmap-specific
node styling) live in `design-system/pages/<page>.md` and override sections
of this Master file when present.

When implementing a page:

> I am building the [Page Name] page. Read `design-system/MASTER.md`. Also
> check if `design-system/pages/[page-name].md` exists. If the page file
> exists, prioritize its rules. If not, use the Master rules exclusively.
