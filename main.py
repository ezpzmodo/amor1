import asyncio
import random
from telethon import TelegramClient

# ---------- 텔레그램 API 설정 ----------
API_ID = 27619640               # 실제 API_ID로 변경
API_HASH = "d6a2472bde05ce8bd785047c6f80217f"      # 실제 API_HASH로 변경
PHONE_NUMBER = "+818083586377"        # 실제 전화번호(국제 형식)로 변경

# 홍보 계정 : 이 계정에 미리 보내둔 메시지를 가져옵니다.
# 여기에는 홍보 계정의 username, 채널 id 또는 전화번호 등을 사용할 수 있습니다.
SOURCE_CHAT = "@cuz_z"             

# 각 그룹 전송 후 대기 시간 (초)
MIN_DELAY = 5
MAX_DELAY = 10

# 사용자 계정으로 사용하므로 세션 이름은 "user_session" 등으로 설정합니다.
client = TelegramClient("user_session", API_ID, API_HASH)

async def forward_message_to_all_groups():
    # 홍보 계정에서 최근 최대 6개의 메시지 불러오기
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

    # 순차 전달을 위한 인덱스 초기화 (순서대로 메시지 사용)
    msg_index = 0
    num_msgs = len(msgs)
    
    # 영구 무한 반복: 그룹 리스트 전체를 순회하며 메시지를 전달
    while True:
        for group in groups:
            try:
                # 순차적으로 메시지를 선택합니다. 예) 1번째 메시지, 2번째 메시지, …, 다시 1번째 메시지...
                src_msg = msgs[msg_index % num_msgs]
                await client.forward_messages(group.id, src_msg.id, from_peer=SOURCE_CHAT)
                print(f"그룹 '{group.name}' ({group.id}) 에 {msg_index % num_msgs + 1}번째 메시지 전달 성공")
                msg_index += 1
            except Exception as e:
                print(f"그룹 '{group.name}' ({group.id}) 에 전달 실패: {e}")
            # 각 그룹 전송 후 5~10초 랜덤 딜레이
            delay = random.randint(MIN_DELAY, MAX_DELAY)
            await asyncio.sleep(delay)

async def main():
    print("텔레그램에 로그인 중...")
    # 일반 사용자 계정으로 로그인 (첫 실행 시 OTP 인증 필요)
    await client.start(phone=PHONE_NUMBER)
    print("로그인 완료. 영구적으로 메시지를 전달합니다.")
    await forward_message_to_all_groups()

if __name__ == "__main__":
    asyncio.run(main())