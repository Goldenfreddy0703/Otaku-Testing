import os
import ast
import re
import json as pyjson

# -----------------------------
# SETTINGS
# -----------------------------
ADDON_PATH = r"C:\Users\jenki\Desktop\Kodi 21 Joezito\portable_data\addons\plugin.video.otaku.testing"
LAZY_MODULE_TEMPLATE = '{name} = LazyModule(lambda: __import__("{module_path}"{fromlist}))'
OUTPUT_JSON = "lazy_modules.json"

# -----------------------------
# FUNCTIONS (same as before)
# -----------------------------
def find_classes_in_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception:
        return []
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

def file_to_module_path(addon_path, filepath):
    rel = os.path.relpath(filepath, addon_path)
    rel = rel.replace(os.sep, ".")
    if rel.endswith(".py"):
        rel = rel[:-3]
    if rel.endswith("__init__"):
        rel = rel[:-9]
    return rel

def scan_addon_for_classes(addon_path):
    classes = []
    modules = set()
    for root, _, files in os.walk(addon_path):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                module_path = file_to_module_path(addon_path, path)
                modules.add(module_path)
                file_classes = find_classes_in_file(path)
                for cls in file_classes:
                    classes.append((cls, module_path))
    return modules, classes

def scan_addon_for_imports(addon_path):
    import_pattern = re.compile(r'^\s*(import|from)\s+([^\s]+)')
    found_imports = set()
    for root, _, files in os.walk(addon_path):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        for line in f:
                            match = import_pattern.match(line)
                            if match:
                                mod = match.group(2).split('.')[0]
                                found_imports.add(mod)
                except Exception:
                    continue
    return found_imports

def generate_lazy_imports(modules, classes, extra_modules):
    output_lines = []
    output_data = []

    # Extra modules
    for mod in sorted(extra_modules):
        line = LAZY_MODULE_TEMPLATE.format(name=mod, module_path=mod, fromlist="")
        output_lines.append(line)
        output_data.append({"name": mod, "module_path": mod, "fromlist": []})

    # Addon modules
    for mod in sorted(modules):
        name = mod.split(".")[-1]
        line = LAZY_MODULE_TEMPLATE.format(name=name, module_path=mod, fromlist="")
        output_lines.append(line)
        output_data.append({"name": name, "module_path": mod, "fromlist": []})

    # Classes
    for cls_name, mod_path in sorted(classes):
        line = LAZY_MODULE_TEMPLATE.format(name=cls_name, module_path=mod_path, fromlist=f', fromlist=["{cls_name}"]')
        output_lines.append(line)
        output_data.append({"name": cls_name, "module_path": mod_path, "fromlist": [cls_name]})

    return output_lines, output_data

# -----------------------------
# MAIN
# -----------------------------
def main():
    addon_modules, addon_classes = scan_addon_for_classes(ADDON_PATH)
    imported_modules = scan_addon_for_imports(ADDON_PATH)

    lazy_lines, lazy_data = generate_lazy_imports(addon_modules, addon_classes, imported_modules)

    print("# ===== AUTO-GENERATED LAZY MODULES =====\n")
    print("from resources.lib.ui.control import LazyModule\n")
    for line in lazy_lines:
        print(line)

    # Save JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        pyjson.dump(lazy_data, f, indent=4)
    print(f"\n[INFO] Lazy module data saved to {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
