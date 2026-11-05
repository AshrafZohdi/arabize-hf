# Darby design tokens

Light mode only for the hackathon. Put these in one place (`web/src/styles/tokens.css` as CSS variables, mapped into Tailwind's theme) and never write a hex in a component.

## Colour

| Token | Hex | Use |
|---|---|---|
| bg | #F5EBDD | page, cream sand |
| surface | #FFFDF9 | cards, header |
| surface-2 | #FBF6EE | text wells inside cards |
| surface-3 | #F7F0E6 | analogy box, done path rows |
| line | #E8D9C3 | borders |
| shadow | #E2CFB3 | chunky card shadow `0 6px 0` |
| ink | #22181A | main text |
| ink-2 | #4A3D38 | secondary text |
| muted | #6A5D55 | captions (passes 4.5:1 on bg) |
| maroon | #8A1538 | brand, primary buttons, current step, new terms |
| maroon-deep | #5E0E26 | primary button shadow, hover |
| maroon-soft | #F6E1E6 | new-term chip ground |
| maroon-text | #7A1231 | text on maroon-soft |
| teal | #0B6E69 | known terms, listen button |
| teal-soft | #DDEFEC | known-term chip ground |
| teal-text | #0A5A56 | text on teal-soft |
| gold | #E9A93B | points icon |
| gold-soft | #FBE7BF | points chips, review banner |
| gold-text | #6B4300 | text on gold-soft |
| flame | #D9622B | streak icon |
| success | #1F7A4D | correct answer, done node, letter in place |
| success-soft | #E2F3E9 | correct answer ground |
| success-text | #145236 | text on success-soft |
| present | #C98A1A | daily code: letter elsewhere |
| absent | #CFC3B4 | daily code: letter not in word |
| locked | #EADCC8 | locked path node |

## Type

- Display and headings: Readex Pro 500/600, bundled as woff2 files in the app (no Google Fonts link at run time; same for IBM Plex Sans Arabic and IBM Plex Sans, all under the SIL Open Font License). Soft and rounded on purpose: the earlier Reem Kufi was rejected as too strong. Do not use heavy or calligraphic Kufi faces.
- Arabic body and UI: IBM Plex Sans Arabic 400 to 700.
- English passages, terms and answer options: IBM Plex Sans 500 to 700.
- Sizes: h1 36 (28 on phone), section titles 22, term title 26, body 16 to 18, captions 13 to 14. Line height 1.7 for Arabic.

## Shape and space

- Page: max width 1240, padding-inline 40 (16 on phone), top padding 40.
- Home layout: main column (Smart Explain input, then the result card with the term and the quick question side by side) `flex: 999 1 600px`, and a side column `flex: 1 1 340px` with the daily code, the path and the review banner. In RTL the main column sits on the right. On a phone the side column stacks below.
- Title block to content: 32. Column gap and stacked card gap: 28 (20 on phone).
- Card: radius 20, padding 28 (20 on phone), 1px line border, `box-shadow: 0 6px 0 shadow`.
- Inner wells and buttons: radius 14 to 16. Chips and nav: pill (999).
- Primary button: maroon, white text, `box-shadow: 0 5px 0 maroon-deep`, min height 56; on press translateY(3px) and shadow 2px.
- Answer buttons: white, 2px line border, `0 4px 0 shadow`; correct state success colours with a check icon and the word.
- Icons: stroke icons (lucide-react is fine), 2 to 2.2 stroke, never emoji.
