"""
SpeakingSink
------------
음성 채널에서 들어오는 오디오를 '유저별'로 버퍼링하고,
일정 시간 이상 무음이 감지되면 그 구간을 하나의 발화로 잘라서
콜백(on_segment)으로 넘겨주는 커스텀 Sink.

discord(py-cord)에서 들어오는 raw PCM 포맷:
- 48000Hz, 16bit, 스테레오(2채널)
"""

import audioop
import asyncio
import time

import discord


class SpeakingSink(discord.sinks.Sink):
    def __init__(
        self,
        on_segment,
        silence_thresh: int = 500,
        silence_duration: float = 0.8,
        min_voice_ms: int = 300,
        *args,
        **kwargs,
    ):
        """
        on_segment: async def on_segment(user_id: int, pcm_bytes: bytes) 형태의 콜백
        silence_thresh: 이 RMS 값보다 작으면 '무음'으로 판단 (환경에 따라 조절 필요)
        silence_duration: 이 시간(초) 이상 무음이면 해당 유저의 발화 구간을 종료하고 콜백 호출
        min_voice_ms: 너무 짧은 잡음(헛기침 등)을 걸러내기 위한 최소 발화 길이
        """
        super().__init__(*args, **kwargs)
        self.on_segment = on_segment
        self.silence_thresh = silence_thresh
        self.silence_duration = silence_duration
        self.min_voice_bytes = int(48000 * 2 * 2 * (min_voice_ms / 1000))  # 48kHz*2ch*2byte

        self.buffers: dict[int, bytearray] = {}
        self.last_voice_time: dict[int, float] = {}
        self.voice_bytes: dict[int, int] = {}
        self.loop = asyncio.get_event_loop()

    def write(self, data, user):
        # user는 py-cord가 식별한 user id (int) 혹은 None(식별 전)
        if user is None:
            return

        if user not in self.buffers:
            self.buffers[user] = bytearray()
            self.last_voice_time[user] = time.time()
            self.voice_bytes[user] = 0

        try:
            rms = audioop.rms(data, 2)
        except Exception:
            rms = 0

        now = time.time()

        if rms >= self.silence_thresh:
            self.buffers[user].extend(data)
            self.voice_bytes[user] += len(data)
            self.last_voice_time[user] = now
            return

        # 무음 프레임이지만, 이미 말하던 중이면 잠깐의 무음은 자연스럽게 포함
        if self.buffers[user]:
            self.buffers[user].extend(data)
            if now - self.last_voice_time[user] >= self.silence_duration:
                pcm = bytes(self.buffers[user])
                voiced = self.voice_bytes[user]

                self.buffers[user] = bytearray()
                self.voice_bytes[user] = 0

                if voiced >= self.min_voice_bytes:
                    asyncio.run_coroutine_threadsafe(
                        self.on_segment(user, pcm), self.loop
                    )

    def cleanup(self):
        super().cleanup()
