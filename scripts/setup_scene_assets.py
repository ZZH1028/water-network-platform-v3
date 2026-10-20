"""Install pinned Cesium browser assets locally, with npm artifact verification."""
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

VERSION = "1.121.0"
URL = f"https://registry.npmjs.org/cesium/-/cesium-{VERSION}.tgz"
INTEGRITY = "7zxptir4qvOK6lUi0T98a3PS51rYyBHDIk9uFXySb6sKtk4QkqVnDu0Y0Cm424BeuqLvJsQcOAvqwi6O1TSMqg=="
TARGET = Path(__file__).resolve().parents[1] / "static" / "cesium"


def install_assets(target: Path = TARGET) -> None:
    marker = target / ".version"
    if marker.is_file() and marker.read_text().strip() == VERSION:
        if (target / "Build/Cesium/Cesium.js").is_file():
            print(f"Cesium {VERSION} browser assets already installed")
            return
    if target.exists() and any(target.iterdir()):
        raise RuntimeError(f"Refusing to overwrite existing assets at {target}; inspect them first")
    request = urllib.request.Request(URL, headers={"User-Agent": "water-network-asset-installer/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        archive = response.read(80 * 1024 * 1024)
    actual = base64.b64encode(hashlib.sha512(archive).digest()).decode()
    if actual != INTEGRITY:
        raise RuntimeError("Cesium archive integrity check failed; assets were not installed")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cesium-", dir=target.parent) as staging:
        stage = Path(staging)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
            for member in package.getmembers():
                if not member.isfile():
                    continue
                name = member.name.removeprefix("package/")
                if not (name.startswith("Build/Cesium/") or name in ("LICENSE.md", "ThirdParty.extra.json")):
                    continue
                destination = stage / name
                if not destination.resolve().is_relative_to(stage.resolve()):
                    raise RuntimeError("Unsafe archive member")
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = package.extractfile(member)
                if source is None:
                    raise RuntimeError("Missing archive member")
                with source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
        if not (stage / "Build/Cesium/Cesium.js").is_file():
            raise RuntimeError("Cesium browser bundle missing")
        (stage / ".version").write_text(VERSION + "\n")
        if target.exists():
            target.rmdir()
        shutil.move(str(stage), str(target))
    print(f"Installed verified Cesium {VERSION} assets in {target}")


if __name__ == "__main__":
    install_assets()
