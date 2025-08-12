import argparse
import logging
import os
import sys
import warnings
from typing import List

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

from tqdm import tqdm

MODEL_THREADS = {
    "gpt-4o": 11,
    "gpt-4o-mini": 11
}

from translator import XLSXTranslator, suppress_info_logging


def find_xlsx_files(root_dir: str) -> List[str]:
    """Recursively find all .xlsx files under root_dir."""
    xlsx_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith('.xlsx'):
                xlsx_files.append(os.path.join(dirpath, filename))
    return xlsx_files


def ensure_target_subdir(src_file: str, target_lang: str) -> str:
    """Create a subdirectory named after the target language alongside the source file, and append the language code to the filename."""
    src_dir = os.path.dirname(src_file)
    target_dir = os.path.join(src_dir, target_lang)
    os.makedirs(target_dir, exist_ok=True)
    base, ext = os.path.splitext(os.path.basename(src_file))
    return os.path.join(target_dir, f"{base}_{target_lang}{ext}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch XLSX Translator")
    parser.add_argument('--root', required=True, help='Root directory to search for .xlsx files')
    parser.add_argument('--source', required=True, help='Source language code (e.g., en)')
    parser.add_argument('--target', required=True, help='Target language code (e.g., fr)')
    parser.add_argument('--model', default='gpt-4o', choices=['gpt-4o', 'gpt-4o-mini'],
                        help='Model name to use (default: gpt-4o)')
    args = parser.parse_args()

    # Suppress info logs for CLI usage
    suppress_info_logging()
    # Suppress root logger and all other module info logs
    logging.getLogger().setLevel(logging.WARNING)
    for handler in logging.root.handlers:
        handler.setLevel(logging.WARNING)

    root: str = args.root
    source_lang: str = args.source
    target_lang: str = args.target
    model_name: str = args.model

    xlsx_files: List[str] = find_xlsx_files(root)
    if not xlsx_files:
        print(f"No .xlsx files found in {root}")
        sys.exit(1)

    print(f"Found {len(xlsx_files)} .xlsx files. Starting translation...")

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    for file_idx, src_file in enumerate(tqdm(xlsx_files, desc="Files", unit="file")):
        out_file: str = ensure_target_subdir(src_file, target_lang)
        try:
            # Select model and threads
            max_workers = MODEL_THREADS.get(model_name, 11)
            translator = XLSXTranslator(src_file,
                                        target_language=target_lang,
                                        max_workers=max_workers,
                                        model_name=model_name,
                                        rpm_limit=2555)
            # Per-file progress as percent
            pbar_total = 100
            pbar = tqdm(total=pbar_total, desc=os.path.basename(src_file), unit="%", position=1, leave=False)
            last_percent = 0
            for prog in translator.translate_with_progress():
                percent = int(prog * 100)
                if percent > last_percent:
                    pbar.update(percent - last_percent)
                    last_percent = percent
            pbar.close()
            translator.get_result(out_file)
        except Exception as e:
            logging.error(f"Failed to translate {src_file}: {e}")


if __name__ == "__main__":
    main()
