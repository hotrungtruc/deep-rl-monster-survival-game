import pygame

# ===================================
# WALLS LEVEL 1 — CƠ BẢN, TRỐNG TRẢI
# ===================================
walls_1 = [
    pygame.Rect(400, 300, 400, 40),     # Tường ngang trên giữa
    pygame.Rect(800, 700, 400, 40),     # Tường ngang dưới giữa
]

# ===================================
# WALLS LEVEL 2 — PHÂN KHU TRÁI / PHẢI
# ===================================
walls_2 = [
    pygame.Rect(200, 250, 600, 40),     # Tường ngang khu trái trên
    pygame.Rect(200, 950, 600, 40),     # Tường ngang khu trái dưới
    pygame.Rect(800, 400, 40, 500),     # Tường dọc ngăn giữa
    pygame.Rect(1000, 250, 600, 40),    # Tường ngang khu phải trên
    pygame.Rect(1000, 950, 600, 40),    # Tường ngang khu phải dưới
]

# ===================================
# WALLS LEVEL 3 — THU NHỎ KHUNG NGOÀI 0.5 LẦN
# ===================================
walls_3 = [
    pygame.Rect(400, 200, 1000, 40),    # Tường ngang trên (thu nhỏ)
    pygame.Rect(400, 240, 40, 700),     # Tường trái
    pygame.Rect(1360, 240, 40, 700),    # Tường phải
    pygame.Rect(500, 940, 900, 40),     # Tường ngang dưới
    pygame.Rect(800, 400, 40, 500),     # Dọc trung tâm
    pygame.Rect(650, 650, 300, 40),     # Ngang giữa trung tâm
]

# ===================================
# WALLS LEVEL 4 — CÂN BẰNG, THOÁNG GẤP ĐÔI (ĐÃ CHỈNH)
# ===================================
walls_4 = [
    # Viền ngoài (thu vào trong 0.5 so với màn 3)
    pygame.Rect(400, 200, 1000, 40),    # Trên
    pygame.Rect(400, 200, 40, 850),     # Trái
    pygame.Rect(1360, 200, 40, 850),    # Phải
    pygame.Rect(400, 1010, 1000, 40),   # Dưới

    # Cụm trung tâm (nới gấp đôi)
    pygame.Rect(700, 400, 40, 400),     # Dọc trái trung tâm
    pygame.Rect(1050, 400, 40, 400),    # Dọc phải trung tâm
    pygame.Rect(740, 600, 310, 40),     # Ngang giữa trung tâm
    pygame.Rect(650, 800, 540, 40),     # Hành lang ngang thấp hơn

    # Khu trái
    pygame.Rect(450, 300, 300, 40),     # Ngang trái trên
    pygame.Rect(450, 850, 300, 40),     # Ngang trái dưới

    # Khu phải
    pygame.Rect(1040, 300, 300, 40),    # Ngang phải trên
    pygame.Rect(1040, 850, 300, 40),    # Ngang phải dưới
]

# ===================================
# WALLS LEVEL 5 — MÊ CUNG LỚN, THOÁNG GẤP ĐÔI + KHUNG 0.5
# ===================================
walls_5 = [
    # Viền ngoài (thu vào 0.5 lần so với biên mặc định)
    pygame.Rect(400, 200, 1000, 40),     # Trên
    pygame.Rect(400, 200, 40, 850),      # Trái
    pygame.Rect(1360, 200, 40, 850),     # Phải
    pygame.Rect(400, 1010, 1000, 40),    # Dưới

    # Cụm trung tâm (nới rộng gấp đôi khoảng cách giữa các khối)
    pygame.Rect(500, 300, 400, 40),      # Ngang trên
    pygame.Rect(900, 300, 40, 300),      # Dọc nối
    pygame.Rect(550, 650, 600, 40),      # Ngang giữa
    pygame.Rect(1150, 300, 40, 350),     # Dọc phải trung tâm
    pygame.Rect(1150, 750, 400, 40),     # Ngang thấp
    pygame.Rect(1300, 500, 40, 300),     # Dọc nối phụ
    pygame.Rect(650, 900, 700, 40),      # Ngang đáy mê cung

    # Nhánh phụ (tăng khoảng cách, thoáng hơn)
    pygame.Rect(450, 500, 40, 400),
    pygame.Rect(450, 500, 300, 40),
    pygame.Rect(1400, 250, 40, 400),
    pygame.Rect(950, 950, 300, 40),
]