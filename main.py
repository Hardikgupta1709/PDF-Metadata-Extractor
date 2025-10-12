# main.py
import sys
import os
import argparse
import configparser

# Add src to path BEFORE any other imports from src
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")

print(f"DEBUG: Project root: {project_root}")
print(f"DEBUG: Adding to sys.path: {src_path}")
print(f"DEBUG: src path exists: {os.path.exists(src_path)}")

if src_path not in sys.path:
    sys.path.insert(0, src_path)

print(f"DEBUG: sys.path = {sys.path[:3]}")  # Show first 3 paths

# Now import from src
try:
    from parser.grobid_client import parse_pdf_with_grobid, extract_metadata_from_tei
    from parser.email_extractor import extract_full_text, find_emails
    from utils.file_utils import save_to_json, save_to_csv
    print("DEBUG: All imports successful!")
except ImportError as e:
    print(f"ERROR: Import failed: {e}")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    print(f"DEBUG: Contents of src/: {os.listdir(src_path) if os.path.exists(src_path) else 'NOT FOUND'}")
    if os.path.exists(os.path.join(src_path, 'utils')):
        print(f"DEBUG: Contents of src/utils/: {os.listdir(os.path.join(src_path, 'utils'))}")
    sys.exit(1)


def main(pdf_path: str, output_dir: str):
    """
    Main function to orchestrate the PDF parsing pipeline.
    """
    # Load Configuration
    config = configparser.ConfigParser()
    config.read('config/config.ini')
    grobid_server = config.get('GROBID', 'server', fallback='http://localhost:8070')

    print(f"Processing file: {pdf_path}")

    # Step 1: Parse PDF with GROBID
    try:
        print("Step 1: Parsing with GROBID...")
        tei_xml = parse_pdf_with_grobid(pdf_path, grobid_server)
        metadata = extract_metadata_from_tei(tei_xml)
        print("GROBID parsing successful.")
    except Exception as e:
        print(f"Error during GROBID processing: {e}")
        return

    # Step 2: Extract text and emails
    try:
        print("Step 2: Extracting text and finding emails...")
        full_text = extract_full_text(pdf_path)
        emails = find_emails(full_text)
        metadata['emails'] = emails
        print(f"Found {len(emails)} email(s).")
    except Exception as e:
        print(f"Error during email extraction: {e}")
        metadata['emails'] = []

    # Step 3: Save results
    base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    json_output_path = os.path.join(output_dir, f"{base_filename}.json")
    csv_output_path = os.path.join(output_dir, f"{base_filename}.csv")

    try:
        save_to_json(metadata, json_output_path)
        print(f"Results saved to {json_output_path}")
        save_to_csv(metadata, csv_output_path)
        print(f"Results saved to {csv_output_path}")
    except Exception as e:
        print(f"Error saving output files: {e}")

    # Print summary
    print("\n--- Extracted Data ---")
    print(f"Title: {metadata.get('title')}")
    print(f"Authors: {', '.join(metadata.get('authors', []))}")
    print(f"Emails: {', '.join(metadata.get('emails', []))}")
    print(f"Abstract: {metadata.get('abstract', 'N/A')[:200]}...")
    print("----------------------\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract metadata from a PDF")
    parser.add_argument("pdf_path", type=str, help="Path to the input PDF")
    parser.add_argument("--output_dir", type=str, default="data/output", help="Directory to save outputs")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    main(args.pdf_path, args.output_dir)