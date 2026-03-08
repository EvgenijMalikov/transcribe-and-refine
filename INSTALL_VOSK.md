# Installing a Vosk Model

## Option 1: Use the helper script

This is the easiest setup path on Windows:

```powershell
.\download_vosk_model.ps1 en full
.\download_vosk_model.ps1 ru full
.\download_vosk_model.ps1 zh full
```

The script creates the correct folder layout automatically:

```text
vosk-model/
  en/
  ru/
  zh/
```

## Option 2: Install a model manually

### 1. Download a model

Browse the official Vosk model list:

- https://alphacephei.com/vosk/models

Example English model:

- `vosk-model-en-us-0.22`

Example Russian model:

- `vosk-model-ru-0.42`

### 2. Extract it into the project

The app expects models in language-specific directories:

```text
transcribe-and-refine/
├── vosk-model/
│   ├── en/
│   │   ├── am/
│   │   ├── conf/
│   │   ├── graph/
│   │   └── ...
│   └── ru/
│       ├── am/
│       ├── conf/
│       ├── graph/
│       └── ...
├── app.py
└── ...
```

### 3. Verify the structure

Each language folder should contain standard Vosk model files such as:

- `am/`
- `conf/`
- `graph/`
- `ivector/`

## PowerShell example for manual installation

```powershell
Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip" -OutFile "vosk-model.zip"
Expand-Archive -Path "vosk-model.zip" -DestinationPath "."
Move-Item -Path "vosk-model-en-us-0.22" -Destination "vosk-model\en"
Remove-Item "vosk-model.zip"
```

## Custom model paths

If you want to use a custom location, pass the path explicitly:

```python
transcriber = VoskTranscriber(model_path="path/to/your/model")
```

## Notes

- Vosk models are usually large; install only the languages you need
- The models work offline after download
- Full models usually provide better quality than small ones
