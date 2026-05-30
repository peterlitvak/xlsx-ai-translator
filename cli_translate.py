import argparse
import logging
import os
import sys
import warnings
from typing import List, Tuple
import csv
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

from tqdm import tqdm

MODEL_THREADS = {"gpt-4o": 11, "gpt-4o-mini": 11}

from translator import XLSXTranslator, suppress_info_logging

# Additional dependencies for estimation mode
import openpyxl
import tiktoken
from pricing import MODEL_PRICING

# Output token estimation factors by (source, target) language pair
OUTPUT_TOKEN_FACTORS: dict[Tuple[str, str], float] = {
    ("en", "en"): 1.0,
    ("en", "ja"): 0.6,
    ("en", "de"): 1.1,
    ("en", "fr"): 1.1,
    ("en", "zh"): 0.7,
    ("ja", "en"): 1.7,
    ("ja", "ja"): 1.0,
    ("de", "en"): 0.9,
    ("fr", "en"): 0.9,
}


def find_xlsx_files(source_path: str) -> List[str]:
    """Find supported workbook files from a single XLSX file or directory tree."""
    source = Path(source_path)
    if source.is_file():
        return [str(source)] if is_xlsx_filename(source.name) else []

    if not source.is_dir():
        return []

    xlsx_files: List[str] = []
    for dirpath, _, filenames in os.walk(source):
        for filename in filenames:
            if is_xlsx_filename(filename):
                xlsx_files.append(os.path.join(dirpath, filename))
    return sorted(xlsx_files)


def is_xlsx_filename(filename: str) -> bool:
    """Return true when filename is a supported workbook name."""
    base_name = os.path.basename(filename)
    if base_name.startswith(("~$", "._")):
        return False
    return base_name.lower().endswith(".xlsx")


def get_report_root(source_path: str) -> str:
    """Return the directory where CLI summary reports should be written."""
    source = Path(source_path)
    if source.is_file():
        return str(source.parent)
    return str(source)


def ensure_target_subdir(src_file: str, target_lang: str) -> str:
    """Create a subdirectory named after the target language alongside the source file, and append the language code to the filename."""
    src_dir = os.path.dirname(src_file)
    target_dir = os.path.join(src_dir, target_lang)
    os.makedirs(target_dir, exist_ok=True)
    base, ext = os.path.splitext(os.path.basename(src_file))
    return os.path.join(target_dir, f"{base}_{target_lang}{ext}")


def estimate_cost(
    file_path: str, source_lang: str, target_lang: str, model_name: str
) -> Tuple[int, int, float]:
    """Estimate input/output tokens and cost for translating a single XLSX file."""
    wb = openpyxl.load_workbook(file_path)
    texts: List[str] = []
    sheets = [
        s for s in wb.worksheets if getattr(s, "sheet_state", "visible") == "visible"
    ]
    for sheet in sheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    val = cell.value.strip()
                    if val and any(char.isalnum() for char in val):
                        texts.append(val)
    try:
        enc = tiktoken.encoding_for_model(model_name)
        total_input_tokens = sum(len(enc.encode(str(t))) for t in texts)
    except Exception:
        total_input_tokens = sum(len(str(t).split()) for t in texts)

    factor: float = OUTPUT_TOKEN_FACTORS.get((source_lang, target_lang), 1.0)
    est_output_tokens = int(total_input_tokens * factor)
    price = MODEL_PRICING.get(model_name, MODEL_PRICING["gpt-4o"])
    cost = (total_input_tokens / 1000 * price["input"]) + (
        est_output_tokens / 1000 * price["output"]
    )
    return total_input_tokens, est_output_tokens, cost


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch XLSX Translator")
    parser.add_argument(
        "--root",
        required=True,
        help="Root directory to search for .xlsx files, or one .xlsx file",
    )
    parser.add_argument(
        "--source", required=True, help="Source language code (e.g., en)"
    )
    parser.add_argument(
        "--target", required=True, help="Target language code (e.g., fr)"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        choices=["gpt-4o", "gpt-4o-mini"],
        help="Model name to use (default: gpt-4o)",
    )
    parser.add_argument(
        "--estimate",
        action="store_true",
        help="Dry run: estimate token usage and cost only",
    )
    args = parser.parse_args()

    # Suppress info logs for CLI usage
    suppress_info_logging()
    # Suppress root logger and all other module info logs
    logging.getLogger().setLevel(logging.WARNING)
    for handler in logging.root.handlers:
        handler.setLevel(logging.WARNING)

    source_path: str = args.root
    source_lang: str = args.source
    target_lang: str = args.target
    model_name: str = args.model
    estimate_only: bool = args.estimate

    report_root = get_report_root(source_path)
    xlsx_files: List[str] = find_xlsx_files(source_path)
    if not xlsx_files:
        print(f"No .xlsx files found in {source_path}")
        sys.exit(1)

    print(f"Found {len(xlsx_files)} .xlsx files. Starting translation...")

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Dry-run estimation mode
    if estimate_only:
        grand_in = grand_out = 0
        grand_cost = 0.0
        # Prepare report file in root directory
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(
            report_root, f"estimate_report_{source_lang}_to_{target_lang}_{ts}.csv"
        )
        with open(report_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["file", "input_tokens", "output_tokens", "cost_usd"])
            for src_file in tqdm(xlsx_files, desc="Estimating", unit="file"):
                in_tok, out_tok, cost = estimate_cost(
                    src_file, source_lang, target_lang, model_name
                )
                grand_in += in_tok
                grand_out += out_tok
                grand_cost += cost
                writer.writerow(
                    [
                        os.path.relpath(src_file, report_root),
                        in_tok,
                        out_tok,
                        f"{cost:.2f}",
                    ]
                )
            # totals row
            writer.writerow(["TOTAL", grand_in, grand_out, f"{grand_cost:.2f}"])

        print("\n=== Estimate Summary ===")
        print(f"Files processed : {len(xlsx_files)}")
        print(f"Total input tokens : {grand_in}")
        print(f"Total output tokens: {grand_out}")
        print(f"Estimated cost     : ${grand_cost:.2f}")
        print(f"Detailed report saved to {report_path}\n")
        sys.exit(0)

    # Prepare actual cost report
    ts_run = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_actual_path = os.path.join(
        report_root, f"actual_report_{source_lang}_to_{target_lang}_{ts_run}.csv"
    )
    grand_act_in = grand_act_out = 0
    grand_act_cost = 0.0
    with open(report_actual_path, "w", newline="") as csvfile:
        writer_act = csv.writer(csvfile)
        writer_act.writerow(["file", "input_tokens", "output_tokens", "cost_usd"])

        for file_idx, src_file in enumerate(
            tqdm(xlsx_files, desc="Files", unit="file")
        ):
            out_file: str = ensure_target_subdir(src_file, target_lang)
            try:
                # Select model and threads
                max_workers = MODEL_THREADS.get(model_name, 11)
                translator = XLSXTranslator(
                    src_file,
                    target_language=target_lang,
                    max_workers=max_workers,
                    model_name=model_name,
                    rpm_limit=2555,
                )
                # Per-file progress as percent
                pbar_total = 100
                pbar = tqdm(
                    total=pbar_total,
                    desc=os.path.basename(src_file),
                    unit="%",
                    position=1,
                    leave=False,
                )
                last_percent = 0
                for prog in translator.translate_with_progress():
                    percent = int(prog * 100)
                    if percent > last_percent:
                        pbar.update(percent - last_percent)
                        last_percent = percent
                pbar.close()
                translator.get_result(out_file)

                # Aggregate actual token usage if available
                in_tok = getattr(translator, "actual_input_tokens", 0)
                out_tok = getattr(translator, "actual_output_tokens", 0)
                cost_val = getattr(translator, "actual_cost", 0.0)
                grand_act_in += in_tok
                grand_act_out += out_tok
                grand_act_cost += cost_val
                writer_act.writerow(
                    [
                        os.path.relpath(src_file, report_root),
                        in_tok,
                        out_tok,
                        f"{cost_val:.2f}",
                    ]
                )
            except Exception as e:
                logging.error(f"Failed to translate {src_file}: {e}")
                writer_act.writerow(
                    [
                        os.path.relpath(src_file, report_root),
                        "ERROR",
                        "ERROR",
                        "ERROR",
                    ]
                )

        # totals row
        writer_act.writerow(
            ["TOTAL", grand_act_in, grand_act_out, f"{grand_act_cost:.2f}"]
        )

    print("\n=== Actual Usage Summary ===")
    print(f"Total input tokens : {grand_act_in}")
    print(f"Total output tokens: {grand_act_out}")
    print(f"Actual cost        : ${grand_act_cost:.2f}")
    print(f"Detailed report saved to {report_actual_path}\n")


if __name__ == "__main__":
    main()
