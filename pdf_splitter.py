from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class Marker:
    label: str
    marker: str


@dataclass
class PageRange:
    label: str
    marker: str
    start_page: int
    end_page: int

    @property
    def page_count(self) -> int:
        return self.end_page - self.start_page + 1


def normalize_text(text: str) -> str:
    """Collapse whitespace and normalise case for robust text comparison."""
    return " ".join(text.split()).strip().casefold()


def safe_filename(value: str) -> str:
    """Convert a label into a filesystem-safe filename component."""
    value = re.sub(r"[^A-Za-z0-9._ -]+", "", value).strip()
    value = re.sub(r"\s+", "_", value)
    return value or "output"


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    if not config.get("markers"):
        raise ValueError("Config must contain a non-empty 'markers' list.")

    config.setdefault("start_page", 1)
    config.setdefault("end_page", None)
    config.setdefault("match_mode", "exact")
    config.setdefault("output_suffix", "")

    if config["match_mode"] not in {"exact", "contains"}:
        raise ValueError("'match_mode' must be either 'exact' or 'contains'.")

    return config


def marker_matches(page_text: str, marker_text: str, match_mode: str) -> bool:
    page_value = normalize_text(page_text)
    marker_value = normalize_text(marker_text)

    if match_mode == "exact":
        return page_value == marker_value
    return marker_value in page_value


def detect_markers(
    doc: fitz.Document,
    markers: list[Marker],
    start_page: int,
    end_page: int,
    match_mode: str,
) -> list[tuple[Marker, int]]:
    """Return each configured marker and the 1-based page on which it was found."""
    found: list[tuple[Marker, int]] = []
    remaining = markers.copy()

    for page_number in range(start_page, end_page + 1):
        if not remaining:
            break

        page_text = doc.load_page(page_number - 1).get_text("text")

        # Markers are expected in configured order. This avoids matching a later
        # section before an earlier one when headings are similar.
        expected = remaining[0]
        if marker_matches(page_text, expected.marker, match_mode):
            found.append((expected, page_number))
            remaining.pop(0)

    if remaining:
        missing = ", ".join(marker.label for marker in remaining)
        raise ValueError(f"Could not find configured marker(s): {missing}")

    return found


def build_ranges(
    detected: list[tuple[Marker, int]],
    document_end_page: int,
) -> list[PageRange]:
    ranges: list[PageRange] = []

    for index, (marker, start_page) in enumerate(detected):
        if index + 1 < len(detected):
            end_page = detected[index + 1][1] - 1
        else:
            end_page = document_end_page

        if end_page < start_page:
            raise ValueError(
                f"Invalid page range for {marker.label}: {start_page}-{end_page}"
            )

        ranges.append(
            PageRange(
                label=marker.label,
                marker=marker.marker,
                start_page=start_page,
                end_page=end_page,
            )
        )

    return ranges


def write_manifest(ranges: list[PageRange], output_dir: Path, suffix: str) -> Path:
    manifest_path = output_dir / "manifest.csv"

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "label",
                "marker",
                "start_page",
                "end_page",
                "page_count",
                "output_file",
            ]
        )

        for item in ranges:
            filename = f"{safe_filename(item.label)}{suffix}.pdf"
            writer.writerow(
                [
                    item.label,
                    item.marker,
                    item.start_page,
                    item.end_page,
                    item.page_count,
                    filename,
                ]
            )

    return manifest_path


def split_pdf(
    doc: fitz.Document,
    ranges: list[PageRange],
    output_dir: Path,
    suffix: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for item in ranges:
        output = fitz.open()
        output.insert_pdf(
            doc,
            from_page=item.start_page - 1,
            to_page=item.end_page - 1,
        )

        filename = f"{safe_filename(item.label)}{suffix}.pdf"
        output_path = output_dir / filename
        output.save(output_path, garbage=4, deflate=True)
        output.close()

        print(
            f"Created {output_path.name}: "
            f"pages {item.start_page}-{item.end_page} ({item.page_count} pages)"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split a large PDF into labelled sub-documents using marker pages."
    )
    parser.add_argument("input_pdf", type=Path, help="Path to the source PDF")
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="JSON configuration containing marker labels and matching settings",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Directory for split PDFs and manifest.csv",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect and display ranges without writing PDFs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    if not args.input_pdf.exists():
        raise FileNotFoundError(f"Input PDF not found: {args.input_pdf}")

    markers = [Marker(**item) for item in config["markers"]]

    with fitz.open(args.input_pdf) as doc:
        total_pages = len(doc)
        start_page = int(config["start_page"])
        end_page = int(config["end_page"] or total_pages)

        if start_page < 1 or start_page > total_pages:
            raise ValueError(
                f"start_page must be between 1 and {total_pages}; got {start_page}."
            )
        if end_page < start_page or end_page > total_pages:
            raise ValueError(
                f"end_page must be between {start_page} and {total_pages}; got {end_page}."
            )

        detected = detect_markers(
            doc=doc,
            markers=markers,
            start_page=start_page,
            end_page=end_page,
            match_mode=config["match_mode"],
        )
        ranges = build_ranges(detected, document_end_page=end_page)

        print("\nDetected ranges:")
        for item in ranges:
            print(
                f"- {item.label}: pages {item.start_page}-{item.end_page} "
                f"({item.page_count} pages)"
            )

        if args.dry_run:
            print("\nDry run complete. No PDFs were written.")
            return

        args.output.mkdir(parents=True, exist_ok=True)
        split_pdf(doc, ranges, args.output, config["output_suffix"])
        manifest = write_manifest(ranges, args.output, config["output_suffix"])
        print(f"\nManifest written to {manifest}")


if __name__ == "__main__":
    main()
