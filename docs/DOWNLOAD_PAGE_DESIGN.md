# Download page design (site/)

The GitHub Pages download page shows a recording turning into a counted transcript.

- **World:** a measuring graticule on an ice-blue ground (`--ground #f3f7fd`, 24 px minor and 120 px major grid lines in azure at 5–10 % alpha). Navy ink (`--ink #0b1630`), electric azure for action and signal (`--azure #1c4fff`, `--azure-deep #1238d4`), one red only for "to check" (`--flag #e5484d`). A navy band (`--night`) for the readout and the privacy section.
- **Type:** Prompt for display, Noto Sans Thai for text, JetBrains Mono only for data: CHAT codes, times, counts and measure values. All self-hosted (fonts/).
- **Signature motion (the only one):** the hero panel draws a synthetic waveform on canvas; a playhead crosses it at about 2× speed, each turn's line lights up, child lines get their words underlined and their count, and the readout counts up to the page's written totals (4 utterances, 14 words, MLU-w 3.50, NDW 12, 3 echo cues). With reduced motion or no script the panel shows the finished state.
- **Version:** written into the HTML (`data-release-version`, `data-release-date`) and replaced at load from the GitHub releases API, so a release needs no edit but a stale or blocked API call still shows a current number. Update the written fallback when a release ships.
- **Language:** Thai by default; `?lang=en` or the toggle switches, and the choice is remembered.
- **Rules kept:** no eyebrow labels, no card grid as structure, no gradient text, no glow; focus, selection, caret and scrollbars themed; body contrast ≥ 4.5:1.
