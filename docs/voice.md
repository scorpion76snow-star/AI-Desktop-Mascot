# Voice setup

Voice is disabled by default.

## Piper

Put your own `.onnx` + `.json` pair in `voices\`, then set the paths in
`%APPDATA%\YunPet\config.json`:

```json
{
  "voice_enabled": true,
  "voice_chat_enabled": true,
  "voice_zh_model": "voice_zh_huayan.onnx",
  "voice_zh_config": "voice_zh_huayan.json",
  "voice_en_model": "voice_en_alba.onnx",
  "voice_en_config": "voice_en_alba.json",
  "voice_zh_length_scale": 1.1,
  "voice_en_length_scale": 1.0
}
```

Paths may be absolute or relative to `voices\`.

## License warning

Piper voice models have their own licenses. This repository does not distribute
third-party voice models. Do not commit `voices\*.onnx` unless you have checked
the license and have permission to redistribute it.

## Windows SAPI fallback

If Piper is unavailable, the app can use Windows SAPI through `pyttsx3`. This
uses the installed Windows voice and does not bundle a third-party model.
