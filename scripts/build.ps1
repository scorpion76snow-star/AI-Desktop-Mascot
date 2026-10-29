$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$piperData = python -c "import piper, os; print(os.path.dirname(piper.__file__))"

python -m PyInstaller --noconfirm --clean --onedir --windowed --name YunPet `
  --paths . `
  --hidden-import app.model.local.service `
  --hidden-import app.model.local.gated_lm `
  --hidden-import app.model.openai_backend `
  --hidden-import app.chat.render `
  --hidden-import app.chat.factcheck `
  --hidden-import app.chat.guard `
  --hidden-import piper --hidden-import piper.voice --hidden-import piper.config `
  --hidden-import piper.phonemize_espeak --hidden-import piper.phoneme_ids `
  --hidden-import piper.espeakbridge `
  --hidden-import pyttsx3 --hidden-import sounddevice --hidden-import soundfile `
  --hidden-import onnxruntime `
  --add-data "$piperData\espeak-ng-data;piper\espeak-ng-data" `
  --exclude-module matplotlib --exclude-module pandas --exclude-module scipy `
  --exclude-module transformers --exclude-module torchvision --exclude-module torchaudio `
  --exclude-module numba --exclude-module llvmlite --exclude-module pyarrow `
  --exclude-module pytest --exclude-module sklearn --exclude-module tensorflow `
  --exclude-module datasets --exclude-module bitsandbytes --exclude-module librosa `
  --distpath dist --workpath build --specpath build app\main.py

$dist = Join-Path (Get-Location) "dist\YunPet"
New-Item -ItemType Directory -Force (Join-Path $dist "models\local"), (Join-Path $dist "voices") | Out-Null
Copy-Item "models\local\sft_best.pt", "models\local\tokenizer.json" (Join-Path $dist "models\local") -Force
if (Test-Path "voices\voice_zh_huayan.onnx") {
  Copy-Item "voices\*" (Join-Path $dist "voices") -Force
}
Write-Host "Built $dist"
