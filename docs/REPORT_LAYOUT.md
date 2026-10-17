# Session report layout (PDF and on-screen preview)

The desktop app prints the session report as an A4 document. One function,
`paint_report` in `packages/desktop/ui/pdf.py`, draws the pages for both the
PDF file and the print preview on the Report tab, so the preview always
matches the PDF.

A report is written in Thai or in English. The therapist chooses the language
on the Report tab. A first draft uses the interface language, and a redraft
keeps the report's current language. Both languages have the same sections in
the same order, with the same rules: descriptive values only, no norms, every
cue shown with the therapist's decision, and the limitations stated in the
report (`apps/api/app/services/providers/thai_template_provider.py`).

## Filling in the report

The Report tab has two editing tabs on the left:

- **Fill in.** It has four fields:
  - the clinic name for the letterhead;
  - the therapist's interpretation;
  - therapy goals, one per line;
  - recommendations, one per line.

  Each field is one section of the report (`packages/desktop/ui/report_form.py`):
  - typing rewrites only that section;
  - the print preview redraws after a pause of about a third of a second, and turns to the page where that section is;
  - emptying a field restores the template's placeholder;
  - recommendations become a section, placed before the limitations, once something is written in them.
- **Whole report (Markdown).** The full text, for editing the template's own sections. The form reads it back whenever its tab is opened.

The measures, cues and limitations come from the session's data.

## Page settings

| | Thai report | English report |
|---|---|---|
| Paper | A4 portrait | A4 portrait |
| Font | TH SarabunPSK if the computer has it, otherwise the bundled TH Sarabun New (its successor from SIPA, same design and size) | Times New Roman; any Thai text in TH Sarabun at 1.3 times the size, so it sits with the Latin lower case |
| Title | 20 pt bold | 14 pt bold |
| Clinic name above the title | 18 pt bold | 12 pt bold |
| Body: text, headings, tables, limitations | 16 pt | 12 pt |
| Small print: header, footer, signature note | 14 pt | 10 pt |
| Margins (left, top, right, bottom) | 30, 25, 20, 20 mm | 25.4 mm (1 inch) on every side |
| Paragraphs | first line indented 1.25 cm, 6 pt after | block paragraphs, 6 pt after |
| List items | dash (–) at 1.25 cm (the paragraph indent), text at 1.8 cm | bullet (•) at 0.635 cm, text at 1.27 cm |
| Line spacing | 92% of the font's own spacing, about Word's single spacing for TH Sarabun | 115% |

Each report uses only these sizes, and a test checks that no other size appears. Column headings are centred. TH Sarabun has no arrow (→); that one character is drawn in Sarabun at 0.68 of the size, which prints at the same height. Headings are bold at body size, as in Thai official documents. Notes are set upright in the Thai report, because Thai fonts have no true italic.

Both languages share the same page furniture:

- **Page one: letterhead.** It is centred: the PasaScope logo (18 mm), then the clinic name (*Settings → Clinic name on reports*), then the report title. Page one has no running header.
- **Later pages: running header.** The clinic name, or the report title when no clinic name is set. On the right it reads "Confidential health information", or ข้อมูลสุขภาพส่วนบุคคล เก็บเป็นความลับ in Thai.
- **Footer on every page.** The child code, the session date, and "Page x of y" (หน้า x จาก y). On page one, the confidentiality line moves into the footer.
- **Background.** The PasaScope logo at 6% opacity, centred behind the text of every page. Shaded table cells are translucent, so the logo shows through them.
- **Sections.** Numbered. The session details and data sources are set out as two-column tables, and dates are written out in full: 2 ตุลาคม 2569 (Buddhist Era) or 2 October 2026.
- **Signature block.** It sits on the right half of the last page:
  - signature line, then the name in parentheses, then "Responsible therapist" (นักบำบัดผู้รับผิดชอบ), then the date;
  - a signed report adds "signed electronically in PasaScope", with the signing time in Thai time.
- **Draft stamp.** An unsigned report carries a boxed "ร่าง" ("DRAFT") stamp at the top centre of every page, where Thai draft documents are marked.
- **Page breaks.** A section heading never sits alone at the foot of a page, and the signature block is never split across pages.

## The logo

The source is the artwork the project owner supplied. `packages/desktop/ui/assets/logo.png` is a 1024 px copy of it:
- only the white background that touches the image's edge is made transparent, so the face inside the circle stays white;
- the image is cropped to the mark.

The logo is used in these places:
- the report letterhead and the report background;
- the sidebar of the app;
- the app icon. `scripts/build_macos_app.py` draws the mark on a white rounded square, as macOS icons are drawn, and writes `assets/icon.png`.

## Why these values

- **Thai body text and margins.** Thai official documents follow the Prime Minister's Office rules on official correspondence (ระเบียบสำนักนายกรัฐมนตรีว่าด้วยงานสารบรรณ). Agencies apply them as follows:
  - TH SarabunPSK or TH Sarabun New at 16 pt;
  - left margin 3 cm, right margin 2 cm;
  - first-line indent 2.5 cm.

  The report keeps the font, sizes and margins, but uses a 1.25 cm first-line indent (Word's default), because 2.5 cm pushed short paragraphs and lists too far into the page.

  Sources: the Uthai Thani provincial health office manual (https://uthaihealth.moph.go.th/uthaihealth/uploadfile/318.pdf); the PSU Pattani office document (https://office.pn.psu.ac.th/files/docs/doc_000216_2026-04-02); the PSU library template (https://library.psu.ac.th/wp-content/uploads/2025/04/TemplatePSULINET2025.pdf).
- **The font.** Thai official documents are set in TH SarabunPSK. The report uses it when the computer has it installed. Otherwise it uses TH Sarabun New, which the app bundles in `packages/desktop/ui/assets/fonts/` so that reports print the same on every computer.
  - TH Sarabun New is SIPA's later release of the same design.
  - Its licence is GPL v2 or later, with a font exception that lets documents embed it (`THSarabunNew-LICENSE.txt`, taken from the font's own licence field). I found no licence I could confirm for TH SarabunPSK itself, so it is not bundled.
- **Sarabun for the interface.** Google's Sarabun (SIL OFL 1.1, https://github.com/cadsondemak/Sarabun) stays bundled for the app's report editor and for the one character TH Sarabun lacks.
  - Its letters are drawn 1.47 times larger at the same point size. I measured both fonts: ก is 0.586 em tall in Sarabun and 0.400 em in TH Sarabun New.
- **English body text.** Formal English documents commonly use a 12 pt serif with 1-inch margins and page numbers on every page (Open Polytechnic formatting guide, https://www.openpolytechnic.ac.nz/formatting-and-presenting-assignments; APA guide, https://mylibrary.openpolytechnic.ac.nz/apa-style-psychology-assessments).
- **Report structure.** Speech-language evaluation reports are laid out in this order:
  1. identifying information;
  2. background and data sources;
  3. results;
  4. interpretation;
  5. goals or recommendations;
  6. limitations;
  7. a signed, dated attestation by the clinician.

  Sources: the UTEP SLP clinic documentation templates (https://www.utep.edu/chs/slp/_files/docs/september%202019%20update%20on%20campus%20documentation%20templates.pdf) and ASHA's documentation guidance (https://www.asha.org/Practice/reimbursement/Module-Three/).

## Qt details that matter

- **Units.** Qt's text layout reads margins, padding and borders as pixels at the platform's base resolution, which is 72 dpi on macOS and 96 dpi elsewhere, and scales them to the printer itself. A first-line indent is the exception: it is read in device pixels. `layout_base_dpi()` handles both cases, so the PDF looks the same on every platform.
- **Whole-sheet pages.** The document is paginated on whole A4 sheets, with the margins set on the root frame. A Thai line's upper vowels and tone marks then fall inside its own page's top margin and are never cut off by the page above.
- **Applying page breaks.** Qt lays text out lazily, and loses track of the layout when a format changes after a query. Page breaks are therefore found on one build of the document and applied to a fresh build.
- **Thai line breaks.** Qt on macOS breaks lines only at spaces. The renderer puts a zero-width space between Thai words (PyThaiNLP `newmm`) so that a line can break between any two words. This is the same method as the `thai-docx` skill uses for Word files, and text stays left-aligned for the same reason: justified Thai stretches the spaces.
- **Bullets.** Each list is a borderless two-column table, so that every line of an item, wrapped lines included, starts at the same place. Qt counts a table's left margin inside its fixed width.
