---
version: "superdesign-alpha"
name: "Ledger Violet Grid"
description: "Light neutral-gray system built for dense repeated-card inventories, with a single violet brand accent rationed to CTAs and one nav highlight, mint status pills, and near-invisible 12px-radius white cards on a paper-gray field."
colors:
  background: "#F9FAFB"
  surface: "#FFFFFF"
  text-primary: "#111827"
  text-secondary: "#6B7280"
  accent: "#8F17D7"
  accent-hover: "#7E22CE"
  info-bg: "#EFF6FF"
  info-border: "#BFDBFE"
  success-bg: "#DCFCE7"
  success-text: "#166534"
  border-default: "#E5E7EB"
  disabled-fill: "#D1D5DB"
  disabled-text: "#6B7280"
typography:
  display-lg:
    fontFamily: "-apple-system"
    fontSize: "30px"
    fontWeight: 700
    lineHeight: "1.2"
  headline-md:
    fontFamily: "-apple-system"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: "1.4"
  body-md:
    fontFamily: "-apple-system"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "1.43"
  label-md:
    fontFamily: "-apple-system"
    fontSize: "16px"
    fontWeight: 500
    lineHeight: "1.5"
  accent-label:
    fontFamily: "-apple-system"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: "1.3"
spacing:
  base: "4px"
  gap: "24px"
  section-padding: "32px"
rounded:
  control: "8px"
  card: "12px"
  pill: "9999px"
components:
  button-primary-nav:
    background: "#8F17D7"
    text-color: "#FFFFFF"
    radius: "8px"
    height: "36px"
    padding: "8px 16px"
    hover-background: "#7E22CE"
    shadow: "rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.1) 0px 4px 6px -1px, rgba(0, 0, 0, 0.1) 0px 2px 4px -2px"
  button-secondary-nav:
    background: "transparent"
    text-color: "#4B5563"
    radius: "8px"
    height: "36px"
    padding: "8px 16px"
  button-disabled-card:
    background: "#D1D5DB"
    text-color: "#6B7280"
    radius: "8px"
    height: "48px"
    padding: "12px 16px"
  card-practice-test:
    background: "#FFFFFF"
    radius: "12px"
    padding: "24px"
    shadow: "rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.05) 0px 1px 2px 0px"
  banner-info:
    background: "#EFF6FF"
    border: "1px solid #BFDBFE"
    radius: "12px"
    text-color: "#111827"
  badge-status:
    background: "#DCFCE7"
    text-color: "#166534"
    radius: "9999px"
---
# Ledger Violet Grid
Source: https://the1550formula.com/

## Overview
This is a light, neutral-first utility system — closer to Swiss/functional than any decorative aesthetic — built to hold a large repeating inventory of identical cards. The palette is almost entirely grayscale (#F9FAFB field, #FFFFFF surfaces, #6B7280/#111827 text) with a single violet brand hue (#8F17D7) rationed to exactly two places: the active nav pill and every primary CTA. Mint-green status pills (#DCFCE7/#166534) supply the only other saturated color. There is no illustration, no gradient background, no photography — the entire visual interest is typographic hierarchy, card repetition, and one disciplined accent color.

## Composition
The page opens with an edge-to-edge white navbar, then a full-width pale-blue informational banner, then a centered headline block, then a small eyebrow-labeled row header, then a dense uniform grid of practice-test cards that continues, unbroken, for the entire remaining length of the page — 19 cards deep with no interstitial section breaks, no imagery, no testimonials, no footer variety visible. The deliberate choice here is repetition-as-content: rather than varying card size or introducing a bento/masonry rhythm, every card is identical in size, radius, and internal layout, rejecting an editorial or asymmetric layout in favor of scannable, catalog-like uniformity. This works because the content is inherently serial (numbered items in a list); a design that introduced varied spans would fight the content's own structure.

## Colors
`#F9FAFB` is the true page background (61%+ pixel share as the grid's gutter/paper color), with `#FFFFFF` (24–27% share) carrying every card and the navbar itself. `#D1D5DB` gray (9% share) is the disabled/locked-state button fill used across all 19 CTAs, paired with `#6B7280` text — this is a deliberately desaturated, "not-yet-available" visual signal rather than a true primary action. The violet `#8F17D7` (0.2% share) is tightly rationed to the nav's active tab and Sign Up button, appearing nowhere else — it never bleeds into cards or badges. Mint `#DCFCE7`/`#166534` marks availability status on every card, and pale blue `#EFF6FF`/`#BFDBFE` frames the single login-required banner. Borders are hairline `#E5E7EB`. Nothing else is colored — headings, body copy, icons, and card chrome stay strictly grayscale, keeping the violet and mint legible as pure signal.

## Typography
A single system-UI stack (`-apple-system`) carries every role — no serif or mono accent appears anywhere in this system. Hierarchy is built purely through size and weight: a 30px/700 display headline anchors the page center, a 20px/600 headline-md marks card titles, 16px/500 label-md marks the small section eyebrow, and 14px/400 body-md (color `#6B7280`) carries all metadata (duration, question count) and descriptive copy, with `#111827` reserved for higher-emphasis inline text. Line-heights stay tight (1.2) on the display size and open up (1.43–1.5) for body and label text, standard for a dense-UI, non-editorial reading mode.

## Layout
The grid is a fixed 3-column card grid at 24px gap, content capped at a 1280px max-width and centered. Every row is uniform — no spanning cards — giving row composition of [3][3][3][3][3][3][1] across 19 items (the final row holds a single trailing card). This is a pure uniform card grid, not bento or masonry: card widths never vary, only row count grows. Card internal padding is 24px; radii are 12px on cards and 8px on all buttons/controls. Spacing follows a tight 4/8/12/16/24/32px rhythm, visible in the gap between card title and metadata row (~12px) and between metadata and button (~16px).

## Components
- **Navbar** — edge-to-edge, square-cornered bar (0px radius all four corners), 65px tall, full 100% viewport width with 0px inset on either side, background `#FFFFFF`, static/non-transparent. Contains 6 items: a small violet square logo mark, a filled violet "active" nav pill, two plain-text nav links, a plain-text Login link, and a filled violet Sign Up button. Nav CTA (Sign Up): `#8F17D7` fill, `#FFFFFF` text, 8px radius, 36px height, 8px 16px padding, shadow `rgba(0,0,0,0) 0px 0px 0px 0px, rgba(0,0,0,0) 0px 0px 0px 0px, rgba(0,0,0,0.1) 0px 4px 6px -1px, rgba(0,0,0,0.1) 0px 2px 4px -2px`.
- **Button — nav primary/active pill**: `#8F17D7` fill, white text, 8px radius (slightly-rounded), 36–40px height, 8px 16px padding; hover darkens to `#7E22CE`. Appears once, as the active state in the primary nav cluster.
- **Button — nav secondary (Login)**: transparent fill, `#4B5563` text, 8px radius, 36px height, 8px 16px padding. Appears ×2 in the navbar as plain-text utility links.
- **Button — disabled/locked CTA**: `#D1D5DB` fill, `#6B7280` text, 8px radius (slightly-rounded), 48px height, 12px 16px padding, a small play-triangle icon plus label. Appears ×19, one per practice-test card, full card width. No hover elevation observed — this is a locked/gated state, not the hero primary.
- **Banner — info/login-required**: full content-width band, `#EFF6FF` background, `#BFDBFE` border, 12px radius, small person-outline icon at left, two-line stacked text (bold lead-in + secondary sentence). Appears once, directly beneath the navbar.
- **Card — practice-test**: `#FFFFFF` fill, 12px radius, 24px padding, shadow `rgba(0,0,0,0) 0px 0px 0px 0px, rgba(0,0,0,0) 0px 0px 0px 0px, rgba(0,0,0,0.05) 0px 1px 2px 0px`. ×19, arranged 3-per-row across 7 rows (last row: 1 card). Anatomy top-to-bottom: bold headline-md title + mint status badge on the same row (right-aligned); a metadata row below with a clock icon + duration and a question-count figure in body-md/`#6B7280`; a full-width disabled CTA button at the bottom. No imagery, no chips beyond the single status badge.
- **Badge — status pill**: `#DCFCE7` fill, `#166534` text, full pill radius (9999px), compact padding, small-caps-weight label. One per card, top-right corner.
- **Section eyebrow row**: a small violet triangular/play-shaped icon paired with a bold label-md heading, left-aligned above the grid — marks the grid's section start without a full banner treatment.

## Graphics & Effects
No gradients, no mesh backgrounds, no photographic or illustrated imagery, no glassmorphism or blur anywhere in this system — the entire surface language is flat fills plus two shadow tokens. Card shadow is a barely-visible single-layer `rgba(0,0,0,0.05) 0px 1px 2px 0px`, giving cards only the faintest lift off the `#F9FAFB` field. The nav CTA carries a slightly stronger two-layer shadow (`rgba(0,0,0,0.1) 0px 4px 6px -1px, rgba(0,0,0,0.1) 0px 2px 4px -2px`) to raise it above the flat navbar. No texture, grain, or pattern overlay is visible anywhere; the background reads as pure flat paper-gray.

## Motion
Interactive color changes (text, background, border, fill, stroke) transition at `0.2s cubic-bezier(0.4, 0, 0.2, 1)`, with a faster `0.15s` variant on lighter-weight controls; box-shadow changes share the same `0.2s cubic-bezier(0.4, 0, 0.2, 1)` curve — this governs hover state changes on the nav CTA. No scroll-triggered or stagger animation is evident across the repeated card grid; cards render statically. A `dcg-fadeAndScaleIn` keyframe and a set of `slow_plotting_icon` keyframes exist in the codebase for entrance/icon animation but are not visibly active in these static states — treat them as subtle, low-emphasis entrance polish rather than a defining motion signature.

## Guardrails
- Never introduce a gradient or mesh background — this system is flat-fill only.
- Never apply the violet accent to more than the nav active pill and primary CTAs; it must not appear on cards, badges, or body text.
- Never vary card width or add spanning cards to the practice-grid — uniform 3-column repetition is the pattern, not bento.
- Never round the navbar corners — it is a square, edge-to-edge, full-width bar with 0px radius on all corners.
- Never brighten the disabled card-CTA into the violet brand color — its grayed `#D1D5DB`/`#6B7280` fill is a deliberate locked-state signal, not a primary button.
- Never add heavy shadows or elevation beyond the two documented tokens — the whole system stays visually flat and quiet.