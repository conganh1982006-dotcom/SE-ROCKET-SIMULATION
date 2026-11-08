"""Build a ZIP without environments/caches; preserve generated evidence."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    root = Path(__file__).resolve().parents[1]
    destination = root.parent/"c5_rocket_v3_1_english.zip"
    excluded = {"__pycache__", ".pytest_cache", ".venv", ".git", "build"}
    with ZipFile(destination, "w", ZIP_DEFLATED) as zipfile:
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.name.startswith("~$") and not any(x in excluded or x.endswith('.egg-info') for x in path.relative_to(root).parts):
                zipfile.write(path, Path(root.name)/path.relative_to(root))
    print(destination)


if __name__ == "__main__": main()
