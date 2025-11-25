# component/config.py

# FPS
FPS = 60

# 셰이커 관련
SHAKE_THRESHOLD = 1.0          # 이 이상 흔들면 MOVING 모드로
POUR_START_ANGLE = -30.0       # 이 각도보다 많이 기울어야 따르기 시작
POUR_MAX_ANGLE = -110.0        # 완전 기울였을 때 기준

MAX_SHAKER_VOLUME = 4.0        # 셰이커 안 총 칵테일량
VOLUME_PER_PARTICLE = 0.004    # 입자 하나가 소모하는 양

# 잔 관련
GLASS_FILL_PER_PARTICLE = 0.01  # 입자 하나로 잔이 차는 양 (감성 맞춰 조정)

# 잔 최대 용량 (셰이커랑 1:1로 맞추고 싶으면 같게 두면 됨)
GLASS_CAPACITY = MAX_SHAKER_VOLUME

# 물줄기 두께 / 흔들림 관련
STREAM_BASE_WIDTH = 4          # 기본 두께 (원래 2였다면 대충 5배 느낌)
STREAM_EXTRA_WIDTH = 6         # 기울기에 따라 추가로 붙는 두께

STREAM_WIGGLE_AMP = 1.2           # 기본 흔들림 세기 (x축)
STREAM_WIGGLE_AMP_EXTRA = 1.0     # 기울기에 따라 추가로 붙는 흔들림
STREAM_WIGGLE_FREQ = 14.0       # 물줄기 휘어지는 주기 (클수록 더 자주 흔들림)

# 붓는 속도: 1.0 이면 1초 동안 pour_factor=1로 부으면
# 셰이커 volume 1.0이 빠진다고 보면 됨.
POUR_RATE = 1.2

# 잔 최대 용량 (셰이커랑 1:1로 맞추고 싶으면 같게 둔다)
GLASS_CAPACITY = MAX_SHAKER_VOLUME
