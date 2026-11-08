"""Message language. This English edition retains both legacy language selectors."""
import os


def lang():
    return os.environ.get("WMLAB_LANG", "en").lower()


def tr(vi, en):
    return en if lang().startswith("en") else vi
