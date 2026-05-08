# Page Override: `/practice/[id]`

Per-page deviations from `design-system/MASTER.md`. Master rules apply unless
this file overrides them.

---

## 1. Surface model

The practice surface is a **column-flex chat shell** that fills the viewport,
with three fixed-height regions and one scrollable middle:

```
+------------------------------------------------+
| Top bar         (h-12, sticky, z-10)           |
+------------------------------------------------+
| QuestionPane    (auto, collapsible)            |
+------------------------------------------------+
|                                                |
| Message list    (flex-1, overflow-y-auto)      |
|                                                |
+------------------------------------------------+
| Composer        (auto, sticky bottom, z-10)    |
+------------------------------------------------+
```

- `min-h-screen flex flex-col` on the root.
- `flex-1 overflow-y-auto` on the message list - the only scrolling region.
- Composer and top bar do **not** scroll; QuestionPane scrolls only inside its
  collapsed/expanded body.

## 2. Density (deviation from Master)

This page is read- and type-heavy. Pull padding tighter than Master defaults
to keep more chat in view:

| Surface | Master | Practice |
|---------|--------|----------|
| Card padding | `p-5 sm:p-6` | `p-3 sm:p-4` |
| Message bubble vertical | n/a | `py-2.5` |
| QuestionPane vertical | n/a | `py-3` |
| Top bar height | n/a | `h-12` |
| Composer padding | n/a | `p-3` |

Generous spacing belongs on the roadmap. Here, clarity-per-pixel wins.

## 3. Top bar

Single horizontal strip, light surface, low chrome:

- Left: ghost back link `← Roadmap` - `text-sm text-text-muted hover:text-primary`.
- Right: ghost danger button `Leave session` - `text-sm`, `hover:text-err`,
  disabled when `busy || ended`.
- Border-bottom: `border-b border-line`. No drop shadow.

Do **not** make this a clay card - too much chrome competes with the
QuestionPane below it.

## 4. QuestionPane

Use Master card tokens but reduce padding (per §2). Keep the collapse toggle
on the right; it should be a true icon button (chevron) not text.

- Container: `bg-tint border-b border-line-accent` - tinted strip, not a
  floating card. (Override Master card style for this surface.)
- Difficulty pill: Master pill primitive, but always `easy`/`medium`/`hard`
  semantic (never the topic-status palette).
- Title: `font-heading text-base sm:text-lg font-semibold text-text`.
- Statement body (when expanded): `text-sm leading-relaxed text-text-body
  whitespace-pre-wrap max-w-prose`.
- Preserve the existing `data-difficulty="easy|medium|hard"` attribute on the
  outer container - tests rely on it.

## 5. Message list

- Vertical stack, no dividers between messages. Use bubble shape + alignment
  to separate, not borders.
- Role label removed from the rendered output - bubble side and styling
  carry that information. (Master cheat-sheet "user right / assistant left"
  applies.)
- Empty state: centered `text-text-muted text-sm` prompt, generous vertical
  whitespace (`py-12`).
- Tool-call pills (`ToolCallPill`) render **inside** the assistant bubble,
  not as standalone rows. Treat them as a quoted aside - `bg-tint
  border border-line-accent rounded-lg text-xs`.

## 6. Composer

- `border-t border-line bg-surface`.
- Textarea: Master input primitive but `rounded-xl` not `lg`, `min-h-12
  max-h-40`, autosize on input (browsers handle via `field-sizing: content`
  if available; fall back to `rows={2}`).
- Submit button: Master primary button at `h-10 px-4`, with arrow icon.
  Disabled when `busy || ended || !text.trim()`.
- Keyboard: Enter to send, Shift+Enter for newline (already wired).

## 7. Session-ended banner

When `ended === true`, render between the message list and the composer:

- `bg-green-50 border-t border-green-200 text-green-800 text-sm
  py-2 px-4 text-center`.
- Dark mode: `dark:bg-green-950 dark:border-green-900 dark:text-green-300`.
- Composer remains visible but disabled - don't yank it out, that causes a
  jarring layout shift.

## 8. Motion

- New assistant tokens stream in - **no** typing-cursor animation, **no**
  letter-by-letter fade. Streaming itself is the motion.
- New message appears: 150ms `ease-out` opacity 0 -> 1 only. No translate
  or scale - the chat is already noisy.
- Tool-call pill expanding (`<details>`): default browser disclosure, no
  custom animation (keeps reduced-motion users sane by default).

## 9. Empty / error states

- Session metadata still loading: render the shell (top bar + composer
  disabled), with a thin `animate-pulse` block where the QuestionPane will
  go. Do **not** show a blocking spinner - user can read the bar.
- Session 404 / fetch error: replace QuestionPane with an error strip:
  `bg-red-50 border-b border-red-200 text-red-700 text-sm px-4 py-3`.
  Composer is disabled.

## 10. Anti-patterns specific to this page

- No floating "scroll to bottom" button - browser handles it. Auto-scroll
  on new assistant tokens only if the user is already within ~80px of the
  bottom (don't yank them from re-reading earlier context).
- No celebratory confetti on tool calls. Reserve that for `record_outcome`
  with `unaided`, and only on the next page (the roadmap).
- No avatars next to bubbles. Distracting and invents a persona that
  doesn't fit a Socratic coach.
- Don't render the session id anywhere in the UI - it's a URL detail, not
  user-facing.
