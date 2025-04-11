import uuid
import os  # os モジュールをインポート
import glob  # glob モジュールをインポート
from fastmcp import FastMCP

# --- セキュリティ設定 ---
# このプロジェクトのルートディレクトリを許可する
# os.path.abspath を使って絶対パスを取得し、正規化する
ALLOWED_PROJECT_DIR = os.path.abspath("/Users/koichiro-hira/workspace/fastmcp-example")

if not os.path.isdir(ALLOWED_PROJECT_DIR):
    # 起動時にディレクトリが存在しない場合はエラーなど、適切な処理を検討
    print(f"Warning: Allowed project directory '{ALLOWED_PROJECT_DIR}' does not exist.")
    # raise Exception(f"Allowed project directory '{ALLOWED_PROJECT_DIR}' not found.") # 必要なら例外を送出


def is_path_allowed(file_path: str) -> bool:
    """指定されたパスがプロジェクトディレクトリ内にあるか検証する"""
    try:
        # 対象パスを絶対パスに変換し、シンボリックリンクを解決
        abs_path = os.path.realpath(os.path.abspath(file_path))

        # ALLOWED_PROJECT_DIR 自体のパスも許可する
        if abs_path == ALLOWED_PROJECT_DIR:
            return True

        # 指定されたパスが許可されたディレクトリで始まっているかチェック
        # ディレクトリ区切り文字を追加して、部分一致を防ぐ (例: /allowed/dir と /allowed/dir_extra)
        if abs_path.startswith(ALLOWED_PROJECT_DIR + os.sep):
            # ディレクトリトラバーサル(../)が含まれていないかチェック
            # os.path.relpath は ValueError を出す可能性があるので try-except で囲む
            try:
                relative_path = os.path.relpath(abs_path, ALLOWED_PROJECT_DIR)
                if ".." in relative_path.split(os.sep):
                    print(
                        f"Warning: Path traversal attempt detected in '{file_path}' -> '{abs_path}'"
                    )
                    return False
            except ValueError:
                # Windows でドライブが異なる場合などに発生しうる
                print(
                    f"Warning: Could not determine relative path for '{abs_path}' relative to '{ALLOWED_PROJECT_DIR}'"
                )
                return False
            return True
    except Exception as e:
        # パス解決中の予期せぬエラー
        print(f"Error validating path '{file_path}': {e}")
        return False
    return False


# -----------------------------


# Create an MCP server
mcp = FastMCP("Demo")


@mcp.tool()
def get_uuid() -> str:
    """Get a UUID"""
    return str(uuid.uuid4())


# localのファイルをreadする
@mcp.tool()
def read_local_file(file_path: str) -> str:
    """Read a local file within the allowed project directory."""
    if not is_path_allowed(file_path):
        return f"Error: Access denied. Reading from '{file_path}' is not allowed or outside the project directory."
    try:
        # セキュリティチェックを通ったので、絶対パスでファイルを開く
        abs_file_path = os.path.abspath(file_path)
        with open(abs_file_path, "r", encoding="utf-8") as f:  # encodingを指定
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found at '{file_path}'."
    except PermissionError:
        return f"Error: Permission denied when trying to read '{file_path}'."
    except Exception as e:
        # UnicodeDecodeErrorなどもここで捕捉される
        return f"Error reading file '{file_path}': {e}"


# localのファイルにwriteする
@mcp.tool()
def write_local_file(file_path: str, content: str) -> str:
    """Write content to a local file within the allowed project directory. Overwrites existing file."""
    if not is_path_allowed(file_path):
        return f"Error: Access denied. Writing to '{file_path}' is not allowed or outside the project directory."

    try:
        abs_file_path = os.path.abspath(file_path)
        # 親ディレクトリが存在するか確認し、なければ作成する
        parent_dir = os.path.dirname(abs_file_path)

        # 作成しようとしている親ディレクトリも許可範囲内かチェック
        # is_path_allowed はファイル/ディレクトリ両方を想定してチェックするため、そのまま使える
        if not is_path_allowed(parent_dir):
            # is_path_allowed で ALLOWED_PROJECT_DIR 自体は許可されるはず
            return f"Error: Cannot create directory '{parent_dir}' as it is outside the allowed project directory."

        # ディレクトリ作成 (存在していてもエラーにならない)
        # ここで権限エラーが発生する可能性もある
        os.makedirs(parent_dir, exist_ok=True)

        # ファイル書き込み
        with open(abs_file_path, "w", encoding="utf-8") as f:  # encodingを指定
            f.write(content)
        return f"Successfully wrote to file '{file_path}'."
    except PermissionError:
        # ディレクトリ作成 or ファイル書き込み時の権限エラー
        return f"Error: Permission denied when trying to write to '{file_path}' or create its parent directory."
    except Exception as e:
        return f"Error writing to file '{file_path}': {e}"


# ディレクトリ一覧表示
@mcp.tool()
def list_directory(dir_path: str) -> list[str] | str:
    """List files and directories directly under the specified directory path within the allowed project directory.

    Args:
        dir_path: The path to the directory to list.

    Returns:
        A list of file and directory names, or an error message string.
    """
    if not is_path_allowed(dir_path):
        return f"Error: Access denied. Listing directory '{dir_path}' is not allowed or outside the project directory."

    try:
        abs_dir_path = os.path.abspath(dir_path)

        if not os.path.exists(abs_dir_path):
            return f"Error: Directory not found at '{dir_path}'."

        if not os.path.isdir(abs_dir_path):
            return f"Error: The path '{dir_path}' is not a directory."

        # os.listdir() は権限がない場合 PermissionError を送出する
        contents = os.listdir(abs_dir_path)
        return contents

    except PermissionError:
        return f"Error: Permission denied when trying to list directory '{dir_path}'."
    except Exception as e:
        return f"Error listing directory '{dir_path}': {e}"


# ファイルパターン検索
@mcp.tool()
def find_files_by_pattern(
    base_dir: str, pattern: str, recursive: bool = False
) -> list[str] | str:
    """Find files or directories matching a pattern within the allowed project directory.

    Args:
        base_dir: The base directory to start the search from.
        pattern: The glob pattern to match (e.g., '*.txt', 'data/**/').
        recursive: If True, search recursively into subdirectories. Uses '**' in glob.

    Returns:
        A list of matching file/directory paths relative to the project root,
        or an error message string.
    """
    if not is_path_allowed(base_dir):
        return f"Error: Access denied. Searching in '{base_dir}' is not allowed or outside the project directory."

    try:
        abs_base_dir = os.path.abspath(base_dir)

        if not os.path.exists(abs_base_dir):
            return f"Error: Base directory not found at '{base_dir}'."

        if not os.path.isdir(abs_base_dir):
            return f"Error: The base path '{base_dir}' is not a directory."

        # globパターンを結合
        # recursive=True の場合、'**/' をパターンに追加して再帰的に検索
        # os.path.join は / で終わる場合、正しく結合してくれる
        search_pattern = (
            os.path.join(abs_base_dir, "**", pattern)
            if recursive
            else os.path.join(abs_base_dir, pattern)
        )

        # glob.glob は絶対パスを返す
        # recursive=True を glob に渡す必要がある
        matched_paths_abs = glob.glob(search_pattern, recursive=recursive)

        allowed_paths = []
        for path_abs in matched_paths_abs:
            # 念のため、globの結果が許可範囲内か再度チェック
            # is_path_allowed は絶対パスで評価する
            if is_path_allowed(path_abs):
                # 結果はプロジェクトルートからの相対パスで返す方が使いやすい場合がある
                # ここでは絶対パスのまま返すか、相対パスに変換するか選択可能
                # 例: 相対パスにする場合
                try:
                    rel_path = os.path.relpath(path_abs, ALLOWED_PROJECT_DIR)
                    # Windowsでは `./` が先頭につかないことがあるため補完
                    if not rel_path.startswith((".", "..")):
                        rel_path = "." + os.sep + rel_path
                    allowed_paths.append(rel_path)
                except ValueError:
                    # ALLOWED_PROJECT_DIR と異なるドライブなどの場合 (通常は起こらないはず)
                    # その場合は絶対パスのまま追加するなどのフォールバックも可能
                    allowed_paths.append(path_abs)
                    print(
                        f"Warning: Could not create relative path for {path_abs}. Returning absolute path."
                    )

        return allowed_paths

    except PermissionError:
        return f"Error: Permission denied during search in '{base_dir}'."
    except Exception as e:
        return f"Error finding files with pattern '{pattern}' in '{base_dir}': {e}"


# サーバー起動 (例)
# if __name__ == "__main__":
#     print(f"Allowed project directory: {ALLOWED_PROJECT_DIR}")
#     # mcp.run() # 実際のFastMCPサーバー起動処理
