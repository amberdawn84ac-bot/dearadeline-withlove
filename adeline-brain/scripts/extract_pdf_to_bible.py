"""
extract_pdf_to_bible.py — Extract Everett Fox Bible from PDF

Extracts text from Everett Fox PDF and formats it for the seed script.
Requires PyPDF2 or pdfplumber.

Usage:
    pip install pdfplumber
    python scripts/extract_pdf_to_bible.py --pdf data/bible/everett_fox/five_books_moses.pdf
"""
import argparse
import re
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber")
    exit(1)


def extract_book_from_pdf(pdf_path: Path, book_name: str, start_page: int, end_page: int, output_path: Path):
    """
    Extract a single book from the PDF and format it.
    
    Args:
        pdf_path: Path to the PDF file
        book_name: Name of the book (e.g., "genesis")
        start_page: First page of the book (0-indexed)
        end_page: Last page of the book (0-indexed)
        output_path: Where to save the formatted text
    """
    print(f"Extracting {book_name} from pages {start_page}-{end_page}...")
    
    with pdfplumber.open(pdf_path) as pdf:
        text_lines = []
        
        for page_num in range(start_page, end_page + 1):
            if page_num >= len(pdf.pages):
                break
            
            page = pdf.pages[page_num]
            text = page.extract_text()
            
            if text:
                text_lines.append(text)
        
        full_text = "\n".join(text_lines)
        
        # Format the text
        formatted = format_bible_text(full_text, book_name)
        
        # Save to file
        output_path.write_text(formatted, encoding="utf-8")
        print(f"✓ Saved {book_name} to {output_path}")


def format_bible_text(raw_text: str, book_name: str) -> str:
    """
    Format extracted PDF text into the expected format:
    
    Chapter 1
    1 Verse text...
    2 Verse text...
    """
    lines = []
    current_chapter = None
    
    # This is a simplified parser - you may need to adjust based on PDF structure
    for line in raw_text.split("\n"):
        line = line.strip()
        
        # Skip empty lines and page numbers
        if not line or line.isdigit():
            continue
        
        # Detect chapter headers (e.g., "1", "Chapter 1", "CHAPTER 1")
        chapter_match = re.match(r'^(?:CHAPTER\s+)?(\d+)$', line, re.IGNORECASE)
        if chapter_match:
            current_chapter = chapter_match.group(1)
            lines.append(f"\nChapter {current_chapter}")
            continue
        
        # Detect verse lines (start with a number)
        verse_match = re.match(r'^(\d+)\s+(.+)$', line)
        if verse_match and current_chapter:
            verse_num = verse_match.group(1)
            verse_text = verse_match.group(2)
            lines.append(f"{verse_num} {verse_text}")
            continue
        
        # If we're in a chapter and line doesn't start with number, it might be continuation
        if current_chapter and lines:
            # Append to previous line
            lines[-1] += " " + line
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Extract Everett Fox Bible from PDF")
    parser.add_argument("--pdf", required=True, help="Path to the PDF file")
    parser.add_argument("--output-dir", default="data/bible/everett_fox", help="Output directory")
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf)
    output_dir = Path(__file__).resolve().parents[1] / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return
    
    # You'll need to determine the page ranges for each book by inspecting the PDF
    # These are placeholder values - adjust based on actual PDF structure
    books = [
        ("genesis", 1, 100, output_dir / "genesis.txt"),
        ("exodus", 101, 200, output_dir / "exodus.txt"),
        ("leviticus", 201, 250, output_dir / "leviticus.txt"),
        ("numbers", 251, 350, output_dir / "numbers.txt"),
        ("deuteronomy", 351, 450, output_dir / "deuteronomy.txt"),
    ]
    
    print("=" * 60)
    print("IMPORTANT: You need to manually set the page ranges!")
    print("Open the PDF and find where each book starts/ends.")
    print("Then update the 'books' list in this script.")
    print("=" * 60)
    
    # For now, just show how to extract one book as an example
    print("\nTo use this script:")
    print("1. Open the PDF and note the page numbers for each book")
    print("2. Update the 'books' list in this script with correct page ranges")
    print("3. Run the script again")
    print("\nExample for extracting just Genesis (if it's on pages 10-100):")
    print("  extract_book_from_pdf(pdf_path, 'genesis', 10, 100, output_dir / 'genesis.txt')")


if __name__ == "__main__":
    main()
