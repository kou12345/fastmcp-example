import pytest
import os
from pathlib import Path

# main モジュールをインポート (main.py がカレントディレクトリにある想定)
# 必要に応じて sys.path を調整するか、プロジェクト構造に合わせたインポート方法に変更してください
try:
    import main
except ImportError:
    # 例: プロジェクトルートからの実行などを考慮
    import sys

    # ここでは仮に現在のワークスペースルートをパスに追加
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
    try:
        import main
    except ImportError:
        print("Error: Could not import main module. Make sure main.py is accessible.")
        # テスト実行を中止するなど、より適切なエラー処理が必要な場合がある
        raise

# --- Pytest Fixtures ---


# テスト全体で main.ALLOWED_PROJECT_DIR を一時ディレクトリに設定するフィクスチャ
@pytest.fixture(autouse=True)
def setup_allowed_dir(tmp_path: Path, monkeypatch):
    """Sets the ALLOWED_PROJECT_DIR in the main module to the pytest tmp_path for testing."""
    # main モジュール内の ALLOWED_PROJECT_DIR をモンキーパッチで上書き
    monkeypatch.setattr(main, "ALLOWED_PROJECT_DIR", str(tmp_path), raising=False)
    # is_path_allowed が内部でこれを参照するため、テストは tmp_path 内で完結する
    # raising=False は ALLOWED_PROJECT_DIR が main に存在しない場合のエラーを防ぐ（存在すべきだが念のため）


# --- Test Cases for list_directory ---


def test_list_directory_success(tmp_path: Path):
    """Tests listing a directory with files and subdirectories."""
    # Setup: Create test files and a subdirectory
    (tmp_path / "file_a.txt").touch()
    (tmp_path / "script.py").touch()
    (tmp_path / "subdir1").mkdir()
    expected_items = sorted(
        ["file_a.txt", "script.py", "subdir1"]
    )  # Sort for reliable comparison

    # Action: Call the function under test
    result = main.list_directory(str(tmp_path))

    # Assertion: Check if the result is a list and contains the expected items
    assert isinstance(result, list)
    assert sorted(result) == expected_items


def test_list_directory_subdir_success(tmp_path: Path):
    """Tests listing a subdirectory."""
    # Setup: Create a subdirectory and a file within it
    subdir_path = tmp_path / "data"
    subdir_path.mkdir()
    (subdir_path / "config.json").touch()
    expected_items = ["config.json"]

    # Action: Call the function for the subdirectory
    result = main.list_directory(str(subdir_path))

    # Assertion: Check the result
    assert isinstance(result, list)
    assert result == expected_items  # Only one item, no need to sort


def test_list_directory_empty(tmp_path: Path):
    """Tests listing an empty directory."""
    # Setup: Create an empty subdirectory
    empty_dir_path = tmp_path / "empty_folder"
    empty_dir_path.mkdir()
    expected_items = []

    # Action: Call the function for the empty directory
    result = main.list_directory(str(empty_dir_path))

    # Assertion: Check if the result is an empty list
    assert isinstance(result, list)
    assert result == expected_items


def test_list_directory_not_found(tmp_path: Path):
    """Tests listing a non-existent directory."""
    # Setup: Define path for a directory that doesn't exist
    non_existent_path = tmp_path / "i_do_not_exist"

    # Action: Call the function
    result = main.list_directory(str(non_existent_path))

    # Assertion: Check if the result is an error string indicating 'not found'
    assert isinstance(result, str)
    assert "Error: Directory not found" in result


def test_list_directory_is_file(tmp_path: Path):
    """Tests attempting to list a file path instead of a directory."""
    # Setup: Create a file
    file_path = tmp_path / "my_document.txt"
    file_path.touch()

    # Action: Call the function with the file path
    result = main.list_directory(str(file_path))

    # Assertion: Check if the result is an error string indicating 'not a directory'
    assert isinstance(result, str)
    assert "is not a directory" in result


def test_list_directory_outside_allowed(tmp_path: Path):
    """Tests attempting to list a directory outside the allowed project directory."""
    # Action: Attempt to list the parent directory of tmp_path (which is outside ALLOWED_PROJECT_DIR)
    # Note: This assumes tmp_path is not the root directory itself.
    # Using a well-known path like /tmp might be more stable depending on the environment.
    outside_path = tmp_path.parent
    # Ensure we don't accidentally test the root '/' if tmp_path is '/private/var/...'
    if str(outside_path) == "/":
        pytest.skip("Cannot reliably test parent dir when tmp_path is near root")

    result = main.list_directory(str(outside_path))

    # Assertion: Check if the result is an error string indicating 'Access denied'
    assert isinstance(result, str)
    assert "Error: Access denied" in result
    assert "outside the project directory" in result


def test_list_directory_permission_error(tmp_path: Path, monkeypatch):
    """Tests the behavior when os.listdir raises a PermissionError."""

    # Setup: Mock os.listdir to raise PermissionError
    def mock_listdir_permission(path):
        raise PermissionError(f"Simulated permission denied for {path}")

    monkeypatch.setattr(os, "listdir", mock_listdir_permission)

    # Action: Call the function (it should catch the mocked PermissionError)
    result = main.list_directory(str(tmp_path))

    # Assertion: Check if the result is an error string indicating 'Permission denied'
    assert isinstance(result, str)
    assert "Error: Permission denied" in result


# You can add more tests here for other edge cases if needed
# e.g., paths with special characters, very long paths (if relevant), etc.
