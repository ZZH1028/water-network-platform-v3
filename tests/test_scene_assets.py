import base64
import hashlib
import io
import tarfile

import pytest

from scripts import setup_scene_assets as assets


def archive_with_files(files):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as archive:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return data.getvalue()


def configure_download(monkeypatch, data, *, valid=True):
    monkeypatch.setattr(assets.urllib.request, 'urlopen', lambda *args, **kwargs: io.BytesIO(data))
    digest = base64.b64encode(hashlib.sha512(data).digest()).decode()
    monkeypatch.setattr(assets, 'INTEGRITY', digest if valid else 'invalid-integrity')


def test_verified_assets_install_and_repeat_without_network(tmp_path, monkeypatch):
    data = archive_with_files({'package/Build/Cesium/Cesium.js': b'window.Cesium={};',
                               'package/LICENSE.md': b'License', 'package/other.txt': b'not copied'})
    configure_download(monkeypatch, data)
    target = tmp_path/'cesium'
    assets.install_assets(target)
    assert (target/'Build/Cesium/Cesium.js').read_bytes() == b'window.Cesium={};'
    assert (target/'LICENSE.md').read_text() == 'License'
    assert not (target/'other.txt').exists()
    monkeypatch.setattr(assets.urllib.request, 'urlopen', lambda *args, **kwargs: pytest.fail('cached assets fetched again'))
    assets.install_assets(target)


def test_bad_integrity_never_installs_assets(tmp_path, monkeypatch):
    configure_download(monkeypatch, b'corrupted package', valid=False)
    with pytest.raises(RuntimeError, match='integrity'):
        assets.install_assets(tmp_path/'cesium')
    assert not (tmp_path/'cesium').exists()


def test_archive_traversal_cannot_write_outside_target(tmp_path, monkeypatch):
    data = archive_with_files({'package/Build/Cesium/../../../escaped.js': b'bad'})
    configure_download(monkeypatch, data)
    with pytest.raises(RuntimeError, match='Unsafe archive'):
        assets.install_assets(tmp_path/'cesium')
    assert not (tmp_path/'escaped.js').exists()


def test_existing_unknown_assets_are_preserved(tmp_path):
    target=tmp_path/'cesium'
    target.mkdir()
    (target/'user.txt').write_text('keep')
    with pytest.raises(RuntimeError, match='Refusing to overwrite'):
        assets.install_assets(target)
    assert (target/'user.txt').read_text() == 'keep'
