# Answer typed questions on the chat home from a fixed list of topics

The chat home now answers what a therapist types, which ADR 0021 ruled out when
it said that no command is ever inferred from typed text. A typed line is
normalised and matched against fixed lists of Thai and English terms, one list
per topic, with a second attempt that reads the same keystrokes on the other
keyboard layout; each topic has one prepared answer, some of them filled from
the caller's own sessions and cases, and a line that matches nothing is
answered as not understood, with questions that can be asked. There is still no
language model, and the answers say so. The rule that replaces the old one is
narrower, not gone: a typed line may be answered, open a page or begin the
guided start, but it never changes a record. Creating a case, confirming
consent, sending audio and every other write still needs its own button, so a
misread line can at worst show the wrong answer. A line that is exactly a
case's name or code is that case before any topic is considered, and a line
that names part of one is a case search when no topic matches. The exchange
lives on the screen only: it is not stored, sent to the API or logged, because a
typed line may contain a child's name. Typed text inside a session is unchanged
and is still saved as a session note. The term lists are covered by a table of
phrases per topic in the unit tests, which is where a missed phrasing is added.
