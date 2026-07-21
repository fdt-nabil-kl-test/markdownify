# MarkItDown — Evaluation

A self-contained sandbox for trying out Microsoft's **MarkItDown**
(https://github.com/microsoft/markitdown) — a tool that converts documents
(Word, Excel, PowerPoint, PDF, HTML, images, audio) into clean Markdown text,
mainly so they can be fed to AI/LLM tools or search indexes.

This folder is **separate from the HR-System repo** — nothing here touches it.

## What's installed

- Python virtual environment in `venv/` (keeps everything isolated from system Python)
- `markitdown` **0.1.6** with the `pdf`, `docx`, `xlsx`, `pptx` extras

> Note: the `[all]` bundle does not install on Python 3.14 yet (some optional
> dependencies lack 3.14 wheels). The four extras above cover the common office
> formats and install cleanly.

## How to use it

Convert a file and print the result to the screen:

```
./venv/bin/markitdown "/path/to/your/document.xlsx"
```

Save the result to a Markdown file:

```
./venv/bin/markitdown "/path/to/your/document.docx" > output.md
```

## What works well vs. not

| Input | Result |
| --- | --- |
| Word (.docx), PowerPoint (.pptx) | Good — headings, lists, tables preserved |
| Excel (.xlsx) | Excellent — becomes a clean Markdown table |
| Text-based PDF | Good |
| Chart / image / scanned PDF | Poor — only real text is extracted; charts and images are lost. Needs OCR add-ons and still won't recover visual charts. |

## Before using on real company data (regulated environment)

- Core conversion runs **entirely locally** — no data leaves this machine.
- The **optional** image-description and audio-transcription features call an
  external LLM API you configure. Do **not** enable those for client/PII data
  without Compliance (John) signing off on where that data goes.
- Loop in IT Risk (Thevan) and Compliance (John) before any rollout that
  touches real employee or client documents.
