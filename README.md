# PDF Document Splitter Automation

A reusable Python tool for splitting large PDFs into structured sub-documents using identifiable page markers and automated boundary detection.

## Why I built this

This project came from a real document-processing task involving an **893-page PDF**. The required section contained **796 relevant pages** that needed to be separated into **36 state-level PDF files**.

Doing that manually would have meant repeatedly locating page boundaries, extracting page ranges, renaming files, and checking that one section did not spill into the next. The script turns that repetitive workflow into a configurable automation task.

## What the tool does

- Scans a PDF from a configurable starting page
- Detects section cover pages using text markers
- Builds page ranges automatically from the detected markers
- Splits the source document into individual PDFs
- Creates safe, consistent output filenames
- Generates a CSV manifest showing every detected range
- Supports a dry-run mode so boundaries can be reviewed before files are written
- Validates missing markers and invalid page ranges before processing

## Case-study result

For the original task:

- Source document: **893 pages**
- Relevant section: **796 pages**
- Output: **36 PDFs**
- Manual repetitive splitting: replaced with a single Python workflow

The main lesson was not simply how to split a PDF. The important part was translating an ambiguous manual request into a repeatable process:

**clarify the scope → identify deterministic rules → automate → validate → deliver**

## Project structure

```text
PDF-Document-Splitter-Automation/
├── pdf_splitter.py
├── requirements.txt
├── .gitignore
├── README.md
└── examples/
    └── nigeria_state_assembly_config.json
```

## Installation

Clone the repository and install the dependency:

```bash
git clone https://github.com/Danniejnr/PDF-Document-Splitter-Automation.git
cd PDF-Document-Splitter-Automation
pip install -r requirements.txt
```

## Usage

The splitter is configuration-driven. Each marker represents the heading page that begins a new output document.

```bash
python pdf_splitter.py input.pdf \
  --config examples/nigeria_state_assembly_config.json \
  --output output
```

Before writing files, inspect the detected page ranges with:

```bash
python pdf_splitter.py input.pdf \
  --config examples/nigeria_state_assembly_config.json \
  --output output \
  --dry-run
```

A successful run creates the individual PDFs and a `manifest.csv` file containing:

```text
label,marker,start_page,end_page,page_count,output_file
```

## Configuration

Example:

```json
{
  "start_page": 98,
  "end_page": 893,
  "match_mode": "exact",
  "output_suffix": "_State_House_of_Assembly",
  "markers": [
    {"label": "Abia", "marker": "ABIA STATE"},
    {"label": "Adamawa", "marker": "ADAMAWA STATE"},
    {"label": "Akwa Ibom", "marker": "AKWA IBOM STATE"}
  ]
}
```

### Match modes

`exact` is the safer default. A page is considered a marker page only when its extracted text matches the configured marker after whitespace and case normalisation.

`contains` is available for PDFs where marker pages contain extra text, but it should be used carefully because ordinary content pages can also contain the same words.

## Reusing it for other documents

The code is not tied to election documents. It can be adapted to split:

- reports by chapter
- policy documents by region
- textbooks by unit
- scanned/publication compilations by heading
- legal or administrative bundles by section
- large organisational reports by department

The reusable part is the workflow: detect known boundary pages, convert them into ranges, and export each range consistently.

## Limitations

- Marker detection depends on extractable PDF text. Image-only scans require OCR or a different detection method.
- `contains` matching can produce false positives if markers also appear in body text.
- Automated splitting should still be followed by spot-checking the first and last page of selected outputs.

## Tech

- Python
- PyMuPDF (`fitz`)
- `argparse`
- JSON configuration
- CSV manifest generation

## Author

**Daniel Enemona Mamodu**  
Data science, automation, and computational biology projects.
