# 2

import asyncio
import os

import discord
from discord.ext import commands

from keep_alive import start_keepalive_server
from sink import SpeakingSink
from transcriber import transcribe_pcm

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME", "음성-로그")

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# whisper 추론을 한 번에 하나씩만 처리해서 메모리/CPU 과부하 방지
transcribe_sem = asyncio.Semaphore(1)


def get_log_channel(guild: discord.Guild):
    for ch in guild.text_channels:
        if ch.name == LOG_CHANNEL_NAME:
            return ch
    return None


@bot.event
async def on_ready():
    print(f"로그인됨: {bot.user} (id={bot.user.id})")


@bot.command()
async def join(ctx: commands.Context):
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("먼저 음성 채널에 들어가 있어야 해.")
        return

    log_channel = get_log_channel(ctx.guild)
    if log_channel is None:
        await ctx.send(
            f"'{LOG_CHANNEL_NAME}' 이름의 텍스트 채널을 찾을 수 없어. "
            f"그 이름으로 채널을 만들어줘. (이름은 LOG_CHANNEL_NAME 환경변수로 바꿀 수 있어)"
        )
        return

    channel = ctx.author.voice.channel

    # 이전에 꼬인 연결이 남아있으면 먼저 정리
    existing_vc = ctx.guild.voice_client
    if existing_vc is not None:
        try:
            existing_vc.stop_recording()
        except Exception:
            pass
        try:
            await existing_vc.disconnect(force=True)
        except Exception:
            pass
        await asyncio.sleep(1)

    try:
        vc = await channel.connect(timeout=20, reconnect=False)
    except discord.errors.ClientException as e:
        await ctx.send(f"음성 연결 실패: {e}")
        return

    # 연결이 실제로 준비될 때까지 잠깐 재시도 (최대 5초)
    for _ in range(10):
        if vc.is_connected():
            break
        await asyncio.sleep(0.5)
    else:
        await ctx.send("음성 연결이 안정적으로 안 잡혔어. (네트워크/UDP 문제일 수 있음)")
        await vc.disconnect(force=True)
        return

    async def on_segment(user_id: int, pcm_bytes: bytes):
        member = ctx.guild.get_member(user_id)
        name = member.display_name if member else f"알수없음({user_id})"

        async with transcribe_sem:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, transcribe_pcm, pcm_bytes)

        if text:
            await log_channel.send(f"{name}: ({text})")

    def finished_callback(sink, *args):
        # vc.stop_recording() 호출 시 (leave) 실행됨. 특별히 할 일 없음.
        pass

    try:
        vc.start_recording(SpeakingSink(on_segment=on_segment), finished_callback)
    except discord.sinks.errors.RecordingException as e:
        await ctx.send(f"녹음 시작 실패: {e}")
        await vc.disconnect(force=True)
        return

    await ctx.send(f"`{channel.name}` 음성 채널에 들어가서 음성 로그를 시작할게.")


@bot.command()
async def leave(ctx: commands.Context):
    vc = ctx.guild.voice_client
    if vc is None:
        await ctx.send("지금 음성 채널에 들어가 있지 않아.")
        return

    vc.stop_recording()
    await vc.disconnect()
    await ctx.send("나갈게.")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN 환경변수가 설정되어 있지 않아.")

    start_keepalive_server()
    bot.run(TOKEN)
