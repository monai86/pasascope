# Thai Echolalia Cue Check

40 scripted adult/child turn pairs, labelled by hand as echo or not.

| | Flagged by the rule | Not flagged |
|---|---|---|
| Labelled echo | 20 | 0 |
| Labelled not echo | 4 | 16 |

Recall 100%, precision 83%.

## By kind of turn

| Kind | Labelled | Pairs | Flagged |
|---|---|---|---|
| verbatim | echo | 6 | 6 |
| particle_changed | echo | 4 | 4 |
| partial_end | echo | 6 | 6 |
| partial_short | echo | 4 | 4 |
| answer_new_words | not echo | 8 | 1 |
| answer_reuses_words | not echo | 8 | 3 |
| short_reply | not echo | 4 | 0 |

## Pairs the rule got wrong

| Pair | Kind | Adult | Child | Rule said |
|---|---|---|---|---|
| n04 | answer_new_words | วันนี้ใครมาส่ง | แม่มาส่ง | echo |
| n13 | answer_reuses_words | หนูอยากกินขนมไหม | อยากกินขนมครับ | echo |
| n14 | answer_reuses_words | เล่นรถไหมครับ | เล่นครับ | echo |
| n15 | answer_reuses_words | บินไปไหนครับ | บินไปบนต้นไม้ | echo |

## Reading these numbers

- The pairs were written for this check; they are not a sample of real sessions, so these rates do not estimate accuracy in practice.
- The rule sees one adult turn and the child's next turn. It cannot judge whether an echo is functional, and it does not detect delayed echolalia.
- Each flagged turn is shown to the therapist as a cue to confirm or dismiss.
