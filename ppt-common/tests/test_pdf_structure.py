"""Tests for PDF structure extraction utilities."""

import pytest


def test_pdfstructure_dataclass():
    from ppt_common.pdf_structure import PDFStructure
    
    structure = PDFStructure(
        chapter_titles=["第一章 传播概述", "第二章 传播模式"],
        section_titles=["第一节 传播的定义", "第二节 传播要素"],
        bold_text=["关键概念", "重要定义"],
        ordered_lists=[["1. 传播者", "2. 受传者", "3. 信息"]],
        pdf_path="test.pdf"
    )
    
    assert structure.chapter_titles == ["第一章 传播概述", "第二章 传播模式"]
    assert structure.section_titles == ["第一节 传播的定义", "第二节 传播要素"]
    assert len(structure.bold_text) == 2
    assert structure.pdf_path == "test.pdf"


def test_extract_chapter_titles(tmp_path):
    """Test extraction of chapter titles (第X章, Chapter N) from PDF."""
    import fitz
    from ppt_common.pdf_structure import extract_chapter_titles
    
    # Create test PDF with chapter titles (using English to avoid font issues)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Chapter 1 Introduction", fontsize=16)
    page.insert_text((100, 200), "This is regular text.")
    page.insert_text((100, 300), "Chapter 2 Methods", fontsize=16)
    
    pdf_path = tmp_path / "test_chapters.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    titles = extract_chapter_titles(str(pdf_path))
    
    assert len(titles) == 2
    assert "Chapter 1 Introduction" in titles
    assert "Chapter 2 Methods" in titles


def test_extract_section_titles(tmp_path):
    """Test extraction of section titles (Section N, numbered headings) from PDF."""
    import fitz
    from ppt_common.pdf_structure import extract_section_titles
    
    # Create test PDF with section titles (using English to avoid font issues)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Section 1 Definition", fontsize=14)
    page.insert_text((100, 150), "Regular text here.")
    page.insert_text((100, 200), "Section 2 Elements", fontsize=14)
    page.insert_text((100, 250), "1.1 The Communicator")  # numbered section
    
    pdf_path = tmp_path / "test_sections.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    titles = extract_section_titles(str(pdf_path))
    
    assert len(titles) >= 2
    assert "Section 1 Definition" in titles
    assert "Section 2 Elements" in titles


def test_extract_bold_text(tmp_path):
    """Test extraction of bold text from PDF."""
    import fitz
    from ppt_common.pdf_structure import extract_bold_text
    
    # Create test PDF with bold text
    doc = fitz.open()
    page = doc.new_page()
    # Use hebo (Helvetica-Bold) which is a standard PDF font
    page.insert_text((100, 100), "Key Concept", fontsize=12, fontname="hebo")
    page.insert_text((100, 150), "Regular text here.", fontname="helv")
    page.insert_text((100, 200), "Important Definition", fontsize=12, fontname="hebo")
    
    pdf_path = tmp_path / "test_bold.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    bold_items = extract_bold_text(str(pdf_path))
    
    assert len(bold_items) >= 2
    assert "Key Concept" in bold_items
    assert "Important Definition" in bold_items


def test_extract_ordered_lists(tmp_path):
    """Test extraction of ordered lists from PDF."""
    import fitz
    from ppt_common.pdf_structure import extract_ordered_lists
    
    # Create test PDF with ordered list
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Elements include:")
    page.insert_text((100, 150), "1. Communicator")
    page.insert_text((100, 180), "2. Audience")
    page.insert_text((100, 210), "3. Message")
    page.insert_text((100, 300), "This is regular paragraph.")
    
    pdf_path = tmp_path / "test_lists.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    lists = extract_ordered_lists(str(pdf_path))
    
    assert len(lists) >= 1
    assert len(lists[0]) >= 3
    assert "1. Communicator" in lists[0]
    assert "2. Audience" in lists[0]


def test_extract_pdf_structure(tmp_path):
    """Test convenience function to extract all PDF structure."""
    import fitz
    from ppt_common.pdf_structure import extract_pdf_structure, PDFStructure
    
    # Create comprehensive test PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Chapter 1 Overview", fontsize=16)
    page.insert_text((100, 150), "Section 1 Definition", fontsize=14)
    page.insert_text((100, 200), "Key Term", fontsize=12, fontname="hebo")
    page.insert_text((100, 250), "List:")
    page.insert_text((100, 280), "1. Item A")
    page.insert_text((100, 310), "2. Item B")
    
    pdf_path = tmp_path / "test_full.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    structure = extract_pdf_structure(str(pdf_path))
    
    assert isinstance(structure, PDFStructure)
    assert len(structure.chapter_titles) >= 1
    assert len(structure.section_titles) >= 1
    assert len(structure.bold_text) >= 1
    assert len(structure.ordered_lists) >= 1
    assert structure.pdf_path == str(pdf_path)


def test_extract_bold_text_filters_digits(tmp_path):
    """Test that pure digit strings (page numbers) are filtered out from bold text."""
    import fitz
    from ppt_common.pdf_structure import extract_bold_text
    
    # Create test PDF with bold text including page numbers
    doc = fitz.open()
    page = doc.new_page()
    # Use hebo (Helvetica-Bold) which is a standard PDF font
    page.insert_text((100, 100), "Key Concept", fontsize=12, fontname="hebo")
    page.insert_text((100, 150), "93", fontsize=12, fontname="hebo")  # Page number
    page.insert_text((100, 200), "Important Definition", fontsize=12, fontname="hebo")
    page.insert_text((100, 250), "12345", fontsize=12, fontname="hebo")  # Another page number
    
    pdf_path = tmp_path / "test_bold_digits.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    bold_items = extract_bold_text(str(pdf_path))
    
    assert "Key Concept" in bold_items
    assert "Important Definition" in bold_items
    assert "93" not in bold_items  # Pure digits should be filtered
    assert "12345" not in bold_items  # Pure digits should be filtered
