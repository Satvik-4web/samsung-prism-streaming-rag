import hashlib
from collections.abc import Iterator

from backend.interfaces.adapters import CorpusAdapter
from backend.schemas.corpus import Chunk, Document, Section


class MarkdownAdapter(CorpusAdapter):
    def load(self, source_path: str) -> Iterator[Document]:
        with open(source_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        doc = Document(document_id="Doc_dev1", title="Sample", sections=[])
        sections = content.split("##")
        for i, sec in enumerate(sections[1:], start=1):
            lines = sec.split("\n", 1)
            sec_title = lines[0].strip()
            sec_content = lines[1].strip() if len(lines) > 1 else ""
            doc.sections.append(Section(section_id=f"S{i}", title=sec_title, content=sec_content))
        yield doc

    def chunk(self, document: Document) -> Iterator[Chunk]:
        for i, sec in enumerate(document.sections, start=1):
            text = sec.content
            yield Chunk(
                chunk_id=f"{document.document_id}::{sec.section_id}::{i:04d}",
                document_id=document.document_id,
                section_id=sec.section_id,
                text=text,
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
                token_count=len(text.split())
            )
