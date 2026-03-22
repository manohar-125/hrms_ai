import base64
import hashlib
import io
import logging
import math
import re

from app.vectordb.retriever import retrieve_documents
from app.embeddings.embedding_model import EmbeddingModel
from app.embeddings.chunking import chunk_text
from app.vectordb.chroma_client import get_hrms_collection
from app.services.hrms_api_client import fetch_policy_from_api, download_binary

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


logger = logging.getLogger(__name__)

collection = get_hrms_collection()

embedding_model = EmbeddingModel()


def _clean_policy_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]

    # Remove very short noisy lines and page markers.
    lines = [
        ln for ln in lines
        if len(ln) > 2 and not re.search(r"^page\s+\d+\s*(of\s+\d+)?$", ln.lower())
    ]

    # Remove repeated header/footer lines that appear too frequently.
    frequencies = {}
    for ln in lines:
        frequencies[ln] = frequencies.get(ln, 0) + 1
    repeated = {ln for ln, count in frequencies.items() if count >= 3 and len(ln) < 120}
    lines = [ln for ln in lines if ln not in repeated]

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _looks_like_pdf_url(value: str) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return (
        lowered.endswith(".pdf")
        or ".pdf?" in lowered
        or "application/pdf" in lowered
        or "drive.google.com" in lowered
        or "docs.google.com" in lowered
    )


def _normalize_pdf_url(value: str) -> str:
    if not isinstance(value, str):
        return ""

    url = value.strip()
    if not url:
        return ""

    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if match and "drive.google.com" in url.lower():
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    return url


def _decode_pdf_base64(value: str):
    if not isinstance(value, str):
        return None

    payload = value.strip()
    if payload.startswith("data:application/pdf;base64,"):
        payload = payload.split(",", 1)[1]

    # Common PDF base64 signature starts with JVBERi0
    if not payload.startswith("JVBERi0"):
        return None

    try:
        return base64.b64decode(payload, validate=False)
    except Exception:
        return None


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    text_parts = []

    # First attempt direct PDF text extraction (fast path).
    if PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)
        except Exception as exc:
            logger.warning("Direct PDF text extraction failed: %s", str(exc))

    extracted = _clean_policy_text("\n".join(text_parts))
    if len(extracted) >= 200:
        return extracted

    # OCR fallback when PDF text is scanned/non-readable.
    if fitz is None or pytesseract is None or Image is None:
        logger.warning("OCR dependencies missing; skipping OCR fallback")
        return extracted

    logger.info("OCR triggered for PDF policy document")
    ocr_parts = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            page_text = pytesseract.image_to_string(img)
            if page_text.strip():
                ocr_parts.append(page_text)
    except Exception as exc:
        logger.warning("OCR processing failed: %s", str(exc))
        return extracted

    return _clean_policy_text("\n".join(ocr_parts))


def _find_policy_title(item: dict) -> str:
    for key in ["policiesName", "title", "name", "policyName", "policyTitle", "documentName"]:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Company Policy"


def _find_readable_text(item: dict) -> str:
    candidates = [
        "content", "text", "description", "body", "policyText", "details", "summary"
    ]
    for key in candidates:
        value = item.get(key)
        if isinstance(value, str) and len(value.strip()) > 80:
            return _clean_policy_text(value)
    return ""


def _find_pdf_bytes(item: dict):
    direct_pdf = _extract_pdf_url(item)
    if direct_pdf:
        logger.info("PDF detected via uploadFiles field: %s", direct_pdf)
        return download_binary(direct_pdf)

    for key, value in item.items():
        if isinstance(value, str) and _looks_like_pdf_url(value):
            logger.info("PDF detected via URL for policy key '%s'", key)
            return download_binary(_normalize_pdf_url(value))

        if isinstance(value, (bytes, bytearray)) and value.startswith(b"%PDF"):
            logger.info("PDF detected via binary payload for policy key '%s'", key)
            return bytes(value)

        if isinstance(value, str):
            decoded = _decode_pdf_base64(value)
            if decoded and decoded.startswith(b"%PDF"):
                logger.info("PDF detected via base64 payload for policy key '%s'", key)
                return decoded

    return None


def _extract_pdf_url(item: dict) -> str:
    if not isinstance(item, dict):
        return ""

    for key in ["uploadFiles", "uploadFile", "fileUrl", "documentUrl", "url"]:
        value = item.get(key)

        if isinstance(value, str) and value.strip():
            normalized = _normalize_pdf_url(value)
            if _looks_like_pdf_url(normalized):
                return normalized

        if isinstance(value, list):
            for candidate in value:
                if isinstance(candidate, str) and candidate.strip():
                    normalized = _normalize_pdf_url(candidate)
                    if _looks_like_pdf_url(normalized):
                        return normalized

                if isinstance(candidate, dict):
                    nested_url = (
                        candidate.get("url")
                        or candidate.get("fileUrl")
                        or candidate.get("downloadUrl")
                    )
                    if isinstance(nested_url, str) and nested_url.strip():
                        normalized = _normalize_pdf_url(nested_url)
                        if _looks_like_pdf_url(normalized):
                            return normalized

        if isinstance(value, dict):
            nested_url = value.get("url") or value.get("fileUrl") or value.get("downloadUrl")
            if isinstance(nested_url, str) and nested_url.strip():
                normalized = _normalize_pdf_url(nested_url)
                if _looks_like_pdf_url(normalized):
                    return normalized

    return ""


def _iter_policy_items(payload):
    if payload is None:
        return []

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ["data", "items", "policies", "results"]:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return [payload]

    return [{"content": str(payload)}]


def _doc_exists(doc_id: str) -> bool:
    try:
        result = collection.get(ids=[doc_id], include=[])
        return bool(result.get("ids"))
    except Exception:
        return False


def _build_policy_doc_id(item: dict, title: str, pdf_url: str, index: int) -> str:
    stable_source = (
        (item.get("id") if isinstance(item, dict) else None)
        or (item.get("policiesId") if isinstance(item, dict) else None)
        or (item.get("policyId") if isinstance(item, dict) else None)
        or (item.get("policiesIds") if isinstance(item, dict) else None)
        or (item.get("documentId") if isinstance(item, dict) else None)
        or title
        or f"item_{index}"
    )
    signature = f"{stable_source}|{title}|{pdf_url}".lower()
    doc_hash = hashlib.sha1(signature.encode("utf-8")).hexdigest()
    return f"policy_{doc_hash}"


def _token_overlap_score(question: str, title: str) -> float:
    q_tokens = set(re.findall(r"[a-z0-9]+", question.lower()))
    t_tokens = set(re.findall(r"[a-z0-9]+", title.lower()))
    if not q_tokens or not t_tokens:
        return 0.0
    overlap = len(q_tokens.intersection(t_tokens))
    return overlap / max(len(t_tokens), 1)


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _extract_policy_candidates(payload):
    candidates = []
    for index, raw in enumerate(_iter_policy_items(payload)):
        if not isinstance(raw, dict):
            raw = {"content": str(raw)}

        # Skip deactivated policy records when API provides isActive.
        is_active = raw.get("isActive")
        if is_active is False:
            logger.info("Skipping inactive policy record at index %d", index)
            continue

        title = _find_policy_title(raw)
        pdf_url = _extract_pdf_url(raw)

        # Ignore placeholder or non-usable records (e.g. title="string", uploadFiles="string").
        normalized_title = title.strip().lower()
        if normalized_title in {"", "string", "null", "none", "n/a", "na"}:
            logger.info("Skipping non-usable policy title at index %d: '%s'", index, title)
            continue

        has_readable_text = bool(_find_readable_text(raw))
        has_pdf = bool(pdf_url)
        if not has_pdf and not has_readable_text:
            logger.info("Skipping policy '%s' because no PDF URL or readable text found", title)
            continue

        doc_id = _build_policy_doc_id(raw, title, pdf_url, index)
        candidates.append({
            "raw": raw,
            "title": title,
            "pdf_url": pdf_url,
            "doc_id": doc_id,
        })

    return candidates


def _match_best_policy(question: str, candidates: list[dict]):
    if not candidates:
        return None

    titles = [item["title"] for item in candidates]
    try:
        query_embedding = embedding_model.embed_text(question)
        title_embeddings = embedding_model.embed_documents(titles)
    except Exception as exc:
        logger.warning("Policy semantic matching fallback to lexical due to embedding error: %s", str(exc))
        query_embedding = []
        title_embeddings = [[] for _ in titles]

    best = None
    best_score = -1.0

    for candidate, title_embedding in zip(candidates, title_embeddings):
        semantic_score = _cosine_similarity(query_embedding, title_embedding)
        lexical_score = _token_overlap_score(question, candidate["title"])
        contains_bonus = 0.1 if candidate["title"].lower() in question.lower() else 0.0
        score = semantic_score + (0.2 * lexical_score) + contains_bonus

        if score > best_score:
            best_score = score
            best = candidate

    if best:
        logger.info("Best policy match: '%s' (score %.3f)", best["title"], best_score)

    return best


def _build_policy_text(policy_item: dict, title: str) -> str:
    text = _find_readable_text(policy_item)
    text_source = "api_text"

    if not text:
        pdf_bytes = _find_pdf_bytes(policy_item)
        if pdf_bytes:
            text = _extract_pdf_text(pdf_bytes)
            text_source = "pdf"

    if not text:
        text = _clean_policy_text(str(policy_item))
        text_source = "raw_fallback"

    if not text:
        logger.warning("No policy text extracted for '%s'", title)
        return ""

    logger.info(
        "Built policy text for '%s' from %s (chars=%d)",
        title,
        text_source,
        len(text),
    )

    return f"Title: {title}\n\nContent:\n{text}"


def _extract_policy_source(docs: list, metadatas: list) -> dict | None:
    """
    Extract policy source attribution from retrieved documents and their metadata.
    
    Returns:
        dict with keys: source_type, name, page_number (if available)
        or None if no metadata found
    """
    if not docs or not metadatas:
        return None
    
    # Use metadata from first document (most relevant)
    first_meta = metadatas[0] if metadatas else {}
    
    source = {
        "source_type": "policy",
        "name": first_meta.get("title", "Company Policy"),
        "page_number": first_meta.get("page_number"),
    }
    
    return source


def get_policy_context(question: str, return_source: bool = False):
    logger.info("[PolicyFlow] Incoming policy question: %s", question)

    # Step 1: Fetch policy list from API
    policy_payload = fetch_policy_from_api()

    if not policy_payload:
        logger.warning("[PolicyFlow] No policy payload received from API")
        if return_source:
            return [], None
        return []

    raw_items = _iter_policy_items(policy_payload)
    logger.info("[PolicyFlow] Policy records fetched: %d", len(raw_items))

    # Step 2: Match query to the most relevant policy name
    candidates = _extract_policy_candidates(policy_payload)
    logger.info("[PolicyFlow] Usable policy candidates: %d", len(candidates))
    selected = _match_best_policy(question, candidates)
    if not selected:
        logger.warning("[PolicyFlow] No matching policy candidate found")
        if return_source:
            return [], None
        return []

    doc_id = selected["doc_id"]
    title = selected["title"]
    logger.info(
        "[PolicyFlow] Selected policy: title='%s', doc_id='%s', pdf_url='%s'",
        title,
        doc_id,
        selected.get("pdf_url", ""),
    )

    # Step 3: Fast path - retrieve from existing embeddings for selected policy only
    logger.info("[PolicyFlow] Querying vector DB for existing chunks using doc_id='%s'", doc_id)
    retrieved = retrieve_documents(question, where={"doc_id": doc_id}, return_metadata=return_source)
    
    if return_source:
        documents, metadatas = retrieved
        source_meta = _extract_policy_source(documents, metadatas)
    else:
        documents = retrieved
        source_meta = None
    
    if documents:
        logger.info("[PolicyFlow] Vector DB HIT for doc_id='%s' (chunks=%d)", doc_id, len(documents))
        if return_source:
            return documents, source_meta
        return documents

    logger.info("[PolicyFlow] Vector DB MISS for doc_id='%s'; starting ingestion", doc_id)

    # Step 4: Build selected policy text (plain text or PDF extraction)
    policy_text = _build_policy_text(selected["raw"], title)
    if not policy_text:
        if return_source:
            return [], None
        return []

    chunks = chunk_text(policy_text)
    if not chunks:
        logger.warning("[PolicyFlow] Chunking produced no chunks for '%s'", title)
        if return_source:
            return [], None
        return []

    logger.info("[PolicyFlow] Chunking complete for '%s' (chunks=%d)", title, len(chunks))

    all_chunks = []
    all_embeddings = []
    all_ids = []
    all_metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}_chunk_{i}"
        if _doc_exists(chunk_id):
            continue

        vector = embedding_model.embed_text(chunk)
        all_chunks.append(chunk)
        all_embeddings.append(vector)
        all_ids.append(chunk_id)
        all_metadatas.append({"source": "policies_api", "title": title, "doc_id": doc_id})

    # Step 5: Store only new chunks for matched policy
    if all_chunks:
        collection.add(
            documents=all_chunks,
            embeddings=all_embeddings,
            ids=all_ids,
            metadatas=all_metadatas,
        )
        logger.info("embedding stored: %d new policy chunks for '%s'", len(all_chunks), title)
    else:
        logger.info("[PolicyFlow] No new chunks stored; all chunks already existed for '%s'", title)

    # Step 6: Retrieve for selected policy after indexing
    logger.info("[PolicyFlow] Retrieving chunks after ingestion for doc_id='%s'", doc_id)
    retrieved = retrieve_documents(question, where={"doc_id": doc_id}, return_metadata=return_source)
    
    if return_source:
        documents, metadatas = retrieved
        source_meta = _extract_policy_source(documents, metadatas)
        logger.info("[PolicyFlow] Final retrieved chunks for '%s': %d", title, len(documents))
        return documents, source_meta
    else:
        logger.info("[PolicyFlow] Final retrieved chunks for '%s': %d", title, len(retrieved))
        return retrieved