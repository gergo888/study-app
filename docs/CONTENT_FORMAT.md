# Content format (Markdown)

All learning content lives in Markdown files under `content/`. They are the **source of truth**:
the app reads and writes them, and Claude Code edits them directly. Learning state (progress,
spaced-repetition schedule, XP) is stored separately in `data/*.csv` and attached to the content
through **stable ids** written as `{#id}`.

```
content/<material-slug>/<chapter-key>/
├── summary.md       sections → bullet points (EN + HU), key concepts, figures
├── flashcards.md    ≥ 1 flashcard per bullet point
├── quiz.md          ≥ 1 quiz question per bullet point (4 options, exactly 1 correct)
├── notes.md         free-form chapter notes (written in the app)
├── figures/         images referenced by the three files above
└── _source/         (gitignored) extracted text + candidate figures for Claude Code
content/<material-slug>/notes/*.md    material-level notes
```

Ids (`{#usb-2}`, `## usb-2`) must match `[a-z0-9][a-z0-9-]*` and be unique within the chapter.
**Never rename an id** of existing content without reason: renaming detaches its progress and
review history (the old state is archived, not deleted).

Every file starts with YAML front matter:

```yaml
---
material: comptia-a-plus
chapter: 1A
title: Explain Cable Types and Connectors      # summary.md only
title_hu: Kábeltípusok és csatlakozók           # summary.md only (optional)
---
```

## summary.md

```markdown
# Explain Cable Types and Connectors

## Universal Serial Bus Cables {#usb}
hu: USB-kábelek

- **USB 2.0 HighSpeed** {#usb-2}
  - hu-title: USB 2.0 HighSpeed
  - en: USB 2.0 HighSpeed has a nominal data rate of **480 Mbps**; cables can be up to **5 m** long.
  - hu: Az USB 2.0 HighSpeed névleges adatátviteli sebessége **480 Mbps**; a kábel legfeljebb **5 m** lehet.
  - concepts: 480 Mbps | 480 Mb/s ; 5 m | 5 méter | 5 meters
  - figure: ![USB 2 ports and connectors | USB 2 portok és csatlakozók](figures/p0052-x1071.jpg)
```

| Line | Meaning |
|---|---|
| `# Title` | Optional H1, ignored by the parser (the title comes from the front matter). |
| `## Heading {#id}` | Section (English heading). |
| `hu: …` | Hungarian section heading — the line directly below the section heading. |
| `- **Title** {#id}` | Bullet point. The **bold title is what stays visible in memorize mode.** |
| `  - hu-title:` | Hungarian bullet title. |
| `  - en:` / `  - hu:` | The text that is **hidden in memorize mode**. Inline Markdown allowed. Continue on lines indented by 4 spaces (nested lists allowed). |
| `  - concepts:` | Key concepts used to check written answers. Concepts are separated by `;`, alternative wordings (English *and* Hungarian, abbreviations, units) by `\|`. 2–5 concepts per point. |
| `  - figure:` | Optional. `![EN caption \| HU caption](figures/<file>)`. |

## flashcards.md

```markdown
## usb-2
- front-en: What is the nominal data rate of USB 2.0 HighSpeed?
- front-hu: Mekkora az USB 2.0 HighSpeed névleges adatátviteli sebessége?
- back-en: 480 Mbps (max. cable length 5 m)
- back-hu: 480 Mbps (max. 5 m kábelhossz)

## usb-2 (2)
- front-en: …
```

`## <point-id>` links the card to a bullet point; extra cards for the same point use `## <point-id> (2)`,
`(3)`, … (their card keys become `usb-2.2`, `usb-2.3`). Fields: `front-en`, `front-hu`, `back-en`,
`back-hu`, optional `figure`. Values continue on lines indented by 2 spaces.

## quiz.md

```markdown
## usb-2
- q-en: Which USB standard has a nominal data rate of 480 Mbps?
- q-hu: Melyik USB-szabvány névleges sebessége 480 Mbps?
- [ ] USB 1.1 Full Speed
- [x] USB 2.0 HighSpeed
- [ ] USB 3.2 Gen 1 SuperSpeed
- [ ] USB 3.2 Gen 2x2
- why-en: HighSpeed (USB 2.0) is 480 Mbps; Full Speed is 12 Mbps and SuperSpeed starts at 5 Gbps.
- why-hu: A HighSpeed (USB 2.0) 480 Mbps; a Full Speed 12 Mbps, a SuperSpeed 5 Gbps-tól indul.
```

Exactly four options, exactly one marked `[x]`. An option is `English | Magyar`; without ` | ` the
same text is used for both languages (typical for technical terms). A literal ` | ` inside an option
is written ` \| `. `why-en`/`why-hu` (explanation) are strongly recommended; `figure` is optional.

## Validation

`python manage.py check_content <slug> <key>` (and every save in the app) checks:

* errors (block saving): malformed lines, duplicate ids, empty required fields, quiz questions
  without exactly 4 options / exactly 1 correct option, missing or misplaced figure files;
* warnings (reported, fail `check_content`): a point without flashcard or quiz question, a card that
  refers to a missing point, a quiz question without explanation, outdated ("stale") cards.

## Stale cards

`data/cards.csv` remembers, for every flashcard and quiz question, which version of its bullet point
it was written for. If the bullet point text changes and the card does not, the card is **outdated**:
the app shows a badge and `python manage.py stale_report <slug> <key>` lists it. Updating the card
text (in the app or in the file), or pressing "Still valid", clears the flag.
