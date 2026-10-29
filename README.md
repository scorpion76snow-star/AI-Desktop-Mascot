# AI-Desktop-Mascot
This is a desktop pet with built-in AI that can help you reply to emails, schedule appointments, and handle daily chats.

# Creator's reminder
I'm a first-year computer science student currently studying in the UK, which limits my time to fully perfect this desktop pet. The reason I created it is because Outlook is always flooded with emails, a problem I believe most people face, so I looked for a solution. The software supports English and Chinese by default. If anyone wants code optimization or wants to contact me, I will try to reply as quickly as possible. The software does not use AI in the following areas: some basic code, basic testing (few, as I'm working alone), all ideas, and designing and training text filtering. AI is used in the following areas: code optimization, packaging, uploading, and implementation of some functions.
Because of the heavy academic workload, some AI was used in the presentation.
Some features of this model are not yet complete. I will optimize and add these features later, depending on when the learning will be easier.

# Introduction
YunPet is a Windows desktop pet and local-priority personal assistant application.
The white square pet is always on your desktop; clicking it displays your recent to-do list. It includes a built-in calendar, to-do list, notepad, chat, email drafts, and voice reminders. It supports switching between Chinese and English, using local models or OpenAI, and allows you to change skins and voices. The application name is also customizable.
The model character's name is Xiaoyun/Yun, and the default application name is YunPet, which can be changed in the settings.

# 1. Desktop Pet
A white square that remains on the Windows desktop, default size 80x80.
Draggable, position is saved automatically.
Click to display recent to-do bubbles.
Tray Menu:
Open Workbench
Chat
Show/Hide Desktop Pet
Sound Alert
Exit
Single Instance Protection: Repeated startup will prompt that a desktop pet is already running.

# 2. Workbench
Calendar
Monthly Calendar View
Select a date to view today's schedule
Create, edit, delete schedules
Schedule fields: Title, Start, End, Location, Notes
To-Do
Create, edit, complete/cancel, delete
Priority: High / Medium / Low
Due date, Notes
Clicking the desktop pet displays recently unfinished to-dos
Notepad
Create, edit, delete notes
Local SQLite storage
Pending Send
Display draft list
The sending process only begins when the user clicks "Allow Sending"
Automatic sending is not enabled by default
Settings
App Name
Language switch entry
Model: local / OpenAI
Skin
Voice switch, volume, preview, open voice catalog
Email Account
Do Not Disturb Time Period

# 3. Chat
Multi-turn chat, retaining recent context
Context budget approximately 760 tokens, last 6 turns + summary
Chat history can be viewed, individual conversations can be deleted, and the entire chat can be cleared
Rule routing: Schedules/to-dos/events use structured answers
Daily/emotional/boundary issues use deterministic templates
Transfers/high-risk content are routed to human moderators
Promotions/ads are ignored
Quality gate:
Known bad sentences are blocked
Topic mismatch is blocked
Duplicate replies are blocked
Chinese replies in English interface are blocked
Blocked replies are not written to the chat history
In English interface, even if the user inputs Chinese, English is output first

# 4. Chinese/English Switch

Default Language: English There are Chinese/English buttons in the upper right corner of the workbench and the upper right corner of the chat window.

The application restarts after switching, and the interface, model, and voice change together.

Chinese:
Interface Chinese
Template Chinese
Schedule/To-Do Chinese
Chinese Female Voice

English:
Interface English
Template English
Schedule/To-Do English
Model System Requirements English
English Female Voice

# 5. Model

Local Model
Currently 48M GatedLM

Default Production Weights:

models/local/sft_best.pt

models/local/tokenizer.json
Supports GPU/CPU
No internet connection required, suitable for privacy scenarios

OpenAI
Select OpenAI in settings

Configurable:

Base URL
Model Name

API Key
API Key stored in Windows Credential Manager
Does not write to configuration files or the repository
When using OpenAI, only the current context is sent; full calendar/to-do data is not sent.

# 6. Voice

Default off, user must enable

Chinese: Piper Huayan, default 10% slower

English: Piper Alba, default original speed

Failure rollback (Windows SAPI)
Chat, email alerts, and desktop pet/to-do list can be toggled separately

New replies can interrupt the previous paragraph
Automatic deduplication of the same sentence to avoid repetitive reading
Third-party voices are placed in voices/

Configurable:
Model path
Configuration path
Chinese/English speech speed

# 7. Skins / Appearances

Default is a white square

Supports replacing appearances with pet.png

Supports adjusting interface styles with style.qss

Skin Catalog:
%APPDATA%\YunPet\skins\<皮肤名>\
  pet.png
  style.qss
Automatically reverts to the white square when no image is displayed. The settings page allows access to the skin catalog.

# 8. Application Name
Default: YunPet
Editable in settings
Xiaoyun is the model name, not the application name. The workbench title and tray notification use the application name. The chat window title updates after reopening/restarting.

# 9. Email
Supports multiple email account lists
Reserved Gmail/Outlook Provider API
Read-only by default
Sending requires explicit user approval
Currently, there is no built-in real OAuth or real sending functionality.

# 10. Privacy
No telemetry
Calendar, to-dos, notes, and chat history are all local SQLite
Settings are local JSON
OpenAI only connects to the internet when switched to OpenAI mode
Third-party speech models are not distributed with the repository

# Incomplete sections:

# A. Email Loop
Gmail OAuth not implemented
Outlook OAuth not implemented
Real email retrieval not implemented
Real email sending not implemented
"Allow Sending" is currently only in the interface and storage, not yet integrated with the real Provider's send function.
Multiple accounts only have a list and client_id field, no token management.

# B. Scheduled Reminder Loop
Calendar/To-Do list lacks scheduled reminders.
Currently, voice notifications only cover:
Chat replies
New email notifications
Clicking on a desktop pet to-do
No "10-minute reminder before meeting"
No persistent background reminder service.

# C. Model Ecosystem
Currently only:
Local GatedLM
One OpenAI compatible configuration
No list for saving/switching multiple model configurations
No model downloader
No model file selection UI
OpenAI lacks:
Streaming output
Tool calling
Retry/backoff
Token usage statistics
Multiple Provider plugins
No RAG/Vector memory
Chat cannot directly create/modify calendars and to-dos, only query and draft text.

# D. Language
Language switching takes effect upon application restart, not instant refresh.
The main interface, chat, tray icon, settings, and edit pop-ups are now in English.
A few system MessageBoxes and email provider errors, and dynamic text in the history list may still be in Chinese.
No translation files/translation platforms are integrated.

# E. Skins/UI
Only static pet.png and style.qss are supported.
No animations, emoticons, actions, or click feedback.
No real-time skin reloading; a restart is required after modification.
No skin editor.
No multi-skin management UI; only skin names can be entered.
The tray icon is still a code-generated white block and does not follow the skin.
Application icon/install icon has not been replaced.

# F. Voice
Third-party voice license issues remain unresolved; voices are not included in public repositories by default.
No voice downloader/installer.
No voice file selection UI; configuration changes or file replacement with the same name are required.
No voice preview list.
No voice cloning.
No lip-sync.
Disabled by default; users need to prepare their own voices upon first use.

# G. Packaging/Release
Only a Windows one-dir package.
Approximately 4.38 GB, primarily from CUDA. PyTorch: No installer, no code signing, no automatic updates, no CPU-only packages, no CI builds, and the dist entry doesn't go to GitHub.

# H. Testing
Currently only 5 basic unit tests
No UI automation tests
No OpenAI real interface tests
No voice playback integration tests
No multi-language full regression tests
No long-run/memory tests

# I. Public Release
Missing screenshots, demo GIFs, and videos
Missing Roadmap
Missing Issue templates and contribution guidelines
Missing version number and CHANGELOG
Model weights use Git LFS, but users need to install LFS first
The code is MIT, but the licenses for model weights and third-party voices need to be declared separately
No explanation of which data will be sent to a separate OpenAI page

# J. Other
No cloud synchronization
No data encryption
No multi-user/permission system
No auto-start on boot
No crash logs/diagnostic panel
After changing the application name, the chat window and system tray prompt that a restart is required for full synchronization.

# The 3 most important points to note
Voice recording is disabled by default; third-party voice recordings are not included in the repository, and users are responsible for verifying their own licenses.
The code is MIT (Made in Taiwan); the model weights and voice model are independent works and require separate licensing.
OpenAI mode sends the current chat context to the configured interface; the default local mode is not connected to the internet.
