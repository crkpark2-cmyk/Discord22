"""
PCM bytes -> 텍스트 변환 (Groq API, 무료, 한국어+영어 자동 인식)

Groq는 OpenAI와 호환되는 /audio/transcriptions 엔드포인트를 무료로 제공함.
모델: whisper-large-v3-turbo (빠름) 또는 whisper-large-v3 (정확도 더 높음)

API 키는 https://console.groq.com 에서 무료로 발급받을 수 있음.
"""

import io
import os
import wave

import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def _pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int, channels: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def transcribe_pcm(pcm_bytes: bytes, sample_rate: int = 48000, channels: int = 2) -> str:
    """
    discord에서 받은 raw PCM(48kHz, 16bit, stereo)을 wav로 감싸서 Groq API에 전송.
    language를 지정하지 않으면 자동 감지 (한국어/영어 혼용 가능).
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY 환경변수가 설정되어 있지 않아.")

    wav_bytes = _pcm_to_wav_bytes(pcm_bytes, sample_rate, channels)

    response = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        data={
            "model": GROQ_MODEL,
            "response_format": "text",
        },
        timeout=30,
    )

    if response.status_code != 200:
        # 호출 실패해도 봇 전체가 죽지 않도록 빈 문자열 반환 + 로그만 출력
        print(f"[Groq STT 오류] {response.status_code}: {response.text}")
        return ""

    text = response.text.strip()
    return text
