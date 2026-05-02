from __future__ import annotations

from dataclasses import dataclass

from .config import Settings


@dataclass(slots=True)
class LLMStatus:
    dspy_available: bool
    configured: bool
    message: str


def safe_import_dspy():
    try:
        import dspy  # type: ignore
        return dspy
    except Exception:
        return None


def configure_dspy(settings: Settings) -> LLMStatus:
    dspy = safe_import_dspy()
    if dspy is None:
        return LLMStatus(dspy_available=False, configured=False, message='DSPy is not installed.')

    try:
        provider = settings.llm_provider
        if provider == 'ollama_chat':
            lm = dspy.LM(
                f'ollama_chat/{settings.llm_model}',
                api_base=settings.llm_api_base,
                api_key=settings.llm_api_key,
                temperature=settings.llm_temperature,
                cache=False,
            )
        elif provider == 'openai_compatible':
            lm = dspy.LM(
                f'openai/{settings.llm_model}',
                api_base=settings.llm_api_base,
                api_key=settings.llm_api_key or 'local',
                model_type='chat',
                temperature=settings.llm_temperature,
                cache=False,
            )
        elif provider == 'openai':
            lm = dspy.LM(
                f'openai/{settings.llm_model}',
                api_key=settings.llm_api_key,
                model_type='chat',
                temperature=settings.llm_temperature,
                cache=False,
            )
        else:
            return LLMStatus(dspy_available=True, configured=False, message=f'Unsupported LLM provider: {provider}')

        dspy.configure(lm=lm)
        return LLMStatus(dspy_available=True, configured=True, message='DSPy configured successfully.')
    except Exception as exc:
        return LLMStatus(dspy_available=True, configured=False, message=f'DSPy configuration failed: {exc}')
