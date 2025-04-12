import asyncio
import random
from telethon import TelegramClient, errors

# ---------- 텔레그램 API 설정 ----------
API_ID = 22812286                      # 제공하신 API ID
API_HASH = "90d7da817bbbb92373f69e794efaba7a"  # 제공하신 API HASH
PHONE_NUMBER = "+819051251446"          # 제공하신 전화번호 (국제 형식)

# 홍보 계정 (공개 username 사용: 예시 '@cuz_z')
SOURCE_CHAT = "@cuz_z"               

# 각 그룹 전송 후 짧은 딜레이 (초)
MIN_DELAY = 5
MAX_DELAY = 10

client = TelegramClient("user_session", API_ID, API_HASH)

async def forward_message_to_all_groups():
    # 시작 시 홍보 계정에서 최대 6개의 메시지를 불러옵니다.
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

    # 가입된 대화 목록 중 채널을 제외한 그룹만 가져오기
    dialogs = await client.get_dialogs()
    groups = [d for d in dialogs if d.is_group]
    total_groups = len(groups)
    print(f"총 {total_groups}개의 그룹에 전달을 시작합니다.")

    msg_index = 0
    num_msgs = len(msgs)
    group_counter = 0  # 현재 사이클에서 전송한 그룹 수

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
                # 순환 방식으로 메시지를 선택합니다.
                src_msg = msgs[msg_index % num_msgs]
                await client.forward_messages(group.id, src_msg.id, from_peer=SOURCE_CHAT)
                print(f"그룹 '{group.name}' ({group.id}) 에 {msg_index % num_msgs + 1}번째 메시지 전달 성공")
                msg_index += 1
                group_counter += 1

                # 각 그룹 전송 후 5~10초 짧은 딜레이
                await asyncio.sleep(random.randint(MIN_DELAY, MAX_DELAY))

                # 매 4개 그룹마다 긴 휴식: 20~60초 딜레이
                if group_counter % 4 == 0:
                    longer_delay = random.randint(20, 60)
                    print(f"그룹 {group_counter}번째 전송 완료. {longer_delay}초 동안 긴 휴식합니다.")
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
                print(f"그룹 '{group.name}' ({group.id}) 에 전달 실패: {e}")
                await asyncio.sleep(5)
                continue

        # 모든 그룹 순회 완료 후 한 사이클로 간주합니다.
        print("전체 그룹 순회 완료. 5~10분 동안 휴식 후 홍보 메시지를 업데이트합니다.")
        await asyncio.sleep(random.randint(300, 600))
        try:
            new_msgs = await client.get_messages(SOURCE_CHAT, limit=6)
            if new_msgs:
                msgs = new_msgs
                num_msgs = len(msgs)
                # 새로운 메시지 목록으로 업데이트하되 msg_index는 그대로 유지하거나,
                # 만약 msg_index가 현재 새로운 메시지 수보다 크다면 modulo 연산으로 조정합니다.
                msg_index = msg_index % num_msgs
                print("홍보 메시지를 업데이트했습니다. 다음 메시지는 전체 순회에서 이어집니다.")
            else:
                print("새로운 홍보 메시지가 없으므로, 기존 메시지를 계속 사용합니다.")
        except Exception as e:
            print("홍보 메시지 업데이트 실패:", e)
            # 업데이트 실패 시 기존 메시지를 계속 사용합니다.

async def main():
    print("텔레그램에 로그인 중...")
    await client.start(phone=PHONE_NUMBER)
    print("로그인 완료. 자연스러운 패턴으로 영구적으로 메시지를 전달합니다.")
    await forward_message_to_all_groups()

if __name__ == "__main__":
    asyncio.run(main())