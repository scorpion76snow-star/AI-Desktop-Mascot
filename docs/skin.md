# Skin setup

The default pet is a white square. To use an image, create:

```text
%APPDATA%\YunPet\skins\<name>\
  pet.png
  style.qss
```

Set the skin name in Settings → UI / Pet, or in `config.json`:

```json
{"skin": "<name>"}
```

Restart the app after changing the skin.

- `pet.png` is drawn at 80×80.
- `style.qss` is optional and applies to the workspace/chat.
- Missing files fall back to the built-in white square and default style.
