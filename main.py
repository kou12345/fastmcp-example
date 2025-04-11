import uuid
import os  # os モジュールをインポート
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


# サーバー起動 (例)
# if __name__ == "__main__":
#     print(f"Allowed project directory: {ALLOWED_PROJECT_DIR}")
#     # mcp.run() # 実際のFastMCPサーバー起動処理
