"""
Test script to demonstrate image optimization improvements.
Shows the file size difference between old (PNG, zoom 3.0) and new (JPEG, zoom 1.5) approach.
"""

import fitz
from pathlib import Path
import time

def test_pdf_parsing_performance(pdf_path: str):
    """Test PDF parsing performance with different settings."""

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_path}")
        return

    print(f"Testing with: {pdf_file.name}")
    print("=" * 70)

    # Old settings (PNG, zoom 3.0)
    print("\n🔴 OLD SETTINGS: PNG format, zoom 3.0 (9x pixels)")
    start = time.time()
    old_total_size = 0
    num_pages = 0

    with fitz.open(pdf_file) as doc:
        num_pages = len(doc)
        for page_num, page in enumerate(doc, start=1):
            mat = fitz.Matrix(3.0, 3.0)
            pix = page.get_pixmap(matrix=mat)
            image_data = pix.tobytes("png")
            old_total_size += len(image_data)
            if page_num == 1:
                print(f"   Slide 1: {len(image_data) / 1024 / 1024:.2f} MB")

    old_time = time.time() - start
    print(f"   Total size: {old_total_size / 1024 / 1024:.2f} MB")
    print(f"   Parse time: {old_time:.2f}s")
    print(f"   Num slides: {num_pages}")

    # New settings (JPEG, zoom 1.5)
    print("\n🟢 NEW SETTINGS: JPEG format, zoom 1.5 (2.25x pixels)")
    start = time.time()
    new_total_size = 0

    with fitz.open(pdf_file) as doc:
        for page_num, page in enumerate(doc, start=1):
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            image_data = pix.tobytes("jpeg", jpg_quality=85)
            new_total_size += len(image_data)
            if page_num == 1:
                print(f"   Slide 1: {len(image_data) / 1024 / 1024:.2f} MB")

    new_time = time.time() - start
    print(f"   Total size: {new_total_size / 1024 / 1024:.2f} MB")
    print(f"   Parse time: {new_time:.2f}s")
    print(f"   Num slides: {num_pages}")

    # Comparison
    print("\n📊 IMPROVEMENT:")
    size_reduction = (1 - new_total_size / old_total_size) * 100
    time_improvement = (1 - new_time / old_time) * 100
    print(f"   Size reduction: {size_reduction:.1f}% smaller")
    print(f"   Speed improvement: {time_improvement:.1f}% faster")
    print(f"   Memory saved: {(old_total_size - new_total_size) / 1024 / 1024:.2f} MB")

    print("\n✅ Expected results:")
    print(f"   - Slide switching: {old_time / num_pages * 1000:.0f}ms → {new_time / num_pages * 1000:.0f}ms")
    print(f"   - Initial load: {old_time:.1f}s → {new_time:.1f}s")
    print(f"   - Browser memory: {old_total_size / 1024 / 1024:.0f}MB → {new_total_size / 1024 / 1024:.0f}MB")


if __name__ == "__main__":
    # Test with the 12-page presentation mentioned by the user
    test_files = [
        "data/slides/20260215_183749_Pacemaker 2.pdf",
        # Add other test files if available
    ]

    for test_file in test_files:
        if Path(test_file).exists():
            test_pdf_parsing_performance(test_file)
            print("\n")
        else:
            print(f"⚠️  Test file not found: {test_file}")
            print("   Looking for other PDF files in data/slides/...")

            # Try to find any PDF in data/slides
            data_dir = Path("data/slides")
            if data_dir.exists():
                pdfs = list(data_dir.glob("*.pdf"))
                if pdfs:
                    print(f"   Found: {pdfs[0].name}")
                    test_pdf_parsing_performance(str(pdfs[0]))
                else:
                    print("   No PDFs found in data/slides/")




