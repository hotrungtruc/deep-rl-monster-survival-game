import random
import pygame
import math
from PIL import Image, ImageSequence
from util import *

# =============================
# HÀM HỖ TRỢ LOAD GIF
# =============================
def load_gif_frames(path, size):
    """Trả về danh sách các frame pygame.Surface từ 1 file GIF"""
    pil_gif = Image.open(path)
    frames = []
    for frame in ImageSequence.Iterator(pil_gif):
        frame = frame.convert("RGBA")
        # Use nearest-neighbor resizing to preserve pixel-art clarity and match backend pixel size
        frame = frame.resize(size, resample=Image.Resampling.NEAREST)
        mode = frame.mode
        data = frame.tobytes()
        pygame_img = pygame.image.fromstring(data, frame.size, mode)
        frames.append(pygame_img)
    return frames


# =============================
# PLAYER CLASS
# =============================
class Player:
    def __init__(self, world_width, world_height, walls):
        self.size = 70
        self.speed = 5
        self.rect = None

        self.x = world_width // 2
        self.y = world_height // 2

        # Spawn tại vị trí hợp lệ
        while True:
            self.rect = pygame.Rect(self.x, self.y, self.size, self.size)
            if check_collision(self.rect, walls):
                self.x += random.randint(-5, 5)
                self.y += random.randint(-5, 5)
            else:
                break

        self.score = 0
        self.ammo = 10
        self.health = 5

        # Load animation từ GIFs
        self.animations = {}
        for direction in ('up', 'down', 'left', 'right'):
            frames = load_gif_frames(f'gifs/player_{direction}.gif', (self.size, self.size))
            self.animations[direction] = frames

        self.direction = "down"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 6  # tốc độ animation

    def update(self):
        # Cập nhật frame animation
        self.frame_timer += 1
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(self.animations[self.direction])

    def draw(self, screen, camera_x, camera_y):
        frame = self.animations[self.direction][self.frame_index]
        screen.blit(frame, (self.x - camera_x, self.y - camera_y))


# =============================
# ZOMBIE / MONSTER CLASS
# =============================
class Zombie:
    MONSTER_TYPES = {
        "bat": 100,
        "ghost": 120,
        "monster": 120,
        "demon": 120
    }

    def __init__(self, world_width, world_height, speed=1):
        self.world_width = world_width
        self.world_height = world_height
        self.appearing = True
        self.appear_timer = 30  # Number of frames to show appearance effect
        self.speed = speed

        # --- Random loại quái và đặt kích thước ---
        self.type = random.choice(list(Zombie.MONSTER_TYPES.keys()))
        self.size = Zombie.MONSTER_TYPES[self.type]

        # --- Load hiệu ứng xuất hiện (appear effect) ---
        self.appear_image = pygame.image.load("images/appear.png").convert_alpha()
        self.appear_image = pygame.transform.scale(self.appear_image, (self.size, self.size))

        # --- Health dựa trên kích thước ---
        self.max_hp = 3 + (self.size - 70) // 10
        self.hp = self.max_hp

        # --- Spawn vị trí ---
        self.x, self.y = self.spawn()

        # --- Load animation từ GIFs ---
        self.animations = {}
        for direction in ('up', 'down', 'left', 'right'):
            frames = load_gif_frames(f'gifs/{self.type}_{direction}.gif', (self.size, self.size))
            self.animations[direction] = frames

        self.direction = "down"
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_delay = random.randint(10, 20)

        self.rect = pygame.Rect(0, 0, self.size, self.size)
        self.rect.center = (self.x, self.y)
        # Health points for damage handling
        self.hp = 1

    def spawn(self):
        spawn_positions = [
            (random.randint(0, self.world_width - self.size), 0),
            (random.randint(0, self.world_width - self.size), self.world_height - self.size),
            (0, random.randint(0, self.world_height - self.size)),
            (self.world_width - self.size, random.randint(0, self.world_height - self.size))
        ]
        return random.choice(spawn_positions)

    def move_toward_player(self, player_x, player_y, walls):
        dx, dy = player_x - self.x, player_y - self.y
        distance = math.hypot(dx, dy)
        if distance == 0:
            return

        # Hướng gốc
        dir_x, dir_y = dx / distance, dy / distance

        # Kiểm tra va chạm trên hướng chính
        step_size = self.speed
        new_rect = pygame.Rect(self.x + dir_x * step_size, self.y + dir_y * step_size, self.size, self.size)
        if not check_collision(new_rect, walls):
            self.x += dir_x * step_size
            self.y += dir_y * step_size
        else:
            # Nếu bị chắn → thử các góc lệch
            found = False
            for angle in [15, -15, 30, -30, 45, -45, 60, -60, 90, -90]:
                rad = math.radians(angle)
                new_dx = dir_x * math.cos(rad) - dir_y * math.sin(rad)
                new_dy = dir_x * math.sin(rad) + dir_y * math.cos(rad)
                new_rect = pygame.Rect(self.x + new_dx * step_size, self.y + new_dy * step_size, self.size, self.size)
                if not check_collision(new_rect, walls):
                    self.x += new_dx * step_size
                    self.y += new_dy * step_size
                    found = True
                    break
            if not found:
                # Nếu không tìm được hướng nào (bị kẹt hoàn toàn) → lùi lại nhẹ
                back_x = -dir_x * step_size * 0.5
                back_y = -dir_y * step_size * 0.5
                new_rect = pygame.Rect(self.x + back_x, self.y + back_y, self.size, self.size)
                if not check_collision(new_rect, walls):
                    self.x += back_x
                    self.y += back_y

        # Cập nhật hướng hiển thị animation
        if abs(dx) > abs(dy):
            self.direction = 'right' if dx > 0 else 'left'
        else:
            self.direction = 'down' if dy > 0 else 'up'

        self.rect.topleft = (self.x, self.y)


    def update(self):
        if self.appearing:
            self.appear_timer -= 1
            if self.appear_timer <= 0:
                self.appearing = False
        else:
            # Cập nhật frame animation
            self.frame_timer += 1
            if self.frame_timer >= self.frame_delay:
                self.frame_timer = 0
                self.frame_index = (self.frame_index + 1) % len(self.animations[self.direction])

    def draw(self, screen, camera_x, camera_y):
        screen_x = self.x - camera_x
        screen_y = self.y - camera_y
        
        if self.appearing:
            # Draw the appear effect
            screen.blit(self.appear_image, (screen_x, screen_y))
        else:
            # Draw the normal monster animation
            current_frame = self.animations[self.direction][self.frame_index]
            screen.blit(current_frame, (screen_x, screen_y))