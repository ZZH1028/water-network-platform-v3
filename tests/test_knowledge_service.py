from pathlib import Path
import io
import json
import sqlite3
import zipfile

import pytest

from services import knowledge_service as knowledge


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'knowledge.db'
    knowledge.initialize_knowledge_base(path, seed=False)
    return path


def test_chinese_and_english_retrieval_preserves_sources(db):
    first = knowledge.import_document('tidal.md', '# 感潮河网\n\n潮汐边界影响河网水位，防洪需校核高程基准。'.encode(),
                                      title='感潮河网边界', source_url='https://tidesandcurrents.noaa.gov/', db_path=db)
    knowledge.import_document('guide.txt', b'Upload CSV data using the import form.', title='Data import manual', db_path=db)
    chinese = knowledge.search_knowledge('潮汐边界与高程基准', db_path=db)
    assert chinese[0]['document_id'] == first['id']
    assert chinese[0]['source_url'] == 'https://tidesandcurrents.noaa.gov/'
    assert chinese[0]['citation'] == 1
    assert '高程基准' in chinese[0]['text']
    assert knowledge.search_knowledge('upload CSV', db_path=db)[0]['title'] == 'Data import manual'
    assert knowledge.search_knowledge('quantumquark', db_path=db) == []


def test_import_is_idempotent_and_original_bytes_retained(db):
    content = '河网水位监测质量控制'.encode()
    result = knowledge.import_document('../../station.txt', content, db_path=db)
    again = knowledge.import_document('renamed.txt', content, db_path=db)
    assert result['id'] == again['id']
    assert again['duplicate'] is True
    assert result['filename'] == 'station.txt'
    assert 'stored_path' not in result
    files = list((db.parent / 'files').glob('*.txt'))
    assert len(files) == 1 and files[0].read_bytes() == content
    assert knowledge.knowledge_statistics(db)['document_count'] == 1


def test_delete_removes_source_and_search_chunks(db):
    item = knowledge.import_document('source.txt', '闸泵调度约束需要审核'.encode(), db_path=db)
    assert knowledge.search_knowledge('闸泵调度', db_path=db)
    assert knowledge.delete_document(item['id'], db)
    assert not knowledge.delete_document(item['id'], db)
    assert knowledge.search_knowledge('闸泵调度', db_path=db) == []
    assert knowledge.knowledge_statistics(db)['chunk_count'] == 0
    assert list((db.parent / 'files').glob('*')) == []


def test_seed_guides_are_honest_idempotent_and_not_deletable(db):
    first = knowledge.initialize_knowledge_base(db)
    second = knowledge.initialize_knowledge_base(db)
    assert first == second
    assert first['document_count'] >= 6
    assert first['seed_count'] == first['document_count']
    sources = knowledge.search_knowledge('如何导入水位数据 CSV', db_path=db)
    assert sources[0]['source_type'] == 'operation_manual'
    with pytest.raises(ValueError, match='内置'):
        knowledge.delete_document(knowledge.list_documents(db)[0]['id'], db)
    assert not any(doc['filename'].lower() == 'readme.md' for doc in knowledge.list_documents(db))


@pytest.mark.parametrize('filename,content,match', [
    ('empty.txt', b'', '文件为空'),
    ('bad.exe', b'not executable', '支持导入'),
    ('bad.txt', b'\xff\xfe\xff', 'UTF-8'),
    ('bad.json', b'{oops', '文件格式'),
    ('bad.docx', b'not a zip', '文件格式'),
    ('bad.pdf', b'not a PDF', '解析失败'),
])
def test_invalid_upload_does_not_create_document(db, filename, content, match):
    with pytest.raises(ValueError, match=match):
        knowledge.import_document(filename, content, db_path=db)
    assert knowledge.knowledge_statistics(db)['document_count'] == 0


def test_size_limit_and_source_url_validation(db, monkeypatch):
    monkeypatch.setattr(knowledge, 'MAX_FILE_BYTES', 8)
    with pytest.raises(ValueError, match='20 MB'):
        knowledge.import_document('large.txt', b'123456789', db_path=db)
    for url in ('javascript:alert(1)', 'https://secret:password@example.com/source'):
        with pytest.raises(ValueError, match='来源链接'):
            knowledge.import_document('x.txt', b'valid', source_url=url, db_path=db)


def test_csv_json_and_docx_are_searchable(db):
    knowledge.import_document('series.csv', '站点,水位\nA01,3.6'.encode(), db_path=db)
    knowledge.import_document('config.json', json.dumps({'boundary': 'tidalforecast'}).encode(), db_path=db)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('word/document.xml', '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>感潮河网闸门操作指导</w:t></w:r></w:p></w:body></w:document>')
    knowledge.import_document('guide.docx', buffer.getvalue(), db_path=db)
    assert knowledge.search_knowledge('水位', db_path=db)
    assert knowledge.search_knowledge('tidalforecast', db_path=db)
    assert knowledge.search_knowledge('闸门操作指导', db_path=db)[0]['filename'] == 'guide.docx'


def _text_pdf():
    stream = b'BT /F1 12 Tf 72 720 Td (Tidal boundary forecast reference) Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    data = b'%PDF-1.4\n'
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(number).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    start = len(data)
    data += b'xref\n0 6\n0000000000 65535 f \n'
    for offset in offsets[1:]:
        data += f'{offset:010d} 00000 n \n'.encode()
    data += b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(start).encode()+b'\n%%EOF\n'
    return data


def test_pdf_extracts_page_number_and_text(db):
    knowledge.import_document('paper.pdf', _text_pdf(), db_path=db)
    source = knowledge.search_knowledge('Tidal boundary', db_path=db)[0]
    assert source['page'] == 1
    assert 'Tidal boundary forecast reference' in source['text']


def test_search_handles_fts_expression_input_and_limit(db):
    knowledge.import_document('source.md', ('河网水位潮汐边界。\n\n'*150).encode(), db_path=db)
    assert len(knowledge.search_knowledge('河网 OR " * : \"', limit=1, db_path=db)) == 1
    assert knowledge.search_knowledge('', db_path=db) == []
    with pytest.raises(ValueError, match='4000'):
        knowledge.search_knowledge('河'*4001, db_path=db)


def test_retrieval_falls_back_when_fts_table_is_unavailable(db, monkeypatch):
    knowledge.import_document('source.txt', '潮汐影响河网水位，需要核对上下游边界。'.encode(), db_path=db)
    monkeypatch.setattr(knowledge, '_fts_available', lambda conn: False)
    assert knowledge.search_knowledge('河网水位', db_path=db)


def test_public_retrieval_and_statistics_exclude_uploaded_documents(db):
    knowledge.initialize_knowledge_base(db)
    uploaded = knowledge.import_document('restricted.txt', 'restrictedmaterialunique tide calibration'.encode(), db_path=db)
    assert knowledge.search_knowledge('restrictedmaterialunique', db_path=db)[0]['document_id'] == uploaded['id']
    assert knowledge.search_knowledge('restrictedmaterialunique', db_path=db, include_uploaded=False) == []
    assert all(item['is_seed'] for item in knowledge.list_documents(db, include_uploaded=False))
    public_stats = knowledge.knowledge_statistics(db, include_uploaded=False)
    assert public_stats['uploaded_count'] == 0
    assert public_stats['document_count'] == public_stats['seed_count']


def test_revised_seed_replaces_older_searchable_version(db, tmp_path, monkeypatch):
    seed_dir = tmp_path / 'seedroot' / 'data' / 'knowledge'
    seed_dir.mkdir(parents=True)
    guide = seed_dir / 'manual.md'
    guide.write_text('# Manual\nSource-Type: operation_manual\n\noldoperationuniqueword', encoding='utf-8')
    monkeypatch.setattr(knowledge, 'BASE_DIR', seed_dir.parents[1])
    knowledge.initialize_knowledge_base(db)
    assert knowledge.search_knowledge('oldoperationuniqueword', db_path=db)
    guide.write_text('# Manual\nSource-Type: operation_manual\n\nnewoperationuniqueword', encoding='utf-8')
    knowledge.initialize_knowledge_base(db)
    assert knowledge.search_knowledge('oldoperationuniqueword', db_path=db) == []
    assert knowledge.search_knowledge('newoperationuniqueword', db_path=db)
    assert knowledge.knowledge_statistics(db)['document_count'] == 1
