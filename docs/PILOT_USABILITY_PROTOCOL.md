# Pilot Usability Protocol (desktop app)

A short session to see whether therapists can use PasaScope on their own, and how long each step takes. It is ready to run once therapists are available; nothing here involves a real child.

## Who and what

- **Participants**: 3–5 speech-language therapists. Five participants find most usability problems (Nielsen & Landauer, 1993).
- **Data**: the demonstration data only (`scripts/seed_desktop_demo.py`, scripted dialogues and synthetic speech). No real recordings or children's details.
- **Setup**: a Mac with the current release installed and the speech models already downloaded. Start each participant with a fresh demo folder (`./run_gui.sh --demo` after `seed_desktop_demo.py --reset`, on a copy).
- **Time**: about 45 minutes per participant.
- **Consent**: participants agree to take part and to have their screen and comments noted. Check whether your institution needs ethics review for staff usability testing.

## Tasks

Read each task aloud and then stay quiet. Note the time, whether it was completed without help, and where the participant hesitated.

| # | Task | Done when | Time limit |
|---|---|---|---|
| 1 | Set your own name as the therapist | Name shows in the sidebar | 2 min |
| 2 | Add a case: code TEST-01, age 4 years 0 months; record the caregiver's consent | Case shows "Consent given" | 4 min |
| 3 | Create a session for today and import [`pilot/demo_transcript.cha`](./pilot/demo_transcript.cha) | Transcript tab lists the lines | 4 min |
| 4 | Two lines have the wrong speaker: find and correct them, then attest the transcript | Status "Attested" | 6 min |
| 5 | Run the analysis and find the child's MLU-w and NDW | Participant says both values | 3 min |
| 6 | Open the explanation of NDW-100 | Guide entry shown | 2 min |
| 7 | Review the cues: confirm one, dismiss one with a note | No open cues | 4 min |
| 8 | Write a one-line interpretation and one goal, sign the report and export a PDF | PDF saved | 6 min |
| 9 | Back up the data to the Desktop | Backup file exists | 2 min |

Facilitator only: the wrong speakers are line 4 ("ไปบ้านคุณยาย", should be the child) and line 7 ("ไปถึงแล้วจะทำอะไร", should be the adult).

## Measures

- **Completion**: tasks completed without help (count per task and per participant).
- **Time on task**: seconds per task (median across participants).
- **Errors and help requests**: what happened, at which step.
- **System Usability Scale (SUS)** after the tasks (Brooke, 1996), scored 0–100; 68 is the commonly cited average (Sauro, 2011). Use the standard English wording below, or a published Thai translation if participants prefer Thai.
- **Three open questions**: What was hardest? What would you change first? Would you use this in your work, and for what?

### SUS items (1 = strongly disagree … 5 = strongly agree)

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

Score: for odd items subtract 1 from the answer; for even items subtract the answer from 5; add the ten results and multiply by 2.5.

## Recording results

One row per participant and task in a spreadsheet: participant code (P1…P5), task, completed (yes / with help / no), seconds, notes. One row per participant for SUS and the open answers. Report medians and ranges; with five participants, do not report statistical tests.

## References

- Brooke, J. (1996). SUS: A "quick and dirty" usability scale. In *Usability Evaluation in Industry*. Taylor & Francis.
- Nielsen, J., & Landauer, T. K. (1993). A mathematical model of the finding of usability problems. *Proceedings of INTERCHI '93*, 206–213.
- Sauro, J. (2011). *A Practical Guide to the System Usability Scale*. Measuring Usability LLC.
