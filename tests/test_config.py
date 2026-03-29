from pathlib import Path

from changescout.config import load_yaml


def test_load_yaml_returns_dict(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.yaml"
    file_path.write_text("key: value\n", encoding="utf-8")

    data = load_yaml(file_path)

    assert data == {"key": "value"}
