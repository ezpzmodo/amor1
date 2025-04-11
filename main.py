import asyncio
import random
from telethon import TelegramClient, errors

# ---------- 텔레그램 API 설정 ----------
API_ID =  27619640                     # 실제 API_ID로 변경
API_HASH = "d6a2472bde05ce8bd785047c6f80217f"      # 실제 API_HASH로 변경
PHONE_NUMBER = "+818083586377"       # 실제 전화번호(국제 형식)로 변경

# 홍보 계정: 이 계정에 미리 보내둔 메시지를 가져옵니다.
# 공개 username을 사용하는 경우 '@username' 형태로 사용
SOURCE_CHAT = "@cuz_z"               

# 각 그룹 전송 후 대기 시간 (초)
MIN_DELAY = 20
MAX_DELAY = 30

client = TelegramClient("user_session", API_ID, API_HASH)

async def forward_message_to_all_groups():
    # 홍보 계정에서 최대 6개의 메시지를 불러옵니다.
    msgs = await client.get_messages(SOURCE_CHAT, limit=6)
    if not msgs:
        print("홍보 계정에서 메시지를 찾을 수 없습니다.")
        return

    print("홍보 계정에서 가져온 메시지:")
    for idx, msg in enumerate(msgs):
        print(f"{idx+1}번째 메시지 ID: {msg.id}")

    # 가입한 모든 대화(그룹 및 채널) 목록 불러오기
    dialogs = await client.get_dialogs()
    groups = [d for d in dialogs if d.is_group or d.is_channel]
    print(f"총 {len(groups)}개의 그룹/채널에 전달을 시작합니다.")

    msg_index = 0
    num_msgs = len(msgs)

    # 무한 반복: 전체 그룹 순회 후 다시 반복
    while True:
        for group in groups:
            # 연결 상태 확인: 연결 끊김 시 재연결 시도
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
                # 순차적으로 메시지를 선택 (리스트 순환)
                src_msg = msgs[msg_index % num_msgs]
                await client.forward_messages(group.id, src_msg.id, from_peer=SOURCE_CHAT)
                print(f"그룹 '{group.name}' ({group.id}) 에 {msg_index % num_msgs + 1}번째 메시지 전달 성공")
                msg_index += 1

                # 각 그룹 전송 후 랜덤 대기
                delay = random.randint(MIN_DELAY, MAX_DELAY)
                await asyncio.sleep(delay)

            except errors.FloodWaitError as fwe:
                # FloodWaitError 발생 시 지정된 시간 만큼 대기
                print(f"FloodWaitError 발생: {fwe.seconds}초 대기합니다.")
                await asyncio.sleep(fwe.seconds + 1)
            except errors.TypeNotFoundError as tne:
                # TLObject 관련 파싱 오류 발생 시 추가 대기 후, 재연결 시도
                print("TypeNotFoundError 발생:", tne)
                print("세션 혹은 API 불일치로 판단됩니다. 10초 대기 후 재연결을 시도합니다.")
                await asyncio.sleep(10)
                try:
                    await client.disconnect()
                    await client.connect()
                except Exception as e:
                    print("재연결 실패:", e)
                    await asyncio.sleep(10)
                continue
            except Exception as e:
                # 그 외 모든 오류 발생 시 간단히 출력 후 다음 그룹으로 이동
                print(f"그룹 '{group.name}' ({group.id}) 에 전달 실패: {e}")
                await asyncio.sleep(5)
                continue
        # 모든 그룹 순회 후 짧게 휴식
        await asyncio.sleep(30)

async def main():
    print("텔레그램에 로그인 중...")
    await client.start(phone=PHONE_NUMBER)  # OTP 인증이 필요한 경우 최초 실행 시 진행
    print("로그인 완료. 영구적으로 메시지를 전달합니다.")
    await forward_message_to_all_groups()

if __name__ == "__main__":
    asyncio.run(main())