"""
Flask application for local audio transcription and optional text refinement.
"""

import logging
import uuid
import json
import os
from datetime import datetime
from typing import Optional
from flask import Flask, Response, jsonify, render_template, request, send_file, stream_with_context
from werkzeug.utils import secure_filename
from config import Config
from runtime_check import require_python_310
from transcribe import VoskTranscriber
from openai_refiner import TextRefiner

require_python_310()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import Whisper support.
try:
    from transcribe_whisper import WhisperTranscriber
    WHISPER_AVAILABLE = True
    logger.info("Whisper support is available")
except ImportError:
    WHISPER_AVAILABLE = False
    logger.info("Whisper support is unavailable; Vosk remains available")

# Create the Flask app.
app = Flask(__name__)
app.config.from_object(Config)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
Config.init_app(app)

# Cache heavy objects so they are initialized lazily only once.
transcribers_cache = {}
refiner = None


def make_error_response(
    message: str,
    status_code: int,
    error_code: Optional[str] = None,
    error_details: Optional[dict] = None,
):
    """Build a consistent JSON error response."""
    payload = {'error': message}

    if error_code:
        payload['error_code'] = error_code
    if error_details:
        payload['error_details'] = error_details

    return jsonify(payload), status_code


def format_sse_event(payload: dict) -> str:
    """Serialize a single Server-Sent Events payload."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_safe_upload_filename(original_filename: str) -> str:
    """Create a filesystem-safe upload filename while preserving the extension."""
    file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    filename = secure_filename(original_filename)

    if not filename:
        safe_base_name = f"audio_{uuid.uuid4().hex[:8]}"
        return f"{safe_base_name}.{file_extension}" if file_extension else safe_base_name

    if '.' not in filename and file_extension:
        return f"{filename}.{file_extension}"

    return filename


def build_result_filenames(timestamp: str, original_filename: str) -> dict:
    """Create server-side and download filenames for processing results."""
    original_base_name = os.path.splitext(original_filename)[0]

    return {
        'transcript_file': f"{timestamp}_{original_base_name}_transcript.txt",
        'refined_file': f"{timestamp}_{original_base_name}_refined.txt",
        'transcript_display': f"{original_base_name}_transcript.txt",
        'refined_display': f"{original_base_name}_refined.txt",
    }


def cleanup_file(filepath: str):
    """Delete a temporary file without failing the whole request."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.warning("Could not remove temporary file %s: %s", filepath, e)


def validate_request_options(engine: str, language: str):
    """Validate requested engine and audio language before processing."""
    if engine not in Config.SUPPORTED_ENGINES:
        return make_error_response(
            f"Unsupported engine '{engine}'.",
            400,
            'invalid_engine',
            {'engine': engine, 'supported_engines': list(Config.SUPPORTED_ENGINES)},
        )

    if language not in Config.SUPPORTED_AUDIO_LANGUAGES:
        return make_error_response(
            f"Unsupported audio language '{language}'.",
            400,
            'invalid_audio_language',
            {'language': language, 'supported_languages': list(Config.SUPPORTED_AUDIO_LANGUAGES)},
        )

    if engine == 'whisper' and not WHISPER_AVAILABLE:
        return make_error_response(
            "Whisper is not installed on this instance.",
            400,
            'whisper_unavailable',
        )

    if not Config.OPENAI_API_KEY:
        return make_error_response(
            "OpenAI is not configured. Set OPENAI_API_KEY in your .env file.",
            400,
            'openai_not_configured',
        )

    return None


def get_public_app_config() -> dict:
    """Expose safe UI-facing config values to the client."""
    return {
        'allowedExtensions': sorted(Config.ALLOWED_EXTENSIONS),
        'defaultUiLanguage': Config.DEFAULT_UI_LANGUAGE,
        'defaultAudioLanguage': Config.DEFAULT_AUDIO_LANGUAGE,
        'defaultEngine': Config.DEFAULT_ENGINE,
        'supportedAudioLanguages': list(Config.SUPPORTED_AUDIO_LANGUAGES),
        'supportedUiLanguages': list(Config.SUPPORTED_AUDIO_LANGUAGES),
        'supportedEngines': list(Config.SUPPORTED_ENGINES),
        'maxContentLengthMb': round(Config.MAX_CONTENT_LENGTH / (1024 * 1024)),
    }


def get_asset_version() -> int:
    """Build a simple cache-busting version based on static asset mtimes."""
    asset_paths = [
        os.path.join(app.root_path, 'templates', 'index.html'),
        os.path.join(app.root_path, 'static', 'css', 'index.css'),
        os.path.join(app.root_path, 'static', 'js', 'index.js'),
    ]
    return int(max(os.path.getmtime(path) for path in asset_paths if os.path.exists(path)))


def resolve_download_path(filename: str) -> str:
    """Resolve a result filename to an absolute safe path inside RESULTS_FOLDER."""
    results_folder = os.path.abspath(app.config['RESULTS_FOLDER'])
    filepath = os.path.abspath(os.path.join(results_folder, filename))

    if os.path.commonpath([results_folder, filepath]) != results_folder:
        raise PermissionError("Invalid file path")

    return filepath


def strip_timestamp_prefix(filename: str) -> str:
    """Remove the generated timestamp prefix from a download filename."""
    parts = filename.split('_', 2)
    if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
        return parts[2]
    return filename


def get_transcriber(engine: str = 'vosk', language: str = 'ru'):
    """
    Get a lazily initialized transcriber instance.

    Args:
        engine: 'vosk' or 'whisper'
        language: Audio language code ('ru', 'en', etc.)
    """
    global transcribers_cache

    cache_key = f"{engine}_{language}"

    if cache_key not in transcribers_cache:
        if engine == 'whisper':
            if not WHISPER_AVAILABLE:
                raise RuntimeError("Whisper is not installed on this instance.")

            logger.info("Initializing Whisper transcriber for language '%s'...", language)
            transcribers_cache[cache_key] = WhisperTranscriber(
                model_size=Config.WHISPER_MODEL,
                device='cpu',
                compute_type='int8'
            )
            logger.info("Whisper transcriber initialized")
        elif engine == 'vosk':
            logger.info("Initializing Vosk transcriber for language '%s'...", language)
            transcribers_cache[cache_key] = VoskTranscriber(language=language)
            logger.info("Vosk transcriber initialized")
        else:
            raise ValueError(f"Unsupported engine '{engine}'.")

    return transcribers_cache[cache_key]


def get_refiner():
    """Get a lazily initialized text refiner instance."""
    global refiner
    if refiner is None:
        logger.info("Initializing OpenAI text refiner...")
        refiner = TextRefiner()
    return refiner


@app.route('/')
def index():
    """Render the main UI."""
    return render_template(
        'index.html',
        app_config=get_public_app_config(),
        asset_version=get_asset_version(),
    )


@app.after_request
def add_no_cache_headers(response):
    """Avoid stale HTML/JS/CSS during local development."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response




@app.route('/upload', methods=['POST'])
def upload_files():
    """
    Process uploaded files sequentially with streaming progress updates.
    Chunks inside each file may still be processed in parallel by the transcriber.
    """
    if 'files[]' not in request.files:
        return make_error_response('No files were uploaded.', 400, 'no_files_uploaded')

    files = request.files.getlist('files[]')

    if not files or all(file.filename == '' for file in files):
        return make_error_response('No files were selected.', 400, 'no_files_selected')

    engine = request.form.get('engine', Config.DEFAULT_ENGINE)
    language = request.form.get('language', Config.DEFAULT_AUDIO_LANGUAGE)

    validation_error = validate_request_options(engine, language)
    if validation_error:
        return validation_error

    def generate():
        """Yield incremental processing results through SSE."""
        try:
            logger.info(
                "Processing request started: engine=%s, language=%s, files=%s",
                engine,
                language,
                len(files),
            )

            for file in files:
                if file and file.filename != '':
                    original_filename = file.filename

                    if not Config.allowed_file(original_filename):
                        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                        logger.warning("Unsupported file format for '%s' (%s)", original_filename, file_ext or 'no extension')
                        result = {
                            'filename': original_filename,
                            'status': 'error',
                            'engine': engine,
                            'language': language,
                            'error': f"Unsupported file format ({'.' + file_ext if file_ext else 'no extension'}).",
                            'error_code': 'unsupported_format',
                            'error_details': {
                                'extension': f".{file_ext}" if file_ext else 'no extension',
                                'allowed_extensions': sorted(Config.ALLOWED_EXTENSIONS),
                            },
                        }
                        yield format_sse_event(result)
                        continue

                    filename = build_safe_upload_filename(original_filename)

                    logger.info("Received file '%s' -> safe filename '%s'", original_filename, filename)

                    try:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(filepath)

                        logger.info("Processing file '%s' with engine=%s, language=%s", filename, engine, language)

                        trans = get_transcriber(engine=engine, language=language)
                        transcribed_text = trans.transcribe_file(filepath, language=language)

                        if not transcribed_text or not transcribed_text.strip():
                            logger.warning("No speech could be transcribed from '%s'", filename)
                            result = {
                                'filename': original_filename,
                                'status': 'error',
                                'engine': engine,
                                'language': language,
                                'error': 'No speech could be transcribed from this file.',
                                'error_code': 'transcription_failed',
                            }
                            yield format_sse_event(result)
                            cleanup_file(filepath)
                            continue

                        logger.info("Refining transcript for '%s' with OpenAI...", filename)
                        ref = get_refiner()
                        refined_text = ref.refine_transcript(transcribed_text)

                        result_files = build_result_filenames(timestamp, original_filename)
                        transcript_path = os.path.join(app.config['RESULTS_FOLDER'], result_files['transcript_file'])
                        with open(transcript_path, 'w', encoding='utf-8') as f:
                            f.write(transcribed_text)

                        refined_path = os.path.join(app.config['RESULTS_FOLDER'], result_files['refined_file'])
                        with open(refined_path, 'w', encoding='utf-8') as f:
                            f.write(refined_text)

                        logger.info("File '%s' processed successfully", filename)

                        result = {
                            'filename': original_filename,
                            'status': 'success',
                            'engine': engine,
                            'language': language,
                            'transcript_file': result_files['transcript_file'],
                            'refined_file': result_files['refined_file'],
                            'transcript_display': result_files['transcript_display'],
                            'refined_display': result_files['refined_display'],
                            'timestamp_iso': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
                        }
                        yield format_sse_event(result)
                        cleanup_file(filepath)

                    except Exception as e:
                        logger.error("Failed to process file '%s': %s", filename, e)
                        result = {
                            'filename': original_filename,
                            'status': 'error',
                            'engine': engine,
                            'language': language,
                            'error': str(e),
                        }
                        yield format_sse_event(result)
                        cleanup_file(filepath)

            yield format_sse_event({"done": True})

        except Exception as e:
            logger.error("Request processing failed: %s", e)
            yield format_sse_event({"error": str(e)})

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/download/<path:filename>')
def download_file(filename):
    """
    Download a generated result file.

    Args:
        filename: Result filename
    """
    try:
        filepath = resolve_download_path(filename)
        if not os.path.exists(filepath):
            logger.warning("Requested file was not found: %s", filepath)
            return make_error_response('File not found.', 404, 'file_not_found')

        download_name = strip_timestamp_prefix(filename)
        return send_file(filepath, as_attachment=True, download_name=download_name)

    except PermissionError:
        logger.warning("Blocked an invalid download path request: %s", filename)
        return make_error_response('Invalid file path.', 403, 'invalid_download_path')
    except Exception as e:
        logger.error("Failed to download file '%s': %s", filename, e)
        return make_error_response(str(e), 500, 'download_failed')


@app.route('/health')
def health():
    """Return lightweight health and capability information for the UI."""
    try:
        return jsonify({
            'status': 'ok' if Config.OPENAI_API_KEY else 'warning',
            'message': 'Application is running.',
            'openai_configured': bool(Config.OPENAI_API_KEY),
            'whisper_available': WHISPER_AVAILABLE,
            'cloud_refiner_provider': 'openai',
            'local_transcription': True,
            'supported_audio_languages': list(Config.SUPPORTED_AUDIO_LANGUAGES),
            'default_audio_language': Config.DEFAULT_AUDIO_LANGUAGE,
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle oversized upload attempts."""
    return make_error_response(
        f"File is too large. Maximum size: {round(Config.MAX_CONTENT_LENGTH / (1024 * 1024))}MB.",
        413,
        'file_too_large',
        {'max_size_mb': round(Config.MAX_CONTENT_LENGTH / (1024 * 1024))},
    )


if __name__ == '__main__':
    if not Config.OPENAI_API_KEY:
        logger.warning(
            "OpenAI is not configured. Create a .env file and set OPENAI_API_KEY."
        )

    logger.info("Starting Flask application on %s:%s", Config.HOST, Config.PORT)
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
