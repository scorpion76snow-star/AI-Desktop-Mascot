# Privacy

- No telemetry or analytics.
- Calendar, to-do, notes, drafts, and chat history are stored locally in
  `%APPDATA%\YunPet\yunpet.db`.
- Settings are stored in `%APPDATA%\YunPet\config.json`.
- OpenAI is contacted only when the OpenAI model profile is active.
- API keys are stored in Windows Credential Manager, not in the repository.
- Never commit `%APPDATA%\YunPet`, `.db` files, `.env`, or API keys.
