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