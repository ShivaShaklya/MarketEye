from __future__ import annotations

import argparse
from pathlib import Path

from reporting import ReportGenerator, load_input_payload, transform_chat_to_report_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a six-page MarketEye PDF report from project chat JSON and companion report JSON."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="Path to generic report JSON input.")
    source.add_argument("--chat-json", help="Path to a MarketEye chat JSON file.")
    parser.add_argument("--report-json", help="Optional path to the paired MarketEye report JSON file.")
    parser.add_argument("--output", default="report.pdf", help="Path to the output PDF file.")
    parser.add_argument("--html-output", help="Optional path to write the rendered HTML preview.")
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Render only the HTML preview and skip PDF generation.",
    )
    parser.add_argument(
        "--assets-dir",
        default="generated_assets",
        help="Directory for generated chart assets when using MarketEye chat JSON.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.chat_json:
        chat_payload = load_input_payload(args.chat_json)
        paired_report = load_input_payload(args.report_json) if args.report_json else None
        report_payload = transform_chat_to_report_payload(
            chat_payload,
            args.assets_dir,
            report_payload=paired_report,
        )
    else:
        report_payload = load_input_payload(args.input)

    output_path = _resolve_output_path(args.output, report_payload)

    generator = ReportGenerator()

    if args.html_output:
        html_path = generator.write_html(report_payload, Path(args.html_output))
        print(f"HTML preview generated: {html_path.resolve()}")

    if args.html_only:
        return

    pdf_path = generator.generate(report_payload, output_path)
    print(f"Report generated: {pdf_path.resolve()}")


def _resolve_output_path(requested_output: str, report_payload: dict) -> Path:
    output_path = Path(requested_output)
    if output_path.name != "report.pdf":
        return output_path

    safe_author = _safe_filename(report_payload.get("author")) or "marketeye_report"
    return output_path.with_name(f"{safe_author}.pdf")


def _safe_filename(value: str | None) -> str:
    if not value:
        return ""
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value).strip())
    cleaned = cleaned.strip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned


if __name__ == "__main__":
    main()
