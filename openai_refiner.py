"""
Utilities for cleaning up transcripts with the OpenAI API.
"""

import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
from runtime_check import require_python_310

require_python_310()

logger = logging.getLogger(__name__)

# Load environment variables from .env when available.
load_dotenv()


class TextRefiner:
    """Refine raw speech-to-text output with OpenAI."""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY from .env.
            model: Model name. Falls back to OPENAI_MODEL from .env.
        """
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError(
                    "OpenAI API key was not found. Create a .env file and set OPENAI_API_KEY."
                )

        self.client = OpenAI(api_key=api_key)

        if model is None:
            model = os.getenv('OPENAI_MODEL', 'gpt-4o')
        self.model = model

        logger.info("Initialized TextRefiner with model %s", self.model)

    def refine_text(self, text: str, custom_prompt: str = None) -> str:
        """
        Clean up a transcript using the OpenAI Chat Completions API.

        Args:
            text: Input transcript to refine
            custom_prompt: Optional custom system prompt

        Returns:
            Refined transcript text
        """
        if not text or not text.strip():
            logger.warning("Received an empty transcript to refine")
            return ""

        try:
            logger.info("Sending transcript to OpenAI (length: %s characters)", len(text))

            system_prompt = custom_prompt or self._create_default_prompt()

            request_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
            }

            model_limits = {
                'o1-preview': 32768,
                'o1-mini': 65536,
                'o1': 100000,
                'o3-mini': 100000,
                'o3': 200000,

                'gpt-5.2': 128000,
                'gpt-5': 128000,
                'gpt-4o': 16384,
                'gpt-4o-mini': 16384,
                'gpt-4-turbo': 4096,
                'gpt-4': 8192,
                'gpt-3.5-turbo': 4096,
            }

            max_tokens = 16384
            for model_prefix, limit in model_limits.items():
                if self.model.startswith(model_prefix):
                    max_tokens = limit
                    break

            is_reasoning_model = any(self.model.startswith(prefix) for prefix in ['o1', 'o3'])

            if is_reasoning_model:
                request_params["max_completion_tokens"] = max_tokens
            else:
                request_params["temperature"] = 0.1
                request_params["max_completion_tokens"] = max_tokens

            logger.info(
                "Using model %s with max_completion_tokens=%s",
                self.model,
                request_params['max_completion_tokens'],
            )

            response = self.client.chat.completions.create(**request_params)
            refined_text = response.choices[0].message.content.strip()

            logger.info("Transcript refined successfully (length: %s characters)", len(refined_text))
            return refined_text

        except Exception as e:
            logger.error("Failed to refine transcript with OpenAI: %s", e)
            raise

    def _create_default_prompt(self) -> str:
        """
        Build the default system prompt for generic transcript cleanup.

        Returns:
            System prompt text
        """
        return """You are a professional transcript editor.

You will receive speech-to-text output that was generated from an audio recording.

Your task:
1. Remove obvious filler words, repeated fragments, and transcription artifacts when they do not add meaning.
2. Keep the original meaning, tone, and language of the source content.
3. Fix only obvious recognition mistakes that are clearly implied by the surrounding context.
4. Do not invent new facts, sentences, or structure that is not supported by the source transcript.
5. Return only the cleaned transcript without explanations, notes, or markdown.
"""

    def refine_transcript(self, text: str) -> str:
        """
        Refine a raw transcript with the default cleanup prompt.

        Args:
            text: Raw transcript text

        Returns:
            Cleaned transcript
        """
        return self.refine_text(text)

    def refine_fairy_tale(self, text: str) -> str:
        """Backward-compatible alias for older code paths."""
        return self.refine_transcript(text)


def refine_transcribed_text(text: str, api_key: str = None, model: str = None) -> str:
    """
    Convenience helper for refining a transcript.

    Args:
        text: Transcript text
        api_key: Optional OpenAI API key
        model: Optional model name

    Returns:
        Cleaned transcript
    """
    refiner = TextRefiner(api_key=api_key, model=model)
    return refiner.refine_text(text)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    import sys
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()

            refined = refine_transcribed_text(text)

            print("\n=== Refined Text ===")
            print(refined)

            output_file = input_file.replace('.txt', '_refined.txt')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(refined)
            print(f"\n=== Saved output to {output_file} ===")

        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python openai_refiner.py <path_to_text_file>")
