# Design — Project Identity

> This document is project-long-lived. Tokens are not changed without
> the Architect's approval. Developers MUST use these tokens
> instead of improvising their own colors/spacings.

## Style Direction

Calm, tool-like light UI in the spirit of Linear/Stripe: neutral cool-grey surfaces, one indigo accent, Inter for the interface and JetBrains Mono for ids, results and timestamps; status is readable at a glance through color-coded badges with text labels.

## Colors

- `--color-bg`: **#F6F7F9**
- `--color-surface`: **#FFFFFF**
- `--color-fg`: **#14171F**
- `--color-muted`: **#5B6475**
- `--color-accent`: **#4F46E5**
- `--color-accent_hover`: **#4338CA**
- `--color-accent_active`: **#3730A3**
- `--color-accent_soft`: **#EEF0FF**
- `--color-border`: **#E1E4EA**
- `--color-border_strong`: **#C6CBD6**
- `--color-focus_ring`: **#4F46E5**
- `--color-status_pending_bg`: **#F1F2F5**
- `--color-status_pending_fg`: **#4A5263**
- `--color-status_running_bg`: **#E3EEFF**
- `--color-status_running_fg`: **#1747B8**
- `--color-status_done_bg`: **#DFF5E8**
- `--color-status_done_fg`: **#136B3A**
- `--color-status_failed_bg`: **#FDE7E7**
- `--color-status_failed_fg`: **#A11D1D**
- `--color-error_bg`: **#FDF0F0**
- `--color-error_border`: **#F2B8B8**
- `--color-error_fg`: **#A11D1D**
- `--color-code_bg`: **#F3F4F8**

## Typography

- `font_family`: "Inter", system-ui, "Segoe UI", Roboto, Arial, sans-serif
- `heading_font`: "Inter", system-ui, "Segoe UI", Roboto, Arial, sans-serif
- `mono_font`: "JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, "Liberation Mono", monospace
- `heading_weight`: 600
- `body_weight`: 400
- `size_scale`: xs 12px, sm 14px, base 16px, lg 18px, xl 22px, 2xl 28px; line-height 1.5 body, 1.25 headings; fonts loaded locally via design/fonts/inter/font.css and design/fonts/jetbrains-mono/font.css, no external font URLs
- Inter files: `design/fonts/inter/` — `font.css` holds its @font-face rules, `OFL.txt` its licence
- JetBrains Mono files: `design/fonts/jetbrains-mono/` — `font.css` holds its @font-face rules, `OFL.txt` its licence

## Spacing Scale

- `--space-0`: 4px
- `--space-1`: 8px
- `--space-2`: 12px
- `--space-3`: 16px
- `--space-4`: 24px
- `--space-5`: 32px
- `--space-6`: 48px

## Border-Radii

- `--radius-sm`: 4px
- `--radius-md`: 8px
- `--radius-lg`: 12px
- `--radius-pill`: 999px

## Components

### Button

Primary: bg=accent, fg=#FFFFFF, font 14px/600, padding 12px 24px, radius md, min-height 44px. Hover=accent_hover; active=accent_active plus 1px translateY; focus-visible: 2px focus_ring outline with 2px offset; disabled: opacity 0.5, cursor not-allowed, no hover change (also used while the text is empty or while submitting). Loading state shows the label 'Wird gesendet…' and stays disabled. Full width on mobile, auto width from 640px.

### Textarea

Field for the job text. bg=surface, 1px border, radius md, padding 12px, min-height 160px, vertical resize only, font Inter 15px. Hover: border_strong; focus: border=accent plus 3px accent_soft ring. Error state: border=error_fg with an error message below (12-14px, error_fg, role=alert). A character counter 'n / 100.000' at the bottom right in muted mono 12px turns error_fg above the limit. The error is shown only after typing or a submit attempt, never on the untouched form.

### Select

Dropdown for the analysis, same height (44px), border, radius and focus as Input. Native <select> with a custom chevron. Options exactly: 'Wörter zählen', 'Häufigste Wörter', 'Lesezeit schätzen'. Label above in 14px/500.

### FormField

Label (14px/500, fg) + control + hint or error line (13px, muted or error_fg). Vertical gap 8px, between fields 16px.

### Card

bg=surface, 1px border, radius lg, padding 24px (16px on mobile), subtle shadow 0 1px 2px rgba(20,23,31,0.04). Used for the job form and the job list container. Heading inside at 18px/600.

### StatusBadge

Pill (radius pill), padding 4px 10px, font 12px/600, with a 6px dot before the label. Always text, never color only. Labels and colors: pending 'wartend' (status_pending_bg/fg, grey dot), running 'in Arbeit' (status_running_bg/fg, dot pulses 1.2s, disabled under prefers-reduced-motion), done 'fertig' (status_done_bg/fg), failed 'fehlgeschlagen' (status_failed_bg/fg). data-status attribute carries the raw status.

### AnalysisChip

Small neutral tag showing the analysis in German: 'Wörter zählen', 'Häufigste Wörter', 'Lesezeit schätzen'. bg=code_bg, fg=muted, 12px/500, padding 2px 8px, radius sm. An unknown analysis value is shown as the raw value.

### JobItem

One job row inside the list card, separated by a 1px border, padding 16px 0. Top row: mono id '#42' (muted, 13px), AnalysisChip, StatusBadge pushed to the right, timestamp below on mobile. Second row: text preview, max 120 characters then '…', 2 lines clamp, 15px fg, rendered as a plain React text node only. Third row: ResultBlock. Newest job first. Job text, result and error are never injected as HTML.

### ResultBlock

Only for done and failed jobs, on a code_bg panel, radius md, padding 8px 12px, mono 13px. done: word_count -> '3 Wörter'; top_words -> a row of chips 'wort × 4' (alphabetical on ties as delivered); reading_time -> '2 Min. Lesezeit'; unknown result shape -> raw text. failed: error_bg panel with error_border, error_fg text, prefix 'Fehler:' followed by the message. pending/running: muted text 'Ergebnis folgt …'.

### ErrorNotice

Banner above the list. bg=error_bg, 1px error_border, fg=error_fg, radius md, padding 12px 16px, leading icon, role=alert. Text: 'Die API ist nicht erreichbar. Neuer Versuch in wenigen Sekunden.' The previously loaded list stays visible below it. Disappears automatically after the next successful poll. Form submit errors use the same style inline above the submit button, with the server message shown in German (e.g. 'Der Text darf nicht leer sein.').

### EmptyState

Centered inside the list card, padding 48px 24px: simple 40px line icon in muted, title 'Noch keine Aufträge' (16px/600), hint 'Erstelle links deinen ersten Auftrag, das Ergebnis erscheint hier automatisch.' (muted).

### LiveIndicator

Small text in the list header: 6px green dot plus 'Aktualisiert automatisch alle 3 s' (12px muted). During an error the dot turns error_fg and the text reads 'Verbindung unterbrochen'. Informational only, not interactive.

### SkeletonRow

Loading placeholder for JobItem: three grey bars (code_bg, radius sm) with a soft shimmer; the shimmer is off under prefers-reduced-motion. Shown only during the first load.

## Layout Principles

- Container max-width 1120px, centered, horizontal padding 16px (mobile) / 24px (from 640px) / 32px (from 1024px); page bg=bg.
- Breakpoints: 640px (tablet), 1024px (desktop). Single column below 1024px: form card first, job list below. From 1024px two columns: form card 380px fixed and sticky (top 24px), list card fills the rest, gap 24px.
- Vertical rhythm: 24px between cards, 16px inside forms, 32px between header and content. Spacing only from the scale 4/8/12/16/24/32/48.
- Every interactive element has min-height 44px and a visible focus ring (2px accent outline, 2px offset). Color contrast at least WCAG AA; status is always conveyed with text, not only color.
- Format of dates and times everywhere: 'TT.MM.JJJJ, HH:mm:ss' in 24h in the user's local time, e.g. '27.05.2025, 14:03:09', set in mono 12px muted. Job ids as '#<integer>'. Numbers in the German locale (thousands separator '.', e.g. '100.000'). Durations as '<n> Min.'; counts as '<n> Wörter'.
- All UI text is German; all job content (text, result, error) is rendered only as React text nodes, with white-space: pre-wrap and overflow-wrap: anywhere so that long text never breaks the layout.
- Only locally served assets: fonts via the bundled font.css files (font-display: swap), icons as inline SVG; no CDN, no external URLs.
- Motion is minimal (120-150ms color/shadow transitions, the running dot pulse) and switched off under prefers-reduced-motion.

## Screens

### Home (/)

Layout: Header on top; from 1024px form card (380px, sticky) left + job list card right; below 1024px a single column with the form first and the list below, all full width.

- Header: product title 'Textanalyse-Aufträge' (22px/600) with a short subtitle 'Aufträge anlegen, der Worker verarbeitet sie im Hintergrund.' and the LiveIndicator on the right (wraps below the title on mobile).
- Job form card: heading 'Neuer Auftrag', Textarea 'Text' with placeholder 'Text zur Analyse einfügen …' and character counter, Select 'Analyse', primary Button 'Auftrag erstellen' (disabled while the text is empty or while submitting), inline ErrorNotice for server errors. After success the textarea is cleared, the list refreshes immediately, and the form shows no error.
- Error notice: ErrorNotice banner above the list when the API is unreachable; the last known list stays visible.
- Job list card: header 'Aufträge' with a count badge (e.g. '12') and the newest-first order; below it JobItem rows (id, text preview, AnalysisChip, StatusBadge, timestamp, ResultBlock). Refreshes every 3 seconds without a flash or scroll jump; polling stops on unmount.

States: Loading: three SkeletonRows in the list card on the first load only (no flicker on later polls). Empty: EmptyState 'Noch keine Aufträge' with the hint to create a job. Error: ErrorNotice 'Die API ist nicht erreichbar …' above the list (last known list stays visible); a failed submit shows the server message inline above the button; failed jobs show 'Fehler: <message>' in their ResultBlock.
