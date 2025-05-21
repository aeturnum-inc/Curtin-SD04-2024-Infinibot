"""
Utility functions for parsing various document formats.
"""
import io
import pdfplumber
import docx2txt


def parse_pdf(content_bytes):
    """
    Parse PDF content to extract text.
    
    Args:
        content_bytes: The PDF content as bytes
        
    Returns:
        str: The extracted text content
    """
    with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
        text = " ".join(page.extract_text() or "" for page in pdf.pages)
    return text


def parse_docx(content_bytes):
    """
    Parse DOCX content to extract text.
    
    Args:
        content_bytes: The DOCX content as bytes
        
    Returns:
        str: The extracted text content
    """
    return docx2txt.process(io.BytesIO(content_bytes))


def parse_content_by_type(content_bytes, content_type):
    """
    Parse content based on its MIME type.
    
    Args:
        content_bytes: The content as bytes
        content_type: The MIME type of the content
        
    Returns:
        str: The extracted text content
    """
    if "application/pdf" in content_type:
        return parse_pdf(content_bytes)
    elif "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in content_type:
        return parse_docx(content_bytes)
    elif "text/" in content_type or "application/json" in content_type:
        return content_bytes.decode('utf-8')
    else:
        return f"Unsupported content type: {content_type}"