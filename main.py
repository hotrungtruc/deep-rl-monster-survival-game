import os
import sys
import cv2
import torch
import numpy as np
import pygame
from game import ZombieShooter

# ===== Game configuration =====
WINDOW_WIDTH, WINDOW_HEIGHT = 1200, 800
WORLD_WIDTH, WORLD_HEIGHT = 1800, 1200
FPS = 60

# ===== Initialize game =====
game = ZombieShooter(
    window_width=WINDOW_WIDTH,
    window_height=WINDOW_HEIGHT,
    world_width=WORLD_WIDTH,
    world_height=WORLD_HEIGHT,
    fps=FPS,
    sound=False,
    render_mode="human"
)

# ===== Prepare temp folder for screenshots =====
os.makedirs("temp", exist_ok=True)

# ===== Game loop =====
observation, info = game.reset()
clock = pygame.time.Clock()

while True:
    action = 0

    # --- Handle events ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_j:  # J key for Frenzied Kick
                action = 5
            elif event.key == pygame.K_k:  # K key for Blood Burst
                action = 6
            elif event.key == pygame.K_ESCAPE:
                print("Game exited.")
                pygame.quit()
                sys.exit()

    # --- Handle continuous key presses ---
    keys = pygame.key.get_pressed()
    if action == 0:
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            action = 1
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            action = 2
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            action = 3
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            action = 4

    # --- Step game ---
    observation, reward, done, truncated, info = game.step(action=action)

    # --- Save frame if reward changes ---
    if reward != 0:
        print(f"Reward: {reward} | Done: {done}")
        img_array = torch.clip(observation.squeeze(0), 0, 255).numpy().astype(np.uint8)

        # Convert RGB -> BGR for OpenCV
        if img_array.shape[-1] == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        save_path = "temp/screen.jpg"
        cv2.imwrite(save_path, img_array)
        print(f"✅ Frame saved to {save_path}")

    # --- Control FPS ---
    clock.tick(FPS)
 