import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.parser import (
    CorruptedFileError,
    DocumentParser,
    PasswordProtectedError,
    UnsupportedFileTypeError,
    MAX_TEXT_LENGTH,
)


class TestDocumentParser:
    def setup_method(self):
        self.parser = DocumentParser()

    # ---------- PDF Extraction ----------

    def test_parse_pdf_text_extraction(self, sample_pdf):
        result = self.parser.parse(str(sample_pdf), "application/pdf")
        assert "Invoice" in result.text
        assert "Acme Corp" in result.text
        assert result.page_count >= 1
        assert result.method == "pymupdf"

    def test_parse_pdf_auto_detect_mime(self, sample_pdf):
        """Mime type auto-detected from extension."""
        result = self.parser.parse(str(sample_pdf))
        assert result.text
        assert result.method == "pymupdf"

    def test_parse_empty_pdf(self, empty_pdf):
        """Empty PDF triggers OCR fallback."""
        # Mock tesseract since we can't guarantee it's installed in CI
        with patch("app.services.parser.pytesseract.image_to_string", return_value=""):
            result = self.parser.parse(str(empty_pdf), "application/pdf")
            # OCR on a blank page returns minimal text
            assert result.method.startswith("pymupdf+ocr")

    # ---------- DOCX Extraction ----------

    def test_parse_docx_text_extraction(self, sample_docx):
        result = self.parser.parse(str(sample_docx))
        assert "Contract Agreement" in result.text
        assert "Party A" in result.text
        assert result.page_count >= 1
        assert result.method == "python-docx"

    def test_parse_docx_with_tables(self, sample_docx):
        result = self.parser.parse(str(sample_docx))
        assert "Item" in result.text
        assert "Duration" in result.text
        assert "12 months" in result.text

    # ---------- Image OCR ----------

    def test_parse_image(self, sample_image):
        """Image parsing invokes Tesseract OCR."""
        with patch("app.services.parser.pytesseract.image_to_string", return_value="OCR text from image"):
            result = self.parser.parse(str(sample_image), "image/png")
            assert result.text == "OCR text from image"
            assert result.page_count == 1
            assert result.method == "tesseract"

    # ---------- Error Handling ----------

    def test_unsupported_file_type(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")
        with pytest.raises(UnsupportedFileTypeError):
            self.parser.parse(str(txt_file), "text/plain")

    def test_unsupported_extension_no_mime(self, tmp_path):
        unknown_file = tmp_path / "test.xyz"
        unknown_file.write_text("data")
        with pytest.raises(UnsupportedFileTypeError):
            self.parser.parse(str(unknown_file))

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.parser.parse("/nonexistent/file.pdf", "application/pdf")

    def test_corrupted_pdf(self, tmp_path):
        bad_pdf = tmp_path / "corrupt.pdf"
        bad_pdf.write_bytes(b"not a real pdf content at all")
        with pytest.raises(CorruptedFileError):
            self.parser.parse(str(bad_pdf), "application/pdf")

    def test_password_protected_pdf(self, tmp_path):
        """Password-protected PDF raises PasswordProtectedError."""
        import fitz

        pdf_path = tmp_path / "protected.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Secret content")
        perm = fitz.PDF_PERM_ACCESSIBILITY
        encrypt_meth = fitz.PDF_ENCRYPT_AES_256
        doc.save(
            str(pdf_path),
            encryption=encrypt_meth,
            owner_pw="owner123",
            user_pw="user123",
            permissions=perm,
        )
        doc.close()

        with pytest.raises(PasswordProtectedError):
            self.parser.parse(str(pdf_path), "application/pdf")

    # ---------- Truncation ----------

    def test_large_document_truncated(self, tmp_path):
        """Documents exceeding MAX_TEXT_LENGTH are truncated with beginning+end preservation."""
        import fitz

        pdf_path = tmp_path / "large.pdf"
        doc = fitz.open()
        # Create many pages, each with substantial text to exceed MAX_TEXT_LENGTH
        line = "This is a long repeated sentence for testing document truncation behavior. " * 10
        for _ in range(200):
            page = doc.new_page()
            # Insert text at multiple y-positions to pack more text per page
            for y in range(72, 750, 14):
                page.insert_text((72, y), line[:100])
        doc.save(str(pdf_path))
        doc.close()

        result = self.parser.parse(str(pdf_path), "application/pdf")
        # If the extracted text exceeds the threshold, it should be truncated
        if len(result.text) < MAX_TEXT_LENGTH:
            # Text was small enough — verify it's not truncated
            assert "[... content truncated ...]" not in result.text
        else:
            assert "[... content truncated ...]" in result.text
            assert "truncated" in result.method

    # ---------- OCR Fallback ----------

    def test_needs_ocr_short_text(self):
        assert self.parser._needs_ocr("ab") is True
        assert self.parser._needs_ocr("") is True

    def test_needs_ocr_sufficient_text(self):
        assert self.parser._needs_ocr("x" * 100) is False

    # ---------- MIME Map ----------

    def test_ext_mime_map_coverage(self):
        supported = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tiff"}
        assert set(DocumentParser.EXT_MIME_MAP.keys()) == supported
