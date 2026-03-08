"""
Helpers for converting audio files into a Vosk-friendly WAV format.
"""

import os
import subprocess
import logging
import wave

logger = logging.getLogger(__name__)


def convert_to_wav(input_path: str, output_path: str = None) -> str:
    """
    Convert an audio file to 16kHz mono WAV through ffmpeg.

    Args:
        input_path: Input audio file path
        output_path: Optional explicit output WAV path

    Returns:
        Path to the converted WAV file
    """
    try:
        logger.info("Converting %s to WAV", input_path)

        if output_path is None:
            base_name = os.path.splitext(input_path)[0]
            output_path = f"{base_name}_converted.wav"

        command = [
            'ffmpeg',
            '-y',
            '-err_detect', 'ignore_err',
            '-fflags', '+discardcorrupt+genpts',
            '-i', input_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ac', '1',
            '-ar', '16000',
            '-max_muxing_queue_size', '9999',
            output_path
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Audio converted successfully: %s", output_path)
            return output_path

        logger.warning("Primary ffmpeg conversion failed; trying a more tolerant fallback")

        alternative_command = [
            'ffmpeg',
            '-y',
            '-analyzeduration', '100M',
            '-probesize', '100M',
            '-err_detect', 'ignore_err',
            '-fflags', '+discardcorrupt+genpts+igndts',
            '-i', input_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ac', '1',
            '-ar', '16000',
            '-af', 'aformat=sample_fmts=s16:channel_layouts=mono',
            '-max_muxing_queue_size', '9999',
            output_path
        ]

        result2 = subprocess.run(
            alternative_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result2.returncode == 0:
            logger.info("Fallback conversion succeeded: %s", output_path)
            return output_path

        stderr_short = result2.stderr[:1000] if len(result2.stderr) > 1000 else result2.stderr
        logger.error("Both conversion attempts failed")
        logger.error("FFmpeg stderr (first 1000 characters): %s", stderr_short)

        raise Exception(
            f"Could not convert {os.path.basename(input_path)}. "
            "The file may be corrupted or use an unsupported encoding. "
            "Try re-saving it as MP3 or WAV and upload it again."
        )

    except FileNotFoundError:
        logger.error("ffmpeg was not found in PATH")
        raise Exception("ffmpeg is not installed or not available in PATH.")
    except Exception as e:
        logger.error("Audio conversion failed for %s: %s", input_path, e)
        raise


def get_audio_duration(file_path: str) -> float:
    """
    Return the audio duration in seconds using ffprobe.

    Args:
        file_path: Audio file path

    Returns:
        Duration in seconds
    """
    try:
        command = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"ffprobe error: {result.stderr}")

        duration = float(result.stdout.strip())
        logger.info("Detected duration for %s: %.2f seconds", file_path, duration)
        return duration

    except FileNotFoundError:
        logger.error("ffprobe was not found in PATH")
        raise Exception("ffprobe is not installed or not available in PATH.")
    except Exception as e:
        logger.error("Failed to read duration for %s: %s", file_path, e)
        raise


def split_audio(file_path: str, chunk_duration: int = 300) -> list:
    """
    Split a long WAV file into smaller chunks with ffmpeg.

    Args:
        file_path: Audio file path
        chunk_duration: Maximum chunk duration in seconds

    Returns:
        List of chunk file paths
    """
    try:
        duration = get_audio_duration(file_path)

        if duration <= chunk_duration:
            return [file_path]

        chunks = []
        base_name = os.path.splitext(file_path)[0]

        logger.info("Splitting %s into %s-second chunks", file_path, chunk_duration)
        num_chunks = int(duration / chunk_duration) + (1 if duration % chunk_duration > 0 else 0)

        for i in range(num_chunks):
            start_time = i * chunk_duration
            chunk_path = f"{base_name}_chunk_{i}.wav"

            command = [
                'ffmpeg',
                '-y',
                '-err_detect', 'ignore_err',
                '-fflags', '+discardcorrupt+genpts',
                '-ss', str(start_time),
                '-i', file_path,
                '-t', str(chunk_duration),
                '-vn',
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-max_muxing_queue_size', '9999',
                chunk_path
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode != 0:
                logger.warning(
                    "Primary chunk extraction failed for chunk %s; trying fallback settings",
                    i + 1,
                )

                alternative_command = [
                    'ffmpeg',
                    '-y',
                    '-err_detect', 'ignore_err',
                    '-fflags', '+discardcorrupt+genpts+igndts',
                    '-ss', str(start_time),
                    '-i', file_path,
                    '-t', str(chunk_duration),
                    '-vn',
                    '-acodec', 'pcm_s16le',
                    '-ar', '16000',
                    '-ac', '1',
                    '-af', 'aformat=sample_fmts=s16:channel_layouts=mono',
                    '-max_muxing_queue_size', '9999',
                    chunk_path
                ]

                result2 = subprocess.run(
                    alternative_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                if result2.returncode != 0:
                    logger.warning("Could not create chunk %s; skipping it", i + 1)
                    continue

            chunks.append(chunk_path)
            logger.info("Created chunk %s: %s", i + 1, chunk_path)

        if not chunks:
            raise Exception("No audio chunks could be created from this file.")

        logger.info("Finished splitting into %s chunks", len(chunks))
        return chunks

    except Exception as e:
        logger.error("Audio splitting failed for %s: %s", file_path, e)
        raise
