import asyncio
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from telethon import TelegramClient, errors
from telethon.errors.rpcerrorlist import SlowModeWaitError
from telethon.tl.functions.messages import GetFullChatRequest, SendReactionRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import ChatReactionsAll, ChatReactionsSome

# ─── 설정 ─────────────────────────────────────────
API_ID      = 22134537
API_HASH    = "6651ed74d2bbea1d86d7dc6d2cdf087d"
PHONE       = "+818095235397"
SOURCE_CHAT = "@cuz_z"            # Saved Messages 로 사용할 채팅
SESSION     = "promo_session"     # .session 파일명

# ─── 딜레이 설정 ───────────────────────────────────
MIN_DELAY = 5      # 그룹당 최소 5초
MAX_DELAY = 10     # 그룹당 최대 10초

DAY_MIN, DAY_MAX     = 20, 60    # 낮 모드 사이클(분)
NIGHT_MIN, NIGHT_MAX = 60, 120   # 새벽 모드 사이클(분)

REACT_PROB = 0.1
REACTIONS  = ['👍', '❤️', '😂', '🤔']

# 일본 표준시
JST = ZoneInfo("Asia/Tokyo")

# Telethon 클라이언트
client = TelegramClient(SESSION, API_ID, API_HASH)

# 그룹별 메시지 순환 커서
group_msg_cursor = {}

def now():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

async def forward_cycle():
    # 모드 판단 & 로그
    hour = datetime.now(JST).hour
    mode = "새벽(02–07시)" if 2 <= hour < 7 else "낮(07–02시)"
    print(f"{now()} [MODE] {mode} 사이클 시작")

    # 저장 메시지 7개 로드
    msgs = await client.get_messages(SOURCE_CHAT, limit=7)
    if not msgs:
        print(f"{now()} [WARN] 저장된 메시지 없음 → 사이클 스킵\n")
        return
    num_msgs = len(msgs)

    # 채널 제외한 그룹 목록 & 랜덤 셔플
    dialogs = await client.get_dialogs()
    groups = [d for d in dialogs if d.is_group]
    random.shuffle(groups)
    print(f"{now()} ▶ 메시지 {num_msgs}개 → 그룹 {len(groups)}개 대상")

    for d in groups:
        gid = d.id

        # (1) 슬로우모드 조회
        slow_secs = 0
        try:
            ent = d.entity
            if getattr(ent, "megagroup", False):
                full = await client(GetFullChannelRequest(channel=gid))
            else:
                full = await client(GetFullChatRequest(chat_id=gid))
            slow_secs = full.full_chat.slow_mode_seconds
        except:
            slow_secs = 0

        # (2) 슬로우모드 스킵
        if slow_secs > 0:
            last = await client.get_messages(gid, limit=1)
            if last:
                delta = (datetime.now(JST) - last[0].date).total_seconds()
                if delta < slow_secs:
                    print(f"{now()} [SKIP] {d.name or gid}: 슬로우모드 {slow_secs}s, 마지막 메시지 {delta:.0f}s 전")
                    continue

        # (3) 읽음 처리
        try:
            await client.send_read_acknowledge(gid)
        except:
            pass

        # (4) 가끔 리액션
        if random.random() < REACT_PROB:
            try:
                if getattr(ent, "megagroup", False):
                    full = await client(GetFullChannelRequest(channel=gid))
                else:
                    full = await client(GetFullChatRequest(chat_id=gid))
                allowed = full.full_chat.available_reactions

                if isinstance(allowed, ChatReactionsSome):
                    choices = allowed.reactions
                elif isinstance(allowed, ChatReactionsAll):
                    choices = REACTIONS
                else:
                    choices = []

                last = await client.get_messages(gid, limit=1)
                if last and choices:
                    emoji = random.choice(choices)
                    await client(SendReactionRequest(peer=gid, msg_id=last[0].id, reaction=emoji))
                    print(f"{now()} [REACT] {d.name or gid} 메시지 {last[0].id}에 '{emoji}'")
                    await asyncio.sleep(random.uniform(1,2))
            except Exception as e:
                print(f"{now()} [REACT ERR] {d.name or gid}: {type(e).__name__} {e}")

        # (5) 그룹별 순환 메시지 선택
        idx = group_msg_cursor.get(gid, 0) % num_msgs
        msg = msgs[idx]
        group_msg_cursor[gid] = idx + 1  # 다음 사이클에는 다음 메시지

        # (6) 포워드
        try:
            await client.forward_messages(gid, [msg.id], from_peer=SOURCE_CHAT)
            print(f"{now()} [OK] {d.name or gid} ← msg {msg.id}")
        except SlowModeWaitError as sm:
            print(f"{now()} [SLOWMODE-SKIP] {d.name or gid}: {sm.seconds}s 대기 필요 → 건너뜁니다.")
            continue
        except errors.FloodWaitError as f:
            print(f"{now()} [FLOOD-SKIP] {d.name or gid}: {f.seconds}s 대기 필요 → 건너뜁니다.")
            continue
        except Exception as e:
            print(f"{now()} [ERR] {d.name or gid}: {type(e).__name__} {e}")

        # (7) 그룹당 딜레이
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        print(f"{now()}    -- 그룹 딜레이: {delay:.1f}s --")
        await asyncio.sleep(delay)

    print(f"{now()} ◀ 사이클 완료\n")

async def main():
    print(f"{now()} 로그인 중…")
    await client.start(phone=PHONE)
    print(f"{now()} 로그인 완료, 자동 사이클 진입\n")

    while True:
        await forward_cycle()

        # 사이클 휴식 모드 재판단
        hour = datetime.now(JST).hour
        if 2 <= hour < 7:
            dmin, dmax = NIGHT_MIN, NIGHT_MAX
            mode = "새벽(02–07시)"
        else:
            dmin, dmax = DAY_MIN, DAY_MAX
            mode = "낮(07–02시)"

        print(f"{now()} [MODE] (휴식 전) {mode} 모드 유지")
        cycle_delay = random.uniform(dmin, dmax) * 60
        print(f"{now()} [휴식] 다음 사이클까지 {cycle_delay/60:.1f}분 대기\n")
        await asyncio.sleep(cycle_delay)

if __name__ == "__main__":
    asyncio.run(main())