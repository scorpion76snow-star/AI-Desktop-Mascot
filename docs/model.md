# Model setup

## Local GatedLM

Place:

```text
models\local\sft_best.pt
models\local\tokenizer.json
```

then select `local` in Settings → Model.

## OpenAI-compatible API

Settings → Model:

- profile: `openai`
- Base URL: `https://api.openai.com/v1`
- model: e.g. `gpt-4o-mini`
- API key: saved in Windows Credential Manager as `YunPet/openai`

The app uses `/chat/completions`. The API key is never written into the
repository or `config.json`.

## Language

The active UI language is appended to the system prompt:

- English → always answer in English
- Chinese → 始终用中文回答

English mode also rejects CJK model output at the quality gate and uses an
English fallback.
