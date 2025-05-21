import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from app.services.document_processor import DocumentProcessor, DocumentProcessingError

@pytest.fixture
def mock_vectorstore():
    return MagicMock()

@pytest.fixture
def processor(mock_vectorstore):
    return DocumentProcessor(mock_vectorstore)

@patch("app.services.document_processor.PyMuPDFLoader")
@patch("app.services.document_processor.Docx2txtLoader")
def test_existing_document_skips_processing(mock_docx_loader, mock_pdf_loader, processor, mock_vectorstore):
    mock_vectorstore.similarity_search.return_value = ["existing"]
    result = processor.process_document(Path("file.pdf"), {"file_id": "123", "title": "Test"})
    assert result == []
    mock_vectorstore.similarity_search.assert_called_once()

def test_unsupported_filetype_raises(processor, mock_vectorstore):
    mock_vectorstore.similarity_search.return_value = []
    with pytest.raises(DocumentProcessingError) as e:
        processor.process_document(Path("file.txt"), {"file_id": "123"})
    assert "Unsupported file type" in str(e.value)

@patch("app.services.document_processor.PyMuPDFLoader")
def test_loader_returns_empty_raises(mock_pdf_loader, processor, mock_vectorstore):
    mock_vectorstore.similarity_search.return_value = []
    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = []
    mock_pdf_loader.return_value = mock_loader_instance
    with pytest.raises(DocumentProcessingError) as e:
        processor.process_document(Path("file.pdf"), {"file_id": "123"})
    assert "contains no text" in str(e.value)

@patch("app.services.document_processor.PyMuPDFLoader")
def test_splitter_returns_empty_raises(mock_pdf_loader, processor, mock_vectorstore):
    mock_vectorstore.similarity_search.return_value = []
    mock_loader_instance = MagicMock()
    doc = MagicMock()
    doc.metadata = {}
    mock_loader_instance.load.return_value = [doc]
    mock_pdf_loader.return_value = mock_loader_instance
    with patch.object(processor.text_splitter, "split_documents", return_value=[]):
        with pytest.raises(DocumentProcessingError) as e:
            processor.process_document(Path("file.pdf"), {"file_id": "123"})
        assert "split resulted in no chunks" in str(e.value)

@patch("app.services.document_processor.PyMuPDFLoader")
def test_all_chunks_empty_raises(mock_pdf_loader, processor, mock_vectorstore):
    mock_vectorstore.similarity_search.return_value = []
    mock_loader_instance = MagicMock()
    doc = MagicMock()
    doc.metadata = {}
    mock_loader_instance.load.return_value = [doc]
    mock_pdf_loader.return_value = mock_loader_instance
    # chunk with only whitespace
    chunk = MagicMock()
    chunk.page_content = "   "
    chunk.metadata = {}
    with patch.object(processor.text_splitter, "split_documents", return_value=[chunk]):
        with pytest.raises(DocumentProcessingError) as e:
            processor.process_document(Path("file.pdf"), {"file_id": "123"})
        assert "No valid text content" in str(e.value)

@patch("app.services.document_processor.PyMuPDFLoader")
def test_valid_document_processing(mock_pdf_loader, processor, mock_vectorstore):
    mock_vectorstore.similarity_search.return_value = []
    mock_loader_instance = MagicMock()
    doc = MagicMock()
    doc.metadata = {}
    mock_loader_instance.load.return_value = [doc]
    mock_pdf_loader.return_value = mock_loader_instance
    chunk1 = MagicMock()
    chunk1.page_content = "Chunk 1 content"
    chunk1.metadata = {"meta": "data"}
    chunk2 = MagicMock()
    chunk2.page_content = "Chunk 2 content"
    chunk2.metadata = {"meta": "data2"}
    with patch.object(processor.text_splitter, "split_documents", return_value=[chunk1, chunk2]):
        result = processor.process_document(Path("file.pdf"), {"file_id": "123"})
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["chunk_id"] == 0
        assert "Chunk 1 content" in result[0]["text"]
        mock_vectorstore.add_texts.assert_called()