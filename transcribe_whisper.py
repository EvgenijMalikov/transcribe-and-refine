"""
Speech-to-text helpers powered by Faster Whisper.
"""

import os
import logging
from typing import Optional
from runtime_check import require_python_310

require_python_310()

logger = logging.getLogger(__name__)

# Check whether faster-whisper is installed.
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("faster-whisper is not installed. Run: pip install faster-whisper")


class WhisperTranscriber:
    """Transcribe speech with Faster Whisper."""

    def __init__(self, model_size: str = "base", device: str = "auto", compute_type: str = "auto"):
        """
        Initialize the Whisper transcriber.

        Args:
            model_size: Whisper model size
            device: Device name ("cuda", "cpu", or "auto")
            compute_type: Compute precision mode
        """
        if not WHISPER_AVAILABLE:
            raise ImportError("faster-whisper is not installed")

        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        logger.info("Loading Whisper model %s on %s (%s)", model_size, device, compute_type)
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )

        self.device = device
        logger.info("Whisper model loaded on %s", device)

    def transcribe_file(self, file_path: str, language: str = "ru") -> str:
        """
        Transcribe speech from an audio file.

        Args:
            file_path: Audio file path
            language: Audio language code

        Returns:
            Recognized text
        """
        try:
            logger.info("Starting Whisper transcription for %s", file_path)
            segments, info = self.model.transcribe(
                file_path,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            logger.info(
                "Whisper detected language %s with probability %.2f",
                info.language,
                info.language_probability,
            )

            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)
                logger.debug(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")

            full_text = " ".join(text_parts).strip()

            logger.info("Whisper transcription completed. Output length: %s characters", len(full_text))
            return full_text

        except Exception as e:
            logger.error("Whisper transcription failed for %s: %s", file_path, e)
            raise


def transcribe_audio_whisper(file_path: str, use_gpu: bool = True) -> str:
    """
    Convenience helper for Faster Whisper transcription.

    Args:
        file_path: Audio file path
        use_gpu: Whether GPU acceleration should be attempted

    Returns:
        Recognized text
    """
    device = "auto" if use_gpu else "cpu"
    transcriber = WhisperTranscriber(model_size="base", device=device)
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
            try:
                import torch
                cuda_available = torch.cuda.is_available()
                if cuda_available:
                    print(f"CUDA is available: {torch.cuda.get_device_name(0)}")
                else:
                    print("CUDA is unavailable, using CPU")
            except ImportError:
                print("PyTorch is not installed")

            text = transcribe_audio_whisper(audio_file)
            print("\n=== Transcript ===")
            print(text)
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python transcribe_whisper.py <path_to_audio_file>")
