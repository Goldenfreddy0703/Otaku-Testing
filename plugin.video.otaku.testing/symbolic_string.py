import os

# Base directory (where this script is located)
base_dir = os.path.dirname(os.path.abspath(__file__))

# Source folder (real folder)
source_dir = os.path.join(base_dir, "resources", "language", "resource.language.en_gb")

# Destination folder (the symlink we want)
dest_parent = os.path.join(base_dir, "language")
dest_link = os.path.join(dest_parent, "resource.language.en_gb")

# Ensure parent directory exists
os.makedirs(dest_parent, exist_ok=True)

# Remove existing symlink/folder if it exists
if os.path.exists(dest_link) or os.path.islink(dest_link):
    try:
        if os.path.islink(dest_link):
            os.unlink(dest_link)
        else:
            import shutil
            shutil.rmtree(dest_link)
    except Exception as e:
        print(f"Failed to remove existing path: {e}")

# Try to create the symbolic link
try:
    os.symlink(source_dir, dest_link, target_is_directory=True)
    print(f"Symbolic link created:\n{dest_link} → {source_dir}")
except OSError as e:
    print(f"Failed to create symbolic link: {e}")
    if os.name == "nt":
        print("Tip: On Windows, you may need Administrator privileges or Developer Mode enabled.")
