# Transcribe and Refine

Transcribe and Refine is a web app for local audio transcription with optional transcript cleanup via OpenAI.

It supports multiple audio languages, a browser UI, Vosk and Whisper as transcription engines, and progressive result streaming while files are being processed.

## Features

- Local speech-to-text with `Vosk`
- Optional `Whisper` support when `faster-whisper` is installed
- UI translations for English, Russian, Spanish, French, German, and Chinese
- Separate interface language and audio language selection
- Automatic audio conversion with `ffmpeg`
- Long audio handling with chunking
- Progressive result streaming in the browser
- Downloadable raw transcript and refined text output

## Important Note About Local vs Cloud Processing

This app is **not fully local**.

- Audio transcription runs locally on your machine with `Vosk` or `Whisper`
- Transcript cleanup is sent to the OpenAI API

If `OPENAI_API_KEY` is not configured, the app starts, but processing remains limited because refinement is part of the current workflow.

## Requirements

- Python `3.10+`
- `ffmpeg` available in `PATH`
- OpenAI API key
- Vosk model files for the audio languages you want to use
- Optional: `faster-whisper` if you want the Whisper engine in the UI

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/EvgenijMalikov/transcribe-and-refine.git
cd transcribe-and-refine
```

### 2. Create a virtual environment

Windows:

```bash
py -3.10 -m venv venv
venv\Scripts\activate
```

Linux/macOS:

```bash
python3.10 -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

To enable the Whisper engine in the web UI:

```bash
pip install faster-whisper
```

### 4. Install ffmpeg

Windows:

- Download it from [ffmpeg.org](https://ffmpeg.org/download.html)
- Add the `bin` directory to `PATH`

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install ffmpeg
```

macOS:

```bash
brew install ffmpeg
```

### 5. Install Vosk models

Recommended on Windows:

```powershell
.\download_vosk_model.ps1 en full
.\download_vosk_model.ps1 ru full
.\download_vosk_model.ps1 zh full
```

Supported script combinations:

- `ru small`, `ru full`
- `en small`, `en full`
- `es full`
- `fr full`
- `de full`
- `zh full`

Models are stored under:

```text
vosk-model/
  en/
  ru/
  es/
  fr/
  de/
  zh/
```

More details:

- [VOSK_MODELS_STRUCTURE.md](VOSK_MODELS_STRUCTURE.md)
- [INSTALL_VOSK.md](INSTALL_VOSK.md)

### 6. Configure environment variables

Copy the example file:

Windows:

```powershell
Copy-Item env.example .env
```

Linux/macOS:

```bash
cp env.example .env
```

Minimal `.env` example:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
DEFAULT_UI_LANGUAGE=en
DEFAULT_AUDIO_LANGUAGE=en
DEFAULT_ENGINE=vosk
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=false
```

The full template is available in [`env.example`](env.example).

### 7. Run the app

```bash
python app.py
```

Open:

- [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Usage

1. Open the web UI
2. Choose the interface language
3. Choose the transcription engine
4. Choose the audio language
5. Upload one or more audio files
6. Wait for streamed results to appear
7. Download:
   - `*_transcript.txt`
   - `*_refined.txt`

## Supported Audio Formats

- `mp3`
- `wav`
- `ogg`
- `opus`
- `oga`
- `m4a`

## Output Files

Each processed audio file generates two text files:

- `*_transcript.txt`: raw speech-to-text output
- `*_refined.txt`: cleaned version returned by OpenAI

Generated files are saved into `results/`.

## Project Structure

```text
transcribe-and-refine/
├── app.py
├── audio_converter.py
├── config.py
├── openai_refiner.py
├── transcribe.py
├── transcribe_whisper.py
├── runtime_check.py
├── requirements.txt
├── env.example
├── download_vosk_model.ps1
├── templates/
│   └── index.html
├── static/
│   ├── css/
│   ├── js/
│   └── i18n/
├── uploads/
├── results/
└── vosk-model/
```

## Troubleshooting

### Vosk model not found

Make sure the model is installed under `vosk-model/<language>/`.

### OpenAI is not configured

Create `.env` and add:

```env
OPENAI_API_KEY=your_key_here
```

### ffmpeg not found

Install `ffmpeg` and verify it is available in `PATH`.

### Whisper is unavailable in the UI

Install the optional dependency:

```bash
pip install faster-whisper
```

### Processing is slow

This is expected for longer files because the pipeline includes:

- format conversion
- local transcription
- OpenAI refinement

## Security Notes

- Never commit `.env`
- Treat API keys as secrets
- Do not publish files from `uploads/`, `results/`, or local model folders

## License

MIT. See [`LICENSE`](LICENSE).
