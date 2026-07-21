# Internal review request — "Markdownify" desktop tool

**To:** Thevan (IT Risk) · John (Compliance) · Martini (Microsoft/Intune)
**From:** Nabil
**Re:** Sign-off + deployment path for a small internal document-conversion app
**Status:** Working prototype built and tested. Not yet distributed to anyone.

---

## What it is

**Markdownify** is a small desktop app that converts everyday documents (Word,
Excel, PowerPoint, text-based PDFs, HTML, CSV) into clean Markdown/plain text.
It wraps Microsoft's open-source **MarkItDown** library
(https://github.com/microsoft/markitdown, MIT-licensed) in a simple window:
staff pick a file, click convert, and a `.md` text file is written next to the
original. No command line, no Python install for end users.

**Why we want it:** it's the clean-up step before any AI/LLM processing or
search indexing of documents — it turns messy files into text tools can read
reliably. Likely first uses: HR document handling, compliance/policy search,
and internal tooling.

## How it handles data (the important part)

- **Conversion runs 100% locally** on the user's machine. No file, and no
  converted text, is uploaded anywhere. There is no server component.
- MarkItDown *can* optionally call an external LLM API to describe images and
  transcribe audio. **That feature is deliberately NOT enabled in this build** —
  so there are no outbound network calls from the app.
- Output `.md` files are written to the same folder as the source file and are
  otherwise untouched by the app.

## What I'm asking each of you

**Thevan (IT Risk)**
- Review as a new internally-built endpoint tool. Blast radius is low (local,
  read-only on inputs, no network, no persistence beyond the output file).
- Confirm whether this needs a risk-register entry and what control evidence
  you'd want (source is in our control, dependencies are pinned).

**John (Compliance)**
- Confirm acceptable use boundaries — in particular, converting documents that
  contain client PII or regulated data. Since processing is local and nothing
  leaves the device, my read is the exposure is minimal, but I want your call
  before it's used on regulated content.
- Flag if any document category should be out of scope.

**Martini (Microsoft/Intune)**
- Deployment path: I'd like to distribute via **Intune** rather than passing a
  file around (each app is ~240 MB; central versioning + updates is cleaner).
- **Code-signing:** both builds are currently unsigned, so macOS Gatekeeper and
  Windows SmartScreen will warn users. Can we sign with our certs so it installs
  cleanly? This is the main blocker to a smooth rollout.

## Practical notes

- macOS version is built and tested. Windows version builds from the same code
  with one script, run on a Windows PC (a Windows `.exe` can't be built on a Mac).
- ~240 MB per app — it bundles ML libraries MarkItDown uses for file-type
  detection. This is the trade-off vs. a zero-install internal web page, which
  remains an alternative if the size/deployment overhead isn't worth it.
- Known limitation: chart-only or scanned PDFs convert poorly (only real text is
  extracted). Fine for Office docs and normal PDFs.

## Proposed next step

A 20-minute call to agree: (1) sign-off scope, (2) whether we sign + push via
Intune, or (3) whether the web-page alternative is the better fit for the
company. No distribution happens until we've agreed the path.
