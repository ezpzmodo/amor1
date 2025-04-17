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
SOURCE_CHAT = "@cuz_z"            # Saved Messages
SESSION     = "promo_session"     # .session 파일명

# ─── 딜레이 & 사이클 설정 ───────────────────────────
MIN_DELAY = 5      # 그룹당 대기 5~10초
MAX_DELAY = 10

DAY_MIN, DAY_MAX     = 20, 60    # 낮 모드 사이클(분)
NIGHT_MIN, NIGHT_MAX = 60, 120   # 새벽 모드 사이클(분)

REACT_PROB = 0.1     # 10% 확률로 리액션
REACTIONS  = ['👍','❤️','😂','🤔']

JST = ZoneInfo("Asia/Tokyo")

# Telethon 클라이언트 준비
client = TelegramClient(SESSION, API_ID, API_HASH)

# 그룹별 메시지 인덱스 & 첫 사이클 플래그
group_msg_cursor = {}
is_first_cycle = True

def now():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

async def forward_cycle():
    global is_first_cycle

    # 1) 시간대 판단
    hour = datetime.now(JST).hour
    mode = "새벽(02–07시)" if 2 <= hour < 7 else "낮(07–02시)"
    print(f"{now()} [MODE] {mode} 사이클 시작")

    # 2) 홍보 메시지 로드 (최대 7개)
    msgs = await client.get_messages(SOURCE_CHAT, limit=7)
    if not msgs:
        print(f"{now()} [WARN] 저장된 메시지 없음 → 사이클 스킵\n")
        return
    num_msgs = len(msgs)

    # 3) 그룹 목록 불러오기 & 랜덤 섞기 (채널 제외)
    dialogs = await client.get_dialogs()
    groups = [d for d in dialogs if d.is_group]
    random.shuffle(groups)
    print(f"{now()} ▶ 메시지 {num_msgs}개 → 그룹 {len(groups)}개 처리")

    # 4) 첫 사이클에만 “순차 배정”
    if is_first_cycle:
        for idx, d in enumerate(groups):
            group_msg_cursor[d.id] = idx % num_msgs
        is_first_cycle = False

    # 5) 그룹별 전송
    for d in groups:
        gid = d.id

        # 신규 그룹 초기화
        if gid not in group_msg_cursor:
            group_msg_cursor[gid] = 0

        # 5-1) 슬로우모드 조회
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

        # 5-2) 슬로우모드 시간 남으면 “커서만 +1” 하고 스킵
        if slow_secs > 0:
            last = await client.get_messages(gid, limit=1)
            if last:
                delta = (datetime.now(JST) - last[0].date).total_seconds()
                if delta < slow_secs:
                    # **여기서 커서를 올려 주고** 스킵
                    old_idx = group_msg_cursor[gid]
                    group_msg_cursor[gid] = (old_idx + 1) % num_msgs
                    print(f"{now()} [SLOW-SKIP] {d.name or gid}: 슬로우모드 {slow_secs}s 남음(마지막 {delta:.0f}s 전) → 다음 메시지로 이동")
                    continue

        # 5-3) 읽음 처리
        try:
            await client.send_read_acknowledge(gid)
        except:
            pass

        # 5-4) 가끔 리액션
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
                    print(f"{now()} [REACT] {d.name or gid} msg {last[0].id}에 '{emoji}'")
                    await asyncio.sleep(random.uniform(1,2))
            except Exception as e:
                print(f"{now()} [REACT ERR] {d.name or gid}: {e}")

        # 5-5) 메시지 선택 & 커서 증가 (성공 여부와 상관없이 이미 +1 해 두었으니,
        #        여긴 “현재 인덱스”로만 선택)
        idx = group_msg_cursor[gid]
        msg = msgs[idx]
        group_msg_cursor[gid] = (idx + 1) % num_msgs

        # 5-6) 메시지 포워드
        try:
            await client.forward_messages(gid, [msg.id], from_peer=SOURCE_CHAT)
            print(f"{now()} [OK] {d.name or gid} ← msg {msg.id}")
        except SlowModeWaitError as sm:
            print(f"{now()} [SLOWMODE-SKIP] {d.name or gid}: {sm.seconds}s 필요 → 스킵")
        except errors.FloodWaitError as f:
            print(f"{now()} [FLOOD-SKIP] {d.name or gid}: {f.seconds}s 필요 → 스킵")
        except Exception as e:
            print(f"{now()} [ERR] {d.name or gid}: {e}")

        # 5-7) 그룹당 딜레이
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        print(f"{now()}    -- 딜레이: {delay:.1f}s --")
        await asyncio.sleep(delay)

    print(f"{now()} ◀ 사이클 완료\n")

async def main():
    print(f"{now()} 로그인 중…")
    await client.start(phone=PHONE)
    print(f"{now()} 로그인 완료, 자동 사이클 진입\n")

    while True:
        await forward_cycle()

        # 6) 다음 사이클 휴식 모드 판단
        hour = datetime.now(JST).hour
        if 2 <= hour < 7:
            dmin, dmax = NIGHT_MIN, NIGHT_MAX
            mode = "새벽(02–07시)"
        else:
            dmin, dmax = DAY_MIN, DAY_MAX
            mode = "낮(07–02시)"

        print(f"{now()} [MODE] (휴식 전) {mode} 모드")
        cycle_delay = random.uniform(dmin, dmax) * 60
        print(f"{now()} [휴식] 다음 사이클까지 {cycle_delay/60:.1f}분 대기\n")
        await asyncio.sleep(cycle_delay)

if __name__ == "__main__":
    asyncio.run(main())