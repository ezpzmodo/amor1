import asyncio
import random
import time
from telethon import TelegramClient, errors

# ---------- 텔레그램 API 설정 ----------
API_ID = 25354866  # 업데이트된 API ID
API_HASH = "5651defc5904cee453e36e3bbc5b158d"  # 업데이트된 API HASH
PHONE_NUMBER = "+818092009533"  # 업데이트된 전화번호 (국제 형식)

# 홍보 계정: 공개 username (예시)
SOURCE_CHAT = "@cuz_z"  # 필요에 따라 변경 가능

# 각 그룹 전송 후 짧은 딜H레이 (초)
MIN_DELAY = 5
MAX_DELAY = 10

# Telethon 클라이언트 생성 (세션 파일 이름: promo_session)
client = TelegramClient("promo_session", API_ID, API_HASH)

async def forward_message_to_all_groups():
    # 시작 시 홍보 계정에서 최대 6개의 메시지를 불러옴.
    try:
        msgs = await client.get_messages(SOURCE_CHAT, limit=6)
    except Exception as e:
        print("홍보 계정 메시지 불러오기 실패:", e)
        return

    if not msgs:
        print("홍보 계정에서 메시지를 찾을 수 없습니다.")
        return

    print("홍보 계정에서 가져온 메시지:")
    for idx, msg in enumerate(msgs):
        print(f"  {idx+1}번째 메시지 ID: {msg.id}")

    # 가입된 대화 목록에서 채널은 제외한 그룹만 가져오기
    dialogs = await client.get_dialogs()
    groups = [d for d in dialogs if d.is_group]
    total_groups = len(groups)
    print(f"총 {total_groups}개의 그룹에 전달을 시작합니다.")

    msg_index = 0
    num_msgs = len(msgs)
    group_counter = 0  # 현재 사이클에서 전송한 그룹 수
    cycle_counter = 0  # 전체 순회 사이클 수

    while True:
        # 모든 그룹 순회: 각 그룹에 대해 메시지 전송
        for group in groups:
            if not client.is_connected():
                print("연결이 끊어졌습니다. 재연결 시도...")
                try:
                    await client.connect()
                    print("재연결 성공!")
                except Exception as e:
                    print("재연결 실패:", e)
                    await asyncio.sleep(10)
                    continue

            try:
                # 저장된 홍보 메시지 리스트에서 순환 방식으로 선택
                src_msg = msgs[msg_index % num_msgs]
                await client.forward_messages(group.id, src_msg.id, from_peer=SOURCE_CHAT)
                print(f"그룹 '{group.name}' ({group.id}) 에 {msg_index % num_msgs + 1}번째 메시지 전송 성공")
                msg_index += 1
                group_counter += 1

                # 각 그룹 전송 후 5~10초 짧은 딜레이 적용
                await asyncio.sleep(random.randint(MIN_DELAY, MAX_DELAY))

                # 매 4개 그룹마다 긴 휴식 (20~60초)
                if group_counter % 4 == 0:
                    longer_delay = random.randint(20, 60)
                    print(f"{group_counter}개 그룹 전송 완료. {longer_delay}초 동안 긴 휴식합니다.")
                    await asyncio.sleep(longer_delay)

            except errors.FloodWaitError as fwe:
                print(f"FloodWaitError 발생: {fwe.seconds}초 대기합니다.")
                await asyncio.sleep(fwe.seconds + 1)
            except errors.TypeNotFoundError as tne:
                print("TypeNotFoundError 발생:", tne)
                print("세션 또는 API 불일치로 판단됩니다. 10초 후 재연결 시도합니다.")
                await asyncio.sleep(10)
                try:
                    await client.disconnect()
                    await client.connect()
                except Exception as e:
                    print("재연결 실패:", e)
                    await asyncio.sleep(10)
                continue
            except Exception as e:
                print(f"그룹 '{group.name}' ({group.id}) 에 전송 실패: {e}")
                await asyncio.sleep(5)
                continue

        # 전체 그룹 순회 완료 → 한 사이클 종료
        cycle_counter += 1
        print(f"전체 그룹 순회 사이클 {cycle_counter} 완료.")
        # 한 사이클마다 5~10분(300~600초) 휴식
        normal_break = random.randint(300, 600)
        print(f"한 사이클 후 {normal_break/60:.1f}분 동안 휴식합니다.")
        await asyncio.sleep(normal_break)

        # 4 사이클마다 추가 장기 휴식 (30~60분)
        if cycle_counter % 4 == 0:
            extended_break = random.randint(1800, 3600)
            print(f"사이클 {cycle_counter} 도달. 추가 장기 휴식: {extended_break/60:.1f}분")
            await asyncio.sleep(extended_break)

        # 홍보 메시지 업데이트: 이전 사이클에서 이어서 전송하도록 msg_index 유지
        try:
            new_msgs = await client.get_messages(SOURCE_CHAT, limit=6)
            if new_msgs:
                msgs = new_msgs
                num_msgs = len(msgs)
                msg_index = msg_index % num_msgs  # msg_index를 새 메시지 수에 맞게 조정
                print("홍보 메시지를 업데이트했습니다. 이어서 전송합니다.")
            else:
                print("새로운 홍보 메시지가 없으므로, 기존 메시지를 계속 사용합니다.")
        except Exception as e:
            print("홍보 메시지 업데이트 실패:", e)
            # 업데이트 실패 시 기존 메시지 계속 사용

async def main():
    print("텔레그램에 로그인 중...")
    await client.start(PHONE_NUMBER)
    print("로그인 완료. 자연스러운 전송 패턴으로 메시지를 전송합니다.")
    await forward_message_to_all_groups()

if __name__ == "__main__":
    asyncio.run(main())