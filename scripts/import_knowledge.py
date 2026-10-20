"""Batch-index a local professional document collection without model training."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.knowledge_service import SUPPORTED_EXTENSIONS, MAX_FILE_BYTES, import_document, initialize_knowledge_base


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='批量导入有权共享给平台登录用户的专业资料。')
    parser.add_argument('path', type=Path, help='文件或资料目录')
    parser.add_argument('--recursive', action='store_true', help='包含子目录')
    parser.add_argument('--db', type=Path, help='可选知识库数据库路径')
    parser.add_argument('--uploaded-by', default='资料管理员')
    parser.add_argument('--source-url', default='', help='本批资料公开来源链接（可选）')
    args = parser.parse_args(argv)
    if not args.path.exists():
        parser.error('资料路径不存在')
    if args.path.is_file():
        files = [args.path]
    else:
        files = sorted(args.path.rglob('*') if args.recursive else args.path.iterdir())
    files = [path for path in files if path.is_file() and not path.name.startswith('.') and path.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not files:
        parser.error('没有找到支持的 TXT / MD / CSV / JSON / PDF / DOCX 文件')
    initialize_knowledge_base(db_path=args.db)
    imported = duplicate = failed = 0
    for path in files:
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise ValueError('单份资料超过 20 MB')
            result = import_document(path.name, path.read_bytes(), source_url=args.source_url,
                                     uploaded_by=args.uploaded_by, db_path=args.db)
            if result['duplicate']:
                duplicate += 1
                print(f'重复，已保留原索引：{path.name}')
            else:
                imported += 1
                print(f'已索引：{path.name} · {result["chunk_count"]} 个片段')
        except (ValueError, OSError) as exc:
            failed += 1
            print(f'导入失败：{path.name} · {exc}', file=sys.stderr)
    print(f'完成：新增 {imported}，重复 {duplicate}，失败 {failed}。资料供登录用户检索。')
    return int(failed > 0)


if __name__ == '__main__':
    raise SystemExit(main())
