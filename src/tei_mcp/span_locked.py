"""
Span-locked composition for tei-mcp.

This module implements the span-locked rung of the architectural ladder
described in the paper *Shall we entrust our archives to large language
models?*. The premise: rather than asking a model to emit TEI directly
from source text, we ask it to emit `(start, end, element, attrs)` tuples
over the source plaintext. The composer (this module) then assembles
final TEI by interleaving the recorded tags with the source — preserving
body text byte-for-byte by construction.

Three MCP tools are exposed in `server.py`:
    get_source(document_id) -> str
    tag_span(document_id, start, end, element_path, attrs) -> dict
    compose(document_id) -> str

`element_path` is a slash-separated path that documents the intended
nesting context (e.g. "TEI/text/body/div/p/persName"), but only the LAST
segment is used as the element's local name. The rest is recorded for
provenance and future composer features.

Source documents are loaded from a configured `source_root` directory.
A document ID is the filename stem (no extension).
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lxml import etree


TEI_NS = "http://www.tei-c.org/ns/1.0"
TEI_PREFIX = f"{{{TEI_NS}}}"
XML_NS = "http://www.w3.org/XML/1998/namespace"
XML_PREFIX = f"{{{XML_NS}}}"


@dataclass
class TagRecord:
    start: int
    end: int
    element: str  # local name only (last segment of element_path)
    element_path: str  # full path for provenance
    attrs: Dict[str, str] = field(default_factory=dict)
    record_id: str = ""  # stable ID returned to caller

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DocumentState:
    document_id: str
    source_path: Path
    source_text: str
    tags: List[TagRecord] = field(default_factory=list)


class SpanStore:
    """Per-server in-memory state for span-locked composition.

    Thread-safe via a single lock — fastmcp may invoke tools concurrently.
    """

    def __init__(self, source_root: Path):
        self.source_root = Path(source_root)
        self._docs: Dict[str, DocumentState] = {}
        self._lock = threading.Lock()
        self._next_record_id = 0

    def _doc(self, document_id: str) -> DocumentState:
        """Return the document state, loading from disk if not cached."""
        with self._lock:
            if document_id in self._docs:
                return self._docs[document_id]
            # Look up file: try .txt, .xml, then any extension matching the stem
            candidates = list(self.source_root.glob(f"{document_id}.*"))
            txt = self.source_root / f"{document_id}.txt"
            if txt.exists():
                source_text = txt.read_text(encoding="utf-8")
                source_path = txt
            elif candidates:
                source_path = candidates[0]
                source_text = source_path.read_text(encoding="utf-8")
            else:
                raise FileNotFoundError(
                    f"Document {document_id!r} not found under {self.source_root}"
                )
            doc = DocumentState(
                document_id=document_id,
                source_path=source_path,
                source_text=source_text,
            )
            self._docs[document_id] = doc
            return doc

    def get_source(self, document_id: str) -> str:
        return self._doc(document_id).source_text

    def tag_span(
        self,
        document_id: str,
        start: int,
        end: int,
        element_path: str,
        attrs: Optional[Dict[str, str]] = None,
    ) -> Dict:
        doc = self._doc(document_id)
        if start < 0 or end > len(doc.source_text):
            raise ValueError(
                f"span [{start}, {end}) out of bounds for document of length "
                f"{len(doc.source_text)}"
            )
        if start > end:
            raise ValueError(f"start {start} > end {end}")

        local = element_path.rsplit("/", 1)[-1]
        if not local:
            raise ValueError(f"element_path {element_path!r} has empty local name")

        with self._lock:
            self._next_record_id += 1
            rec = TagRecord(
                start=start,
                end=end,
                element=local,
                element_path=element_path,
                attrs=dict(attrs or {}),
                record_id=f"r{self._next_record_id}",
            )
            doc.tags.append(rec)
        return rec.to_dict()

    def list_tags(self, document_id: str) -> List[Dict]:
        doc = self._doc(document_id)
        return [t.to_dict() for t in doc.tags]

    def reset(self, document_id: str) -> None:
        with self._lock:
            if document_id in self._docs:
                self._docs[document_id].tags = []

    def compose(
        self,
        document_id: str,
        wrap_in_body: bool = True,
        check_crossings: bool = True,
    ) -> str:
        """Emit final TEI by interleaving recorded tags with source text.

        If `wrap_in_body=True`, the result is a TEI <body> fragment.
        Otherwise, just the inner XML (tag soup over the source text).
        """
        doc = self._doc(document_id)
        text = doc.source_text
        tags = list(doc.tags)

        # Sort: ascending start, descending end (parents before children),
        # then by tag for determinism.
        tags.sort(key=lambda t: (t.start, -t.end, t.element))

        if check_crossings:
            stack: List[TagRecord] = []
            for t in tags:
                while stack and stack[-1].end <= t.start:
                    stack.pop()
                if stack and t.end > stack[-1].end:
                    raise ValueError(
                        f"Crossing tags: <{t.element}>[{t.start},{t.end}) crosses "
                        f"<{stack[-1].element}>[{stack[-1].start},{stack[-1].end})"
                    )
                stack.append(t)

        nsmap = {None: TEI_NS}
        if wrap_in_body:
            root = etree.Element(f"{TEI_PREFIX}body", nsmap=nsmap)
        else:
            root = etree.Element(f"{TEI_PREFIX}_compose_root", nsmap=nsmap)

        # Stack-based reconstruction: linear sweep through tags.
        stack_items: List[Tuple[int, etree._Element]] = [(len(text), root)]
        cursor = 0

        def attach(parent_elem, chunk: str):
            if not chunk:
                return
            if len(parent_elem):
                last = parent_elem[-1]
                last.tail = (last.tail or "") + chunk
            else:
                parent_elem.text = (parent_elem.text or "") + chunk

        for t in tags:
            # Close fully-ended siblings
            while len(stack_items) > 1 and stack_items[-1][0] <= t.start:
                close_off, close_elem = stack_items.pop()
                if cursor < close_off:
                    attach(close_elem, text[cursor:close_off])
                    cursor = close_off

            # Crossing detection (also caught by check_crossings above; double-check here)
            if t.end > stack_items[-1][0]:
                raise ValueError(
                    f"Crossing tag <{t.element}>[{t.start},{t.end}) at compose time"
                )

            # Emit text up to t.start in current parent
            if cursor < t.start:
                attach(stack_items[-1][1], text[cursor:t.start])
                cursor = t.start

            # Open new element
            new_elem = etree.SubElement(stack_items[-1][1], f"{TEI_PREFIX}{t.element}")
            for k, v in t.attrs.items():
                if k.startswith("xml:"):
                    new_elem.set(f"{XML_PREFIX}{k[4:]}", v)
                elif not k.startswith("{"):
                    new_elem.set(k, v)

            if t.start == t.end:
                # Zero-width annotation; close immediately.
                continue

            stack_items.append((t.end, new_elem))

        # Close remaining open elements
        while len(stack_items) > 1:
            close_off, close_elem = stack_items.pop()
            if cursor < close_off:
                attach(close_elem, text[cursor:close_off])
                cursor = close_off

        # Trailing text
        if cursor < len(text):
            attach(root, text[cursor:])

        # Verify body-text invariant: extracted text equals source
        rendered = etree.tostring(root, method="text", encoding="unicode")
        if rendered != text:
            # This should not happen if input was well-formed; raise loudly.
            raise RuntimeError(
                f"compose body-text invariant violated: rendered length "
                f"{len(rendered)} vs source length {len(text)}"
            )

        return etree.tostring(root, encoding="unicode")
