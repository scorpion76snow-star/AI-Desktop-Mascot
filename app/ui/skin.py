# -*- coding: utf-8 -*-
"""Per-user skin loading: pet image and optional QSS."""

import os

from app.core.config import ASSETS_DIR, SKINS_DIR


def skin_root(settings):
    name = settings.get("skin", "default") or "default"
    return os.path.join(SKINS_DIR, name)


def pet_image(settings):
    root = skin_root(settings)
    for path in (os.path.join(root, "pet.png"),
                 os.path.join(root, "pet.jpg"),
                 os.path.join(ASSETS_DIR, "default_skin", "pet.png")):
        if os.path.exists(path):
            return path
    return None


def style_sheet(settings):
    root = skin_root(settings)
    for path in (os.path.join(root, "style.qss"),
                 os.path.join(ASSETS_DIR, "default_skin", "style.qss")):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except OSError:
                pass
    return ""
