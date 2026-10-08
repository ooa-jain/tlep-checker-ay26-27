"""
Base Document Extractor Dispatcher
Routes uploaded TLEP file to the appropriate format extractor (Excel, Word DOCX, PDF).
"""

import os
from models.schemas import NormalizedTLEP
from extractors.excel import extract_excel_tlep
from extractors.docx import extract_docx_tlep
from extractors.pdf import extract_pdf_tlep


def extract_tlep_document(file_path: str) -> NormalizedTLEP:
    """Extract and normalize a TLEP document from file_path."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in [".xlsx", ".xls"]:
        return extract_excel_tlep(file_path)
    elif ext == ".docx":
        return extract_docx_tlep(file_path)
    elif ext == ".pdf":
        return extract_pdf_tlep(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported formats are .xlsx, .docx, .pdf")
