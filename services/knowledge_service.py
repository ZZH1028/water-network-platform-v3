"""Local, source-preserving document ingestion and Chinese/English retrieval.

Documents are indexed for retrieval; importing a document does not train a model.
No embedding service or network connection is needed by this module.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sqlite3
from typing import Iterator
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import zipfile

from core.config import BASE_DIR

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TEXT_CHARACTERS = 2_000_000
MAX_DOCUMENTS = 1000
SUPPORTED_EXTENSIONS = {'.txt', '.md', '.csv', '.json', '.pdf', '.docx'}
SOURCE_TYPES = {'uploaded', 'reference_overview', 'operation_manual', 'reference'}
_STOPWORDS = {'什么', '如何', '怎么', '可以', '这个', '那个', '一个', '以及', '关于', '进行', '需要', '问题', 'the', 'and', 'how', 'what', 'with', 'for'}


def _db_path(db_path: str | Path | None = None) -> Path:
    path = Path(db_path or os.getenv('KNOWLEDGE_DB_PATH') or BASE_DIR / 'storage' / 'knowledge' / 'knowledge.db')
    return path.expanduser().resolve()


@contextmanager
def _connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    path = _db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=20000')
    try:
        _create_schema(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, filename TEXT NOT NULL, source_url TEXT NOT NULL,
            source_type TEXT NOT NULL, content_hash TEXT NOT NULL UNIQUE,
            byte_size INTEGER NOT NULL, uploaded_by TEXT NOT NULL,
            created_at TEXT NOT NULL, stored_path TEXT NOT NULL,
            is_seed INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL, page INTEGER,
            section TEXT NOT NULL, text TEXT NOT NULL, search_terms TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document ON knowledge_chunks(document_id);
    ''')
    # The standard CPython SQLite build includes FTS5. A deterministic BM25
    # fallback below also supports builds without this optional extension.
    try:
        conn.execute('CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(search_terms, chunk_id UNINDEXED)')
    except sqlite3.OperationalError:
        pass


def _fts_available(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='knowledge_fts'").fetchone() is not None


def _tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for word in re.findall(r'[a-zA-Z][a-zA-Z0-9_.-]*|[\u3400-\u9fff]+|\d+(?:\.\d+)?', text.lower()):
        if re.fullmatch(r'[\u3400-\u9fff]+', word):
            tokens.extend(word[i:i+2] for i in range(len(word)-1))
            if len(word) == 1:
                tokens.append(word)
        else:
            tokens.append(word)
    return [token for token in tokens if token not in _STOPWORDS]


def _safe_filename(filename: str) -> str:
    cleaned = Path(str(filename).replace('\\', '/')).name
    cleaned = re.sub(r'[\x00-\x1f\x7f]', '', cleaned).strip()[:180]
    if not cleaned or cleaned in {'.', '..'}:
        raise ValueError('请提供有效文件名。')
    return cleaned


def _source_url(value: str) -> str:
    value = str(value or '').strip()
    if not value:
        return ''
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('资料来源链接须为不含账号密码的 HTTP/HTTPS 地址。')
    if len(value) > 2000:
        raise ValueError('资料来源链接过长。')
    return value


def _extract_pages(filename: str, content: bytes) -> list[tuple[int | None, str]]:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == '.pdf':
            try:
                from pypdf import PdfReader
            except ImportError as exc:
                raise ValueError('PDF 解析依赖尚未安装，请安装 requirements.txt 中的 pypdf。') from exc
            reader = PdfReader(io.BytesIO(content), strict=True)
            if reader.is_encrypted and not reader.decrypt(''):
                raise ValueError('暂不支持带密码的 PDF，请先导出无密码文本版。')
            if len(reader.pages) > 500:
                raise ValueError('单份 PDF 最多支持 500 页，请拆分后导入。')
            pages = []
            count = 0
            for number, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ''
                count += len(text)
                if count > MAX_TEXT_CHARACTERS:
                    raise ValueError('提取文字超过 200 万字，请拆分后导入。')
                pages.append((number, text))
            if not any(text.strip() for _, text in pages):
                raise ValueError('PDF 中没有可提取文字。扫描件需先进行 OCR 后再导入。')
            return pages
        if suffix == '.docx':
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                entries = archive.infolist()
                if sum(item.file_size for item in entries) > 100 * 1024 * 1024:
                    raise ValueError('DOCX 解压内容过大，请拆分文件。')
                info = archive.getinfo('word/document.xml')
                if info.file_size > MAX_FILE_BYTES:
                    raise ValueError('DOCX 正文过大，请拆分文件。')
                tree = ET.fromstring(archive.read(info))
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            text = '\n'.join(''.join(p.itertext()) for p in tree.findall('.//w:p', ns))
        else:
            text = content.decode('utf-8-sig')
            if suffix == '.json':
                text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
            elif suffix == '.csv':
                rows = csv.reader(io.StringIO(text))
                text = '\n'.join(' | '.join(row) for row in rows)
        if len(text) > MAX_TEXT_CHARACTERS:
            raise ValueError('提取文字超过 200 万字，请拆分后导入。')
        if not text.strip():
            raise ValueError('文件没有可检索的文字。')
        return [(None, text)]
    except UnicodeDecodeError as exc:
        raise ValueError('文本文件请使用 UTF-8 编码保存后再导入。') from exc
    except (json.JSONDecodeError, zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError('文件格式损坏或与扩展名不一致，请检查后重试。') from exc
    except ValueError:
        raise
    except Exception as exc:
        # Parser exceptions can contain machine paths; expose a stable message.
        raise ValueError('文件解析失败，请确认文件有效，或转成 UTF-8 文本后导入。') from exc


def _chunks(pages: list[tuple[int | None, str]], title: str) -> list[dict]:
    result = []
    section = title
    for page, raw in pages:
        raw = raw.replace('\x00', '').replace('\r\n', '\n')
        paragraphs = re.split(r'\n\s*\n|(?<=。)\n|(?<=；)\n', raw)
        buffer = ''
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            heading = re.match(r'^#{1,6}\s+([^\n]+)', paragraph)
            if heading:
                if buffer:
                    result.append({'page': page, 'section': section, 'text': buffer})
                    buffer = ''
                section = heading.group(1).strip()[:180]
            if buffer and len(buffer) + len(paragraph) > 1000:
                result.append({'page': page, 'section': section, 'text': buffer})
                buffer = buffer[-120:] + '\n\n'
            while len(paragraph) > 1000:
                cut = max(paragraph.rfind('。', 550, 1000), paragraph.rfind('\n', 550, 1000))
                cut = cut+1 if cut >= 550 else 900
                if buffer:
                    result.append({'page': page, 'section': section, 'text': buffer})
                    buffer = ''
                result.append({'page': page, 'section': section, 'text': paragraph[:cut]})
                paragraph = paragraph[max(1, cut-100):]
            buffer = (buffer + '\n\n' + paragraph).strip()
        if buffer:
            result.append({'page': page, 'section': section, 'text': buffer})
    return result


def _document_dict(row: sqlite3.Row | dict) -> dict:
    item = dict(row)
    item.pop('stored_path', None)
    item.pop('content_hash', None)
    item['is_seed'] = bool(item.get('is_seed'))
    return item


def import_document(
    filename: str, content: bytes, *, title: str | None = None,
    source_url: str = '', source_type: str = 'uploaded', uploaded_by: str = '用户',
    db_path: str | Path | None = None, storage_dir: str | Path | None = None,
    _is_seed: bool = False,
) -> dict:
    """Store a local copy and index extracted text, deduplicated by SHA-256.

    Callers must enforce the application's management roles before importing.
    ``_is_seed`` is reserved for initialize_knowledge_base.
    """
    filename = _safe_filename(filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError('支持导入 TXT、Markdown、CSV、JSON、PDF 和 DOCX 文件。')
    if not isinstance(content, bytes):
        raise ValueError('请提供文件的二进制内容。')
    if not content:
        raise ValueError('文件为空。')
    if len(content) > MAX_FILE_BYTES:
        raise ValueError('单份资料不能超过 20 MB。')
    if source_type not in SOURCE_TYPES:
        raise ValueError('资料类型不受支持。')
    url = _source_url(source_url)
    title = str(title or Path(filename).stem).strip()[:240]
    if not title:
        raise ValueError('资料标题不能为空。')
    digest = hashlib.sha256(content).hexdigest()
    with _connection(db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        existing = conn.execute('''SELECT d.*, count(c.id) AS chunk_count FROM knowledge_documents d
            LEFT JOIN knowledge_chunks c ON c.document_id=d.id WHERE content_hash=? GROUP BY d.id''', (digest,)).fetchone()
        if existing:
            if _is_seed:
                conn.execute('''UPDATE knowledge_documents SET title=?,filename=?,source_url=?,source_type=?,is_seed=1
                    WHERE id=?''', (title, filename, url, source_type, existing['id']))
                existing = conn.execute('''SELECT d.*, count(c.id) AS chunk_count FROM knowledge_documents d
                    LEFT JOIN knowledge_chunks c ON c.document_id=d.id WHERE d.id=? GROUP BY d.id''', (existing['id'],)).fetchone()
            return {**_document_dict(existing), 'duplicate': True}
        count = conn.execute('SELECT count(*) FROM knowledge_documents').fetchone()[0]
        if count >= MAX_DOCUMENTS:
            raise ValueError('知识库已达到 1000 份资料上限，请整理资料后再导入。')
        pages = _extract_pages(filename, content)
        chunks = _chunks(pages, title)
        if not chunks:
            raise ValueError('文件没有可检索的文字。')
        folder = Path(storage_dir).resolve() if storage_dir else _db_path(db_path).parent / 'files'
        folder.mkdir(parents=True, exist_ok=True)
        stored = folder / f'{digest}{suffix}'
        # Content-addressed names prevent uploaded paths and collisions.
        stored.write_bytes(content)
        cursor = conn.execute('''INSERT INTO knowledge_documents
            (title,filename,source_url,source_type,content_hash,byte_size,uploaded_by,created_at,stored_path,is_seed)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (title, filename, url, source_type, digest, len(content), str(uploaded_by)[:120],
             datetime.now(timezone.utc).isoformat(timespec='seconds'), str(stored), int(_is_seed)))
        document_id = cursor.lastrowid
        fts = _fts_available(conn)
        for index, chunk in enumerate(chunks):
            terms = ' '.join(_tokens(title + '\n' + chunk['section'] + '\n' + chunk['text']))
            c = conn.execute('''INSERT INTO knowledge_chunks
                (document_id,chunk_index,page,section,text,search_terms) VALUES (?,?,?,?,?,?)''',
                (document_id, index, chunk['page'], chunk['section'], chunk['text'], terms))
            if fts:
                conn.execute('INSERT INTO knowledge_fts(search_terms,chunk_id) VALUES (?,?)', (terms, c.lastrowid))
        row = conn.execute('SELECT * FROM knowledge_documents WHERE id=?', (document_id,)).fetchone()
        return {**_document_dict(row), 'chunk_count': len(chunks), 'duplicate': False}


def initialize_knowledge_base(db_path: str | Path | None = None, seed: bool = True) -> dict:
    with _connection(db_path):
        pass
    if seed:
        for path in sorted((BASE_DIR / 'data' / 'knowledge').glob('*.md')):
            if path.name.lower() == 'readme.md':
                continue
            text = path.read_text(encoding='utf-8-sig')
            title = re.search(r'^#\s+(.+)$', text, flags=re.MULTILINE)
            stype = re.search(r'^Source-Type:\s*(\S+)', text, flags=re.MULTILINE)
            url = re.search(r'^Source-URL:\s*(\S+)', text, flags=re.MULTILINE)
            current = import_document(path.name, path.read_bytes(), title=title.group(1) if title else path.stem,
                                      source_type=stype.group(1) if stype else 'reference_overview',
                                      source_url=url.group(1) if url else '', uploaded_by='平台内置导读',
                                      db_path=db_path, _is_seed=True)
            # A tracked guide can be revised between releases. Keep only its
            # current seed version so old instructions do not remain searchable.
            stale_files = []
            with _connection(db_path) as conn:
                stale = conn.execute('SELECT id,stored_path,content_hash,filename FROM knowledge_documents WHERE is_seed=1 AND filename=? AND id<>?',
                                     (path.name, current['id'])).fetchall()
                for row in stale:
                    if _fts_available(conn):
                        conn.execute('DELETE FROM knowledge_fts WHERE chunk_id IN (SELECT id FROM knowledge_chunks WHERE document_id=?)', (row['id'],))
                    conn.execute('DELETE FROM knowledge_documents WHERE id=?', (row['id'],))
                    stored = Path(row['stored_path'])
                    if stored.name == row['content_hash'] + Path(row['filename']).suffix.lower():
                        stale_files.append(stored)
            for stored in stale_files:
                stored.unlink(missing_ok=True)
    return knowledge_statistics(db_path)


def list_documents(db_path: str | Path | None = None, *, include_uploaded: bool = True) -> list[dict]:
    with _connection(db_path) as conn:
        rows = conn.execute('''SELECT d.*, count(c.id) AS chunk_count FROM knowledge_documents d
            LEFT JOIN knowledge_chunks c ON c.document_id=d.id'''
            + ('' if include_uploaded else ' WHERE d.is_seed=1')
            + ' GROUP BY d.id ORDER BY d.created_at DESC,d.id DESC').fetchall()
    return [_document_dict(row) for row in rows]


def knowledge_statistics(db_path: str | Path | None = None, *, include_uploaded: bool = True) -> dict:
    with _connection(db_path) as conn:
        row = conn.execute('''SELECT count(*) AS document_count,coalesce(sum(is_seed),0) AS seed_count,
            coalesce(sum(byte_size),0) AS byte_size FROM knowledge_documents'''
            + ('' if include_uploaded else ' WHERE is_seed=1')).fetchone()
        chunks = conn.execute('''SELECT count(*) FROM knowledge_chunks c
            JOIN knowledge_documents d ON d.id=c.document_id'''
            + ('' if include_uploaded else ' WHERE d.is_seed=1')).fetchone()[0]
    return {**dict(row), 'uploaded_count': row['document_count'] - row['seed_count'], 'chunk_count': chunks}


def delete_document(document_id: int, db_path: str | Path | None = None) -> bool:
    """Delete an uploaded source and its chunks. Built-in guides are retained."""
    with _connection(db_path) as conn:
        row = conn.execute('SELECT * FROM knowledge_documents WHERE id=?', (int(document_id),)).fetchone()
        if not row:
            return False
        if row['is_seed']:
            raise ValueError('内置导读与操作手册不能在界面删除，可在代码资料目录维护。')
        if _fts_available(conn):
            conn.execute('DELETE FROM knowledge_fts WHERE chunk_id IN (SELECT id FROM knowledge_chunks WHERE document_id=?)', (int(document_id),))
        conn.execute('DELETE FROM knowledge_documents WHERE id=?', (int(document_id),))
        path = Path(row['stored_path'])
        # Only remove our exact content-addressed file, never an arbitrary path.
        if path.name == row['content_hash'] + Path(row['filename']).suffix.lower():
            path.unlink(missing_ok=True)
        return True


def search_knowledge(query: str, limit: int = 6, db_path: str | Path | None = None, *,
                     include_uploaded: bool = True) -> list[dict]:
    query = str(query).strip()
    if not query:
        return []
    if len(query) > 4000:
        raise ValueError('检索问题请控制在 4000 字以内。')
    limit = max(1, min(int(limit), 20))
    tokens = list(dict.fromkeys(_tokens(query)))[:70]
    if not tokens:
        return []
    with _connection(db_path) as conn:
        select = '''SELECT c.*,d.title,d.filename,d.source_url,d.source_type,d.is_seed
                    FROM knowledge_chunks c JOIN knowledge_documents d ON d.id=c.document_id'''
        if _fts_available(conn):
            match = ' OR '.join('"'+t.replace('"','""')+'"' for t in tokens)
            rows = conn.execute(select + ''' JOIN knowledge_fts f ON f.chunk_id=c.id
                 WHERE knowledge_fts MATCH ?'''
                 + ('' if include_uploaded else ' AND d.is_seed=1')
                 + ' ORDER BY bm25(knowledge_fts) LIMIT 250', (match,)).fetchall()
        else:
            rows = conn.execute(select + ('' if include_uploaded else ' WHERE d.is_seed=1')).fetchall()
        if not rows:
            return []
        lengths = [len(row['search_terms'].split()) for row in rows]
        average = sum(lengths) / len(rows) or 1
        counters = [Counter(row['search_terms'].split()) for row in rows]
        document_freq = {t: sum(t in counter for counter in counters) for t in tokens}
        ranked = []
        for row, counter, length in zip(rows, counters, lengths):
            matched = [t for t in tokens if counter[t]]
            if not matched:
                continue
            score = 0.0
            for token in matched:
                idf = math.log(1 + (len(rows)-document_freq[token]+.5)/(document_freq[token]+.5))
                frequency = counter[token]
                score += idf * frequency*2.2/(frequency + 1.2*(.25+.75*length/average))
            coverage = len(matched) / len(tokens)
            score *= 1+coverage
            title_tokens = set(_tokens(row['title'] + ' ' + row['section']))
            score += .3 * sum(t in title_tokens for t in matched)
            item = {key: row[key] for key in ('document_id','title','filename','source_url','source_type','chunk_index','page','section','text')}
            item.update({'score': round(score, 4), 'url': row['source_url'], 'is_seed': bool(row['is_seed'])})
            ranked.append((score, item))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]['document_id'], pair[1]['chunk_index']))
    # Diversify sources without excluding a second relevant passage.
    selected: list[dict] = []
    counts: Counter = Counter()
    for _, item in ranked:
        if counts[item['document_id']] >= 2:
            continue
        item['citation'] = len(selected)+1
        selected.append(item)
        counts[item['document_id']] += 1
        if len(selected) >= limit:
            break
    return selected
