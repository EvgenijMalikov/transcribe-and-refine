"""
Speech-to-text helpers powered by Vosk.
"""

import os
import json
import wave
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from vosk import Model, KaldiRecognizer
from audio_converter import convert_to_wav, get_audio_duration, split_audio
from runtime_check import require_python_310

require_python_310()

logger = logging.getLogger(__name__)


class VoskTranscriber:
    """Transcribe speech with Vosk across multiple supported languages."""

    def __init__(self, language: str = 'ru', model_path: str = None):
        """
        Initialize the Vosk transcriber.

        Args:
            language: Audio language code
            model_path: Optional explicit model path
        """
        self.language = language

        if model_path is None:
            model_path = os.path.join('vosk-model', language)

            if not os.path.exists(model_path):
                old_paths = [
                    'vosk-model',
                    f'vosk-model-{language}',
                    f'vosk-model-small-{language}',
                ]

                for path in old_paths:
                    if os.path.exists(path):
                        model_path = path
                        break
                else:
                    raise FileNotFoundError(
                        f"Vosk model for language '{language}' was not found.\n"
                        "Download a model from https://alphacephei.com/vosk/models\n"
                        f"and extract it into 'vosk-model/{language}/'."
                    )

        logger.info("Loading Vosk model for language '%s' from %s", language, model_path)
        self.model = Model(model_path)
        logger.info("Vosk model for '%s' loaded successfully", language)

    def transcribe_wav(self, wav_path: str) -> str:
        """
        Transcribe speech from a WAV file.

        Args:
            wav_path: WAV file path

        Returns:
            Recognized text
        """
        try:
            logger.info("Starting Vosk transcription for %s", wav_path)

            wf = wave.open(wav_path, "rb")

            if wf.getnchannels() != 1:
                logger.warning("WAV file %s is not mono; recognition quality may be lower", wav_path)
            if wf.getframerate() != 16000:
                logger.warning("WAV file %s is not 16kHz; recognition quality may be lower", wav_path)

            rec = KaldiRecognizer(self.model, wf.getframerate())
            rec.SetWords(True)

            results = []

            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if 'text' in result and result['text']:
                        results.append(result['text'])

            final_result = json.loads(rec.FinalResult())
            if 'text' in final_result and final_result['text']:
                results.append(final_result['text'])

            wf.close()

            full_text = ' '.join(results)
            logger.info("Vosk transcription completed. Output length: %s characters", len(full_text))
            return full_text.strip()

        except Exception as e:
            logger.error("Vosk transcription failed for %s: %s", wav_path, e)
            raise

    def transcribe_file(self, file_path: str, max_chunk_duration: int = 600, language: str = None) -> str:
        """
        Transcribe an audio file of any supported format.

        Args:
            file_path: Input audio file path
            max_chunk_duration: Maximum chunk duration in seconds
            language: Unused, preserved for API compatibility

        Returns:
            Recognized text
        """
        temp_files = []

        try:
            if not file_path.lower().endswith('.wav'):
                logger.info("Converting %s to WAV before Vosk transcription", file_path)
                wav_path = convert_to_wav(file_path)
                temp_files.append(wav_path)
            else:
                wav_path = file_path

            duration = get_audio_duration(wav_path)

            if duration > max_chunk_duration:
                logger.info("Long audio detected (%.1fs); splitting into chunks", duration)
                chunks = split_audio(wav_path, max_chunk_duration)
                temp_files.extend(chunks)

                logger.info("Transcribing %s chunks in parallel", len(chunks))
                all_texts = [None] * len(chunks)

                with ThreadPoolExecutor(max_workers=min(len(chunks), os.cpu_count() or 4)) as executor:
                    future_to_index = {
                        executor.submit(self.transcribe_wav, chunk): i 
                        for i, chunk in enumerate(chunks)
                    }

                    for future in as_completed(future_to_index):
                        index = future_to_index[future]
                        try:
                            text = future.result()
                            all_texts[index] = text
                            logger.info(
                                "Chunk %s/%s transcribed (%s characters)",
                                index + 1,
                                len(chunks),
                                len(text),
                            )
                        except Exception as e:
                            logger.error("Failed to transcribe chunk %s: %s", index + 1, e)
                            all_texts[index] = ""

                full_text = ' '.join(filter(None, all_texts))
            else:
                full_text = self.transcribe_wav(wav_path)

            return full_text

        finally:
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        logger.debug("Removed temporary file %s", temp_file)
                except Exception as e:
                    logger.warning("Could not remove temporary file %s: %s", temp_file, e)


def transcribe_audio(file_path: str, language: str = 'ru', model_path: str = None) -> str:
    """
    Convenience helper for Vosk transcription.

    Args:
        file_path: Audio file path
        language: Audio language code
        model_path: Optional Vosk model path

    Returns:
        Recognized text
    """
    transcriber = VoskTranscriber(language=language, model_path=model_path)
    return transcriber.transcribe_file(file_path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    import sys
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        try:
            text = transcribe_audio(audio_file)
            print("\n=== Transcript ===")
            print(text)
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python transcribe.py <path_to_audio_file>")
