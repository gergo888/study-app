# State format (CSV)

All state that is not learning content lives in `data/*.csv` (path: `DATA_ROOT`). The tables are
defined in `backend/apps/core/tables.py`; the CSV header must match the dataclass exactly, otherwise
the app refuses to read the file.

Conventions: UTF-8, comma separated, header row; booleans `1`/`0`; timestamps ISO-8601 in UTC;
dates `YYYY-MM-DD`; empty cell = no value. Mutable tables are rewritten atomically; logs are
append-only. Do not edit these files while the app is running.

| File | Kind | Written by |
|---|---|---|
| `materials.csv` | mutable | material create/update, PDF upload, plan generation |
| `chapters.csv` | mutable | PDF import / chapter rebuild, status changes, learned check |
| `plan.csv` | mutable | "Generate plan" |
| `doc_index.csv` | mutable | content sync (which Markdown version was indexed) |
| `points.csv` | mutable | content sync |
| `cards.csv` | mutable | content sync, answers (FSRS), "Still valid" |
| `review_log.csv` | append-only | every flashcard / quiz answer |
| `activity.csv` | append-only | every answer and every memorize reveal / write-out |
| `xp.csv` | append-only | every correct flashcard / quiz answer |

## materials.csv

| Column | Meaning |
|---|---|
| `slug` | Id used in URLs and folder names (`comptia-a-plus`). |
| `title`, `description` | Display texts. |
| `pdf_path`, `pdf_name` | Stored PDF (relative to `MEDIA_ROOT`) and its original file name. |
| `page_count` | Pages of the PDF. |
| `chapter_level` | Outline level used to build chapters (0 = none yet). |
| `plan_start`, `plan_target` | Study plan start and (optional) exam/target date. |
| `study_weekdays` | Study days, `0`=Monday … `6`=Sunday, comma separated. |
| `created_at` | Creation time. |

## chapters.csv

| Column | Meaning |
|---|---|
| `material`, `key` | Material slug and chapter key (`1A`); together they identify a chapter. |
| `order` | Position in the book. |
| `code`, `title` | `Topic 1A`, `Explain Cable Types and Connectors`. |
| `group_title`, `group_subtitle` | Parent outline entry (`Lesson 1`) and its title. |
| `start_page`, `end_page` | 1-based, inclusive page range in the PDF. |
| `status` | `not_started`, `reading`, `read`, `learned`. |
| `read_at`, `learned_at` | When it was marked read / learned. |
| `learned_via` | `quiz`, `flashcards`, `reveal` (memorize mode) or `manual`. |

## plan.csv

`material`, `chapter`, `order`, `scheduled_date` — one row per chapter of a generated plan.

## doc_index.csv

`material`, `chapter`, `kind` (`summary`/`flashcards`/`quiz`), `sha256` of the indexed file,
`parsed_ok`, `indexed_at`. When a file's sha differs, the chapter is reindexed.

## points.csv

| Column | Meaning |
|---|---|
| `material`, `chapter`, `point_key` | The bullet point (`{#usb-2}`). |
| `section_key`, `order` | Where it is in the summary. |
| `content_hash` | Hash of its titles and texts (EN + HU). |
| `archived` | `1` when the point no longer exists in the Markdown (history is kept). |

## cards.csv

| Column | Meaning |
|---|---|
| `material`, `chapter`, `kind`, `card_key` | The card: `kind` is `flashcard` or `quiz`; `card_key` is `usb-2` or `usb-2.2` for an extra card. |
| `point_key` | The bullet point it belongs to. |
| `text_hash` | Hash of the card's own text. |
| `basis_hash` | `content_hash` of the point when the card was last written or confirmed. Differs from the point's current hash → card is **outdated**. |
| `archived` | `1` when the card no longer exists in the Markdown. |
| `fsrs_card_id`, `fsrs_state`, `step`, `stability`, `difficulty`, `due`, `last_review` | FSRS scheduling state (empty until the first answer). `fsrs_state`: 1 learning, 2 review, 3 relearning. |
| `reps`, `lapses` | Number of answers, number of times forgotten after being learned. |

## review_log.csv

`ts`, `material`, `chapter`, `kind`, `card_key`, `rating` (FSRS 1 Again · 2 Hard · 3 Good · 4 Easy;
quiz: correct = 3, wrong = 1), `selected_index` (quiz only), `correct`, `context` (`learn` or
`review`).

## activity.csv

`ts`, `material`, `chapter`, `point_key`, `kind` (`flashcard`, `quiz`, `reveal`, `write`), `result`
(`correct`, `partial`, `wrong`, `seen`), `context`. Drives the progress chips next to each bullet point
and the "chapter learned" rules.

## xp.csv

`ts`, `amount`, `reason` (`flashcard_correct`, `quiz_correct`), `material`, `chapter`, `ref` (card
key). Total XP is the sum of `amount`; level *n* starts at 50 × (n − 1)² XP.
