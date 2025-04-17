import asyncio
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from telethon import TelegramClient, errors
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.functions.channels import GetFullChannelRequest

# ─── 설정 ─────────────────────────────────────────
API_ID      = 22134537
API_HASH    = "6651ed74d2bbea1d86d7dc6d2cdf087d"
PHONE       = "+818095235397"
SOURCE_CHAT = "@cuz_z"            # Saved Messages
SESSION     = "promo_session"     # .session 파일명

# ─── 딜레이 설정 ───────────────────────────────────
MIN_DELAY = 5      # 그룹당 최소 5초
MAX_DELAY = 10     # 그룹당 최대 10초

DAY_MIN    = 20    # 낮(07–02시) 사이클 최소 20분
DAY_MAX    = 60    # 낮(07–02시) 사이클 최대 60분
NIGHT_MIN  = 60    # 새벽(02–07시) 사이클 최소 60분
NIGHT_MAX  = 120   # 새벽(02–07시) 사이클 최대 120분

REACT_PROB = 0.1
REACTIONS  = ['👍','❤️','😂','🤔']

JST = ZoneInfo("Asia/Tokyo")

# ─── Telethon 클라이언트 & 메시지 커서 ─────────────────
client = TelegramClient(SESSION, API_ID, API_HASH)
msg_cursor = 0

def now():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

async def forward_cycle():
    global msg_cursor

    # 1) 모드 로그
    hour = datetime.now(JST).hour
    mode = "새벽(02–07시)" if 2 <= hour < 7 else "낮(07–02시)"
    print(f"{now()} [MODE] {mode} 모드 시작")

    # 2) 저장 메시지 로드
    msgs = await client.get_messages(SOURCE_CHAT, limit=6)
    if not msgs:
        print(f"{now()} [WARN] 저장된 메시지 없음 → 사이클 스킵\n")
        return

    # 3) 그룹 필터링 (채널 제외)
    dialogs = await client.get_dialogs()
    groups = [d for d in dialogs if d.is_group]
    random.shuffle(groups)
    print(f"{now()} ▶ 사이클 시작: 메시지 {len(msgs)}개 → 그룹 {len(groups)}개")

    # 4) 그룹별 처리
    for d in groups:
        gid = d.id

        # --- 슬로우모드 체크 ---
        slow_secs = 0
        try:
            ent = d.entity
            if getattr(ent, "megagroup", False):
                full = await client(GetFullChannelRequest(channel=gid))
            else:
                full = await client(GetFullChatRequest(chat_id=gid))
            slow_secs = full.slow_mode_seconds
        except Exception:
            slow_secs = 0

        if slow_secs > 0:
            last = await client.get_messages(gid, limit=1)
            if last:
                delta = (datetime.now(JST) - last[0].date).total_seconds()
                if delta < slow_secs:
                    print(f"{now()} [SKIP] {d.name or gid}: 슬로우모드 {slow_secs}s 제한, 마지막 메시지 {delta:.0f}s 전 → 건너뜁니다.")
                    continue
        # --- 슬로우모드 체크 끝 ---

        # a) 읽음 처리
        try:
            await client.send_read_acknowledge(gid)
        except Exception:
            pass

        # b) 가끔 리액션
        if random.random() < REACT_PROB:
            last = await client.get_messages(gid, limit=1)
            if last:
                try:
                    await client.send_reaction(gid, last[0].id, random.choice(REACTIONS))
                    print(f"{now()} [REACT] {d.name or gid} msg {last[0].id}")
                    await asyncio.sleep(random.uniform(1,2))
                except Exception as e:
                    print(f"{now()} [REACT ERR] {d.name or gid}: {e}")

        # c) 포워드
        msg = msgs[msg_cursor % len(msgs)]
        msg_cursor += 1
        try:
            await client.forward_messages(gid, [msg.id], from_peer=SOURCE_CHAT)
            print(f"{now()} [OK] {d.name or gid} ← msg {msg.id}")
        except errors.FloodWaitError as f:
            print(f"{now()} [FLOOD] {d.name or gid} 대기 {f.seconds}s")
            await asyncio.sleep(f.seconds + 1)
        except Exception as e:
            print(f"{now()} [ERR] {d.name or gid}: {e}")

        # d) 그룹당 딜레이 (5~10초)
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        print(f"{now()}    -- 그룹 딜레이: {delay:.1f}s --")
        await asyncio.sleep(delay)

    print(f"{now()} ◀ 사이클 완료\n")

async def main():
    print(f"{now()} 로그인 중…")
    await client.start(phone=PHONE)
    print(f"{now()} 로그인 완료, 루프 진입\n")

    while True:
        await forward_cycle()

        # 사이클 레벨 딜레이 로그 & 계산
        hour = datetime.now(JST).hour
        if 2 <= hour < 7:
            dmin, dmax = NIGHT_MIN, NIGHT_MAX
            print(f"{now()} [MODE] (휴식 전) 새벽 모드 유지")
        else:
            dmin, dmax = DAY_MIN, DAY_MAX
            print(f"{now()} [MODE] (휴식 전) 낮 모드 유지")

        cycle_delay = random.uniform(dmin, dmax) * 60
        print(f"{now()} [휴식] 다음 사이클까지 {cycle_delay/60:.1f}분 대기\n")
        await asyncio.sleep(cycle_delay)

if __name__ == "__main__":
    asyncio.run(main())