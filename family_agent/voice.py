from __future__ import annotations

from typing import Optional


class VoiceIO:
    """
    Optional voice module.
    - STT: whisper (if installed)
    - TTS: kokoro (if installed)
    """

    def __init__(self) -> None:
        self._whisper = None
        self._kokoro = None

        try:
            import whisper  # type: ignore

            self._whisper = whisper
        except Exception:
            self._whisper = None

        try:
            import kokoro  # type: ignore

            self._kokoro = kokoro
        except Exception:
            self._kokoro = None

    @property
    def stt_available(self) -> bool:
        return self._whisper is not None

    @property
    def tts_available(self) -> bool:
        return self._kokoro is not None

    def speech_to_text(self, audio_path: str, model_name: str = "base") -> str:
        if not self._whisper:
            raise RuntimeError("whisper 未安装，无法进行语音识别。")
        model = self._whisper.load_model(model_name)
        result = model.transcribe(audio_path)
        return str(result.get("text", "")).strip()

    def text_to_speech(self, text: str, out_path: str = "reply.wav") -> Optional[str]:
        if not self._kokoro:
            raise RuntimeError("kokoro 未安装，无法进行语音合成。")
        # Different kokoro forks have different APIs.
        # Keep a conservative interface with graceful fallback.
        if hasattr(self._kokoro, "tts_to_file"):
            self._kokoro.tts_to_file(text, out_path)
            return out_path
        raise RuntimeError("当前 kokoro 包不支持 tts_to_file 接口。")
