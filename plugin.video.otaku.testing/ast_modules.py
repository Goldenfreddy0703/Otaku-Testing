import os
import ast
import json
import shutil

# -----------------------------
# SETTINGS
# -----------------------------
ADDON_PATH = r"C:\Users\jenki\Desktop\Kodi 21 Joezito\portable_data\addons\plugin.video.otaku.testing"
JSON_FILE = "lazy_modules.json"
BACKUP_DIR = os.path.join(ADDON_PATH, "backup_lazy_ast")

# -----------------------------
# Load lazy module names
# -----------------------------
with open(JSON_FILE, "r", encoding="utf-8") as f:
    lazy_data = json.load(f)

# List of top-level module names to replace
MODULE_NAMES = {entry["name"] for entry in lazy_data}

# -----------------------------
# AST Transformer
# -----------------------------
class ControlPrefixTransformer(ast.NodeTransformer):
    def visit_Name(self, node):
        # Replace top-level names with control.<name> if in MODULE_NAMES
        if node.id in MODULE_NAMES:
            return ast.Attribute(
                value=ast.Name(id='control', ctx=ast.Load()),
                attr=node.id,
                ctx=node.ctx
            )
        return node

# -----------------------------
# Process files
# -----------------------------
def process_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception as e:
        print(f"[SKIP] {file_path} ({e})")
        return

    transformer = ControlPrefixTransformer()
    new_tree = transformer.visit(tree)
    new_source = ast.unparse(new_tree)

    # Backup original file
    rel_path = os.path.relpath(file_path, ADDON_PATH)
    backup_path = os.path.join(BACKUP_DIR, rel_path)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(file_path, backup_path)

    # Write new file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_source)
    print(f"[UPDATED] {file_path}")

# -----------------------------
# Walk addon directory
# -----------------------------
def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for root, _, files in os.walk(ADDON_PATH):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                process_file(file_path)

if __name__ == "__main__":
    main()
