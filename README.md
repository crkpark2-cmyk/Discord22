# 디스코드 음성 로그 봇

음성 채널에서 누가 말하면, 텍스트 채널(`음성-로그`)에
`닉네임: (말한 내용)` 형태로 계속 기록해주는 봇.

- STT: **Groq API** (무료, 클라우드 호출, whisper-large-v3 기반, 한국어+영어 자동 인식)
- 동작 방식: 유저별로 오디오를 듣다가 약 0.8초 이상 무음이 생기면
  그 구간을 하나의 발화로 잘라서 텍스트로 변환 후 전송. `!join`이 호출된
  동안 계속 반복됨 (음성채팅 하는 내내 동작).

로컬에 STT 모델을 올리지 않고 API로 호출하기 때문에 서버 메모리 부담이
거의 없음 (Railway/Render 가장 저렴한 인스턴스로도 충분).

## 1. Groq API 키 발급 (무료)

1. https://console.groq.com 가입
2. API Keys 메뉴 → Create API Key
3. 발급된 키를 `GROQ_API_KEY`로 사용

(무료 티어 한도가 있긴 하지만 일반적인 음성채팅 로그 용도로는 충분함.
 한도 초과 시 `transcriber.py`에서 오류 로그만 찍히고 봇은 죽지 않음.)

## 2. 디스코드 봇 준비 (Developer Portal)

1. https://discord.com/developers/applications 에서 New Application
2. Bot 탭 → Reset Token으로 토큰 발급 → `DISCORD_TOKEN`으로 사용
3. Bot 탭에서 **SERVER MEMBERS INTENT** 켜기
4. OAuth2 → URL Generator
   - Scopes: `bot`
   - Bot Permissions: `View Channels`, `Send Messages`, `Connect`, `Speak`
   - 생성된 URL로 서버에 봇 초대
5. 서버에 **텍스트 채널 `음성-로그`** 만들어두기 (이름은 `LOG_CHANNEL_NAME` 환경변수로 변경 가능)

## 3. 배포 (Railway 또는 Render, 로컬 실행 불필요)

이 폴더 전체를 GitHub 저장소에 push.

### Railway

1. railway.app → New Project → Deploy from GitHub repo
2. Dockerfile 자동 인식됨
3. Variables 탭에서 추가:
   - `DISCORD_TOKEN`
   - `GROQ_API_KEY`
   - `GROQ_WHISPER_MODEL` = whisper-large-v3-turbo (기본값, 그대로 둬도 됨)
   - `LOG_CHANNEL_NAME` = 음성-로그
4. Deploy

### Render

1. New → Web Service → GitHub repo 선택, Environment: Docker
2. Environment Variables에 위와 동일하게 입력
3. Deploy
   (`render.yaml`이 포함되어 있어서 Blueprint로도 한 번에 띄울 수 있음)

## 4. 사용법

- 음성 채널에 들어간 상태에서 텍스트 채널에 `!join` 입력
  → 봇이 그 음성 채널에 들어와서 듣기 시작, 누가 말하면 `음성-로그` 채널에 기록
- `!leave` → 봇이 나가고 기록 중단

## 주의사항

- **무음 판단 민감도**: `sink.py`의 `silence_thresh`(기본 500) 값은 마이크/환경에 따라
  너무 민감하거나 둔감할 수 있음. 로그가 너무 잘게 끊기거나, 말이 끝나도 한참 안 끊기면
  이 값과 `silence_duration`(기본 0.8초)을 조절하면 됨.
- **여러 명이 동시에 말할 때**: 화자별로 버퍼가 분리되어 있어 각자 따로 인식되지만,
  Groq API 호출은 한 번에 하나씩만 처리하도록(세마포어) 막아놔서 여러 명이
  동시에 계속 말하면 로그가 살짝 밀려서(지연되어) 올라올 수 있음.
- **API 키 노출 주의**: `GROQ_API_KEY`는 절대 코드에 직접 적지 말고 환경변수로만 관리할 것.
- **봇 재시작 시**: 음성 채널에서 자동으로 다시 `!join`되지는 않음. 재시작 후엔
  다시 `!join`을 입력해줘야 함.

## 파일 구성

```
bot.py            # 메인 봇 (명령어, 음성 연결/해제)
sink.py           # 유저별 오디오 버퍼링 + 무음 감지로 발화 구간 분리
transcriber.py    # Groq API로 PCM -> 텍스트 변환
keep_alive.py     # Render 등에서 헬스체크용으로 쓰는 더미 HTTP 서버 (Railway에선 없어도 됨)
Dockerfile        # ffmpeg/libopus 등 시스템 패키지 포함한 빌드 환경
render.yaml       # Render Blueprint 설정
requirements.txt  # 파이썬 패키지 목록
.env.example      # 환경변수 예시
```
