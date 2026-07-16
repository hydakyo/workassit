# tests/unit/test_atomic_json.py
import pytest
from pathlib import Path
from app.utils.atomic_json import read_json, write_json_atomic

def test_write_and_read_json(tmp_path: Path):
    file_path = tmp_path / "test.json"
    data = {"key": "value", "num": 123}
    
    write_json_atomic(file_path, data)
    assert file_path.exists()
    
    read_data = read_json(file_path)
    assert read_data == data

def test_atomic_write_creates_backup(tmp_path: Path):
    file_path = tmp_path / "test.json"
    data1 = {"ver": 1}
    write_json_atomic(file_path, data1)
    
    data2 = {"ver": 2}
    write_json_atomic(file_path, data2)
    
    bak_path = file_path.with_suffix(".bak")
    assert bak_path.exists()
    
    bak_data = read_json(bak_path)
    assert bak_data == data1
    
    current_data = read_json(file_path)
    assert current_data == data2

def test_atomic_write_fails_on_invalid_data(tmp_path: Path):
    file_path = tmp_path / "test.json"
    # Not JSON serializable
    invalid_data = {"key": object()}
    
    with pytest.raises(TypeError):
        write_json_atomic(file_path, invalid_data)  # type: ignore
        
    assert not file_path.exists()
