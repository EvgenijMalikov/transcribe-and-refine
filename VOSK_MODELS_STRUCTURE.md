# Vosk Model Structure for Multi-Language Support

## Expected directory layout

```text
vosk-model/
├── ru/
│   ├── am/
│   ├── conf/
│   ├── graph/
│   └── ...
├── en/
│   ├── am/
│   ├── conf/
│   ├── graph/
│   └── ...
├── es/
├── fr/
├── de/
└── zh/
```

Each language lives in its own subdirectory under `vosk-model/`.

## Recommended models

| Language | Model | Size | Link |
|------|--------|--------|--------|
| English | `vosk-model-en-us-0.22` | 1.8 GB | [Download](https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip) |
| Russian | `vosk-model-ru-0.42` | 1.8 GB | [Download](https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip) |
| Spanish | `vosk-model-es-0.42` | 1.4 GB | [Download](https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip) |
| French | `vosk-model-fr-0.22` | 1.4 GB | [Download](https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip) |
| German | `vosk-model-de-0.21` | 1.8 GB | [Download](https://alphacephei.com/vosk/models/vosk-model-de-0.21.zip) |
| Chinese | `vosk-model-cn-0.22` | 1.2 GB | [Download](https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip) |

## Automatic installation

Use the helper script when possible:

```powershell
.\download_vosk_model.ps1 en full
.\download_vosk_model.ps1 ru full
.\download_vosk_model.ps1 es full
.\download_vosk_model.ps1 zh full
```

## Manual installation example

```powershell
mkdir vosk-model
mkdir vosk-model\en

Expand-Archive -Path vosk-model-en-us-0.22.zip -DestinationPath temp
Move-Item temp\vosk-model-en-us-0.22\* vosk-model\en\
Remove-Item -Recurse temp
```

## How the app uses the structure

When you choose an audio language in the UI, the app looks for the model in:

```text
vosk-model/<language-code>/
```

Examples:

- `vosk-model/en/`
- `vosk-model/ru/`
- `vosk-model/es/`

## Compatibility with the old layout

The app still contains backward-compatibility logic for older Vosk layouts, such as:

- `vosk-model/`
- `vosk-model-ru`
- `vosk-model-small-ru`

However, for clean multi-language usage, the recommended structure is:

```text
vosk-model/<language-code>/
```

## Notes

- Full models usually provide better quality than small models
- Models work offline after download
- Install only the languages you actually need
