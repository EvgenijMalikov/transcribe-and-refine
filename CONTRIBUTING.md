# Contributing

Thanks for contributing to Transcribe and Refine.

This project is a Flask-based web app for local audio transcription with optional OpenAI-powered cleanup. Keep changes focused, easy to review, and aligned with the current lightweight workflow.

## Before You Start

- Check existing issues and pull requests before starting work.
- For non-trivial changes, describe the problem and proposed approach first.
- Prefer small, focused pull requests over large mixed changes.

## Local Setup

1. Create and activate a Python 3.10+ virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the environment template:

```bash
cp env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item env.example .env
```

4. Install `ffmpeg` and make sure it is available in `PATH`.
5. Install Vosk models under `vosk-model/<language>/` for the languages you want to test.
6. Optionally install `faster-whisper` if your change affects the Whisper engine:

```bash
pip install faster-whisper
```

## Development Guidelines

- Target Python `3.10+`.
- Keep patches narrow and avoid unrelated refactors.
- Reuse the existing project structure and naming style.
- Update documentation when behavior, configuration, or setup steps change.
- If you add or rename environment variables, update `env.example` and `README.md`.
- If you change user-facing UI text, update the relevant translation files in `static/i18n/` when applicable.

## Do Not Commit

- Secrets such as `.env` or API keys
- Local model files under `vosk-model/`
- Uploaded audio in `uploads/`
- Generated outputs in `results/`
- Machine-specific or temporary files

## Validation Before Opening a PR

Install dependencies and run the same checks used in CI:

```bash
python -m py_compile app.py config.py audio_converter.py transcribe.py transcribe_whisper.py openai_refiner.py runtime_check.py
python -c "from app import app; print(app.url_map)"
```

Also verify the app starts locally when your change affects runtime behavior:

```bash
python app.py
```

If your change affects transcription, refinement, uploads, downloads, or UI behavior, include a short manual test note in the pull request.

## Pull Request Expectations

- Use a clear, descriptive title.
- Explain why the change is needed.
- Summarize the main behavior change.
- List the checks you ran.
- Add screenshots or short recordings for visible UI changes.
- Link the related issue when one exists.

## Review Notes

Reviewers should be able to understand:

- the user or developer problem being solved
- the scope of the change
- how the change was validated
- any follow-up work that is intentionally out of scope

## Questions

If something is unclear, open an issue or start the discussion in the pull request before investing in a larger implementation.
