import cv2
import torch
import time
import numpy as np
import pygame
import sys
from bullet import *
from characters import *
import random
from util import *
from walls import *
import gymnasium as gym
import os
from PIL import Image

def load_gif_frames(path, size=None):
    """Load all frames from a GIF file into a list of Pygame surfaces"""
    frames = []
    gif = Image.open(path)
    
    try:
        while True:
            frame = gif.copy().convert("RGBA")
            if size:
                frame = frame.resize(size, Image.Resampling.NEAREST)
            frame_surface = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode)
            frames.append(frame_surface)
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass

    return frames


class TreasureChest:

    def __init__(self, x, y):
        self.closed_image = pygame.image.load("images/blue_flower.png").convert_alpha()
        self.opened_image = pygame.image.load("images/blue_flower_opened.png").convert_alpha()  # add a separate opened image

        self.size = 70
        self.closed_image = pygame.transform.scale(self.closed_image, (self.size, self.size))
        self.opened_image = pygame.transform.scale(self.opened_image, (self.size, self.size))

        self.rect = pygame.Rect(x, y, self.size, self.size)
        self.is_opened = False
        self.open_time = None  # for optional visual timing effect

    def draw(self, screen, camera_x, camera_y):
        # When opened, show the opened chest for a moment before disappearing
        if self.is_opened:
            if self.open_time is None:
                self.open_time = pygame.time.get_ticks()
            elif pygame.time.get_ticks() - self.open_time > 1000:  # show for 1 second
                return  # don't draw anymore
            screen.blit(self.opened_image, (self.rect.x - camera_x, self.rect.y - camera_y))
        else:
            screen.blit(self.closed_image, (self.rect.x - camera_x, self.rect.y - camera_y))



class HealthDrop:

    def __init__(self, x, y):
        self.image = pygame.image.load("images/blood.png").convert_alpha()
        self.size = 60
        self.image = pygame.transform.scale(self.image, (self.size, self.size))

        self.x = x
        self.y = y
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)

    def draw(self, screen, camera_x, camera_y):
        screen.blit(self.image, (self.x - camera_x, self.y - camera_y))



class ZombieShooter():

    def __init__(self, window_width, window_height, world_height, world_width, fps, sound=False, render_mode="human"): 
        
        self.window_width = window_width
        self.window_height = window_height
        self.world_height = world_height
        self.world_width = world_width
        
        self.treasure_chest = None
        self.health_drop = None

        self.paused = False

        self.gun_type = "single"
        self.fire_mode = "single"

        if render_mode == "human":
            self.sound = sound
            self.human = True
        elif render_mode == "rgb":
            self.sound = False
            self.human = False
            os.environ["SDL_VIDEODRIVER"] = "dummy"
        else:
            raise Exception("Invalid render mode")
        
        pygame.init()
        self.screen = pygame.display.set_mode((window_width, window_height))

        pygame.display.set_caption("Zombie Shooter")

        self.font = pygame.font.SysFont(None, 36)

        # Load and prepare textures
        self.floor_texture = pygame.image.load("images/floor.jpg").convert()
        self.floor_texture = pygame.transform.scale(self.floor_texture, (150, 150))
        
        # Create floor pattern surface
        self.floor_pattern = pygame.Surface((self.world_width, self.world_height))
        for y in range(0, self.world_height, 120):
            for x in range(0, self.world_width, 120):
                self.floor_pattern.blit(self.floor_texture, (x, y))

        self.clock = pygame.time.Clock()
        self.fps = fps

        self.walls = walls_1
        self.announcement_font = pygame.font.SysFont(None, 72)

        self.player = Player(world_height=self.world_height, world_width=self.world_width, walls=self.walls)

        self.background_color = (181, 101, 29)
        # Use a dark gray block for walls instead of an image texture
        self.wall_color = (50, 50, 50)
        self.border_color = (255, 0, 0)

        self.announcement_font = pygame.font.SysFont(None, 100)

        self.reset()


        self.action_space = gym.spaces.Discrete(7)

        if self.sound:
            pygame.mixer.pre_init(44100, -16, 2, 64)
            pygame.mixer.init()
            pygame.mixer.music.load("sounds/background_music.wav")
            pygame.mixer.music.play(-1,0,0)

            self.last_walk_play_time = 0

            self.zombie_bite = pygame.mixer.Sound("sounds/zombie_bite_1.wav")
            self.zombie_hit = pygame.mixer.Sound("sounds/zombie_hit.wav")
            self.shotgun_blast = pygame.mixer.Sound("sounds/shotgun_blast.wav")
            self.zombie_snarl = pygame.mixer.Sound("sounds/zombie_snarl.wav")
            self.footstep = pygame.mixer.Sound("sounds/footstep.wav")
            self.vocals_1 = pygame.mixer.Sound("sounds/one_of_those_things_got_in.wav")
            self.vocals_2 = pygame.mixer.Sound("sounds/virus_infection_alert.wav")
            self.vocals_3 = pygame.mixer.Sound("sounds/come_and_see.wav")

            self.vocals_1.play()


    def reset(self):
        self.done = False
        self.level = 1
        self.level_goal = 5
        self.max_zombie_count = 5
        self.walls = walls_1
        self.player = Player(world_height=self.world_height, world_width=self.world_width, walls=self.walls)
        self.player.health = 5
        self.max_zombie_count = 5
        self.zombie_top_speed = 2
        self.total_frames = 0
        self.last_bullet_frame = 0
        self.shotgun_ammo = 0
        self.out_of_ammo_message_displayed = False
        self.out_of_ammo_start_time = 0
        self.gun_type = "single"

        self.bullets = []
        self.zombies = []
        self.effects = []
        self.burning = []
        self.blood_burst_charges = 0
        self.last_burst_time = -999999
        self.burst_cooldown_ms = 3000
        self.last_kick_time = -999999
        self.kick_cooldown_ms = 500
        self.screen_shake_end = 0

        return self._get_obs(), self._get_info()

    def play_walking_sound(self):

        if self.sound:
            current_time = pygame.time.get_ticks()
            if(current_time - self.last_walk_play_time > 1000):
                self.footstep.play()
                self.last_walk_play_time = current_time

    def start_next_level(self):
        self.level += 1

        # Nếu đã vượt qua level 5 thì thắng
        if self.level > 5:
            win_surface = self.announcement_font.render("🎉 You Won! 🎉", True, (255, 0, 0))
            win_rect = win_surface.get_rect(center=(self.window_width // 2, self.window_height // 2))
            self.screen.blit(win_surface, win_rect)
            pygame.display.flip()
            pygame.time.wait(4000)
            self.done = True
            return

        # Hiển thị thông báo chuyển cấp
        next_level_surface = self.announcement_font.render(f"Starting Level {self.level}", True, (255, 0, 0))
        next_level_rect = next_level_surface.get_rect(center=(self.window_width // 2, self.window_height // 2))
        self.screen.blit(next_level_surface, next_level_rect)
        pygame.display.flip()
        pygame.time.wait(2500)

        # Reset entities
        self.zombies = []
        self.bullets = []
        self.treasure_chest = None
        self.health_drop = None

        # Chọn tường tương ứng từng cấp độ
        if self.level == 2:
            if self.sound: self.vocals_2.play()
            self.walls = walls_2
            self.level_goal = 10
        elif self.level == 3:
            if self.sound: self.vocals_3.play()
            self.walls = walls_3
            self.level_goal = 20
        elif self.level == 4:
            self.walls = walls_4
            self.level_goal = 30
        elif self.level == 5:
            self.walls = walls_5
            self.level_goal = 40

        # Sinh rương thưởng ngẫu nhiên
        x, y = random.randint(100, self.world_width - 150), random.randint(100, self.world_height - 150)
        self.treasure_chest = TreasureChest(x, y)

        # Tăng độ khó mỗi cấp
        self.zombie_top_speed += 1
        self.max_zombie_count += 3

        # Spawn lại người chơi
        self.player = Player(world_height=self.world_height, world_width=self.world_width, walls=self.walls)

        pygame.display.flip()
        pygame.time.wait(4000)

        if self.level > 3:
            self.done = True
        #    pygame.quit()
         #   sys.exit()

    def game_over(self):

        game_over_surface = self.announcement_font.render('You Died', True, (255, 0, 0)) # Red text

        game_over_rect = game_over_surface.get_rect(center=(self.window_width // 2, self.window_height // 2))

        self.screen.blit(game_over_surface, game_over_rect)

        pygame.display.flip()

        self.done = True

        if self.sound:
            self.zombie_snarl.play()

        if(self.human):
            pygame.time.wait(2000)


        
        # Quit the game. 
        # pygame.quit()
        # sys.exit()


    def fill_background(self):
        # Get camera position
        camera_x = self.player.x - self.window_width // 2
        camera_y = self.player.y - self.window_height // 2
        camera_x = max(0, min(camera_x, self.world_width - self.window_width))
        camera_y = max(0, min(camera_y, self.world_height - self.window_height))
        
        # Draw the floor pattern
        self.screen.blit(self.floor_pattern, (-camera_x, -camera_y))
        
        # Draw walls as solid dark-gray rectangles (no image texture)
        # Walls are drawn in fill_background as solid rectangles

        # Screen shake
        now = pygame.time.get_ticks()
        shake_x = 0
        shake_y = 0
        if hasattr(self, 'screen_shake_end') and now < self.screen_shake_end:
            shake_x = random.randint(-4, 4)
            shake_y = random.randint(-4, 4)

        score_surface = self.font.render(f'Score: {self.player.score}', True, (255, 255, 255))
        self.screen.blit(score_surface, (10 + shake_x, 10 + shake_y))

        health_surface = self.font.render(f'Health: {self.player.health}', True, (255, 255, 255))
        self.screen.blit(health_surface, (10 + shake_x, 35 + shake_y))

        level_surface = self.font.render(f"Level: {self.level}", True, (0, 0, 0))
        self.screen.blit(level_surface, (10 + shake_x, 60 + shake_y))

        # Show Blood Burst charges and cooldown
        if self.blood_burst_charges <= 0:
            cd_text = "Blood Burst: No charges"
            cd_color = (100, 100, 100)  # gray when no charges
        else:
            cd_remaining = max(0, (self.last_burst_time + self.burst_cooldown_ms - now) / 1000)
            if cd_remaining > 0:
                cd_text = f"Blood Burst ({self.blood_burst_charges}): {cd_remaining:.1f}s"
                cd_color = (200, 0, 0)
            else:
                cd_text = f"Blood Burst ({self.blood_burst_charges}): Ready"
                cd_color = (0, 150, 0)
        ammo_surface = self.font.render(cd_text, True, cd_color)
        self.screen.blit(ammo_surface, (10 + shake_x, 85 + shake_y))

        # Frenzied Kick cooldown
        kick_cd = max(0, (self.last_kick_time + self.kick_cooldown_ms - now) / 1000)
        if kick_cd > 0:
            kick_text = f"Frenzied Kick CD: {kick_cd:.1f}s"
            kick_color = (200, 0, 0)
        else:
            kick_text = "Frenzied Kick: Ready"
            kick_color = (0, 150, 0)
        kick_surface = self.font.render(kick_text, True, kick_color)
        self.screen.blit(kick_surface, (10 + shake_x, 110 + shake_y))

        if self.out_of_ammo_message_displayed:
            elapsed = pygame.time.get_ticks() - self.out_of_ammo_start_time
            if elapsed <= 2000:  # 2 giây
                if self.blood_burst_charges <= 0:
                    msg = "No Blood Burst charges! Find treasure chests!"
                else:
                    msg = "Blood Burst on cooldown!"
                out_of_ammo_surface = self.font.render(msg, True, (255, 0, 0))
                out_of_ammo_rect = out_of_ammo_surface.get_rect(center=(self.window_width // 2, self.window_height // 2))
                self.screen.blit(out_of_ammo_surface, out_of_ammo_rect)
            else:
                self.out_of_ammo_message_displayed = False  # tự tắt sau 2 giây


    def perform_kick(self):
        # Frenzied Kick - instant hit; cooldown enforced elsewhere
        self.effects.append(MeleeAttack(
            x=self.player.x,
            y=self.player.y,
            direction=self.player.direction,
            delay_ms=0,     # hit immediately
            active_ms=150,  # hit active for 0.15s
            reach=80,       # range of kick
            damage=2        # how much damage it deals
        ))
        if self.sound:
            self.zombie_hit.play()

    def perform_blood_burst(self):
        # Blood Demon Art: Blood Burst - needs charges to use
        if self.blood_burst_charges <= 0:
            self.out_of_ammo_message_displayed = True
            self.out_of_ammo_start_time = pygame.time.get_ticks()
            return

        now = pygame.time.get_ticks()
        if now < self.last_burst_time + self.burst_cooldown_ms:
            self.out_of_ammo_message_displayed = True
            return
            
        # Use up one charge
        self.blood_burst_charges -= 1

        self.effects.append(BloodBurst(
            x=self.player.x + self.player.size//2,
            y=self.player.y + self.player.size//2,
            max_radius=200,         # explosion size
            expand_ms=300,          # time to reach full size
            dot_duration_ms=3000,   # burning lasts 3 seconds
            damage=1,               # initial hit damage
            dot_damage_per_tick=1,  # damage per burning tick
            tick_interval_ms=1000   # tick every second
        ))

        self.last_burst_time = now
        self.out_of_ammo_message_displayed = False

        if self.sound:
            self.shotgun_blast.play()

    def _get_info(self):

        gun_type_num = 1 if "single" in self.gun_type else 2

        return {
            "health": self.player.health,
            "shotgun_ammo": self.shotgun_ammo,
            "gun_type": self.gun_type,
            "gun_type_num": gun_type_num,
            "bullets": len(self.bullets)
        }
    
    def _get_obs(self):
        # Get the screen image
        screen_array = pygame.surfarray.pixels3d(self.screen)
        screen_array = np.transpose(screen_array, (1, 0, 2))
        downscaled_image = cv2.resize(screen_array, (128, 128), interpolation=cv2.INTER_NEAREST)
        grayscale = cv2.cvtColor(downscaled_image, cv2.COLOR_RGB2GRAY)

        # Add Blood Burst charges as an overlay in top-right corner
        # This makes the charges visible to the AI in a visual way
        charges_area = np.zeros((10, 10), dtype=np.uint8)
        if self.blood_burst_charges > 0:
            # Draw white squares for each charge (up to 3)
            for i in range(min(self.blood_burst_charges, 3)):
                charges_area[i*3:(i+1)*3, 0:3] = 255

        # Overlay charges onto main observation
        grayscale[0:10, 118:128] = charges_area

        observation = torch.from_numpy(grayscale).float().unsqueeze(0)
        return observation

    def toggle_pause(self):
        self.paused = not self.paused

        if self.paused:
            pause_surface = self.announcement_font.render("Game Paused", True, (255, 255, 255))
            pause_rect = pause_surface.get_rect(center=(self.window_width // 2, self.window_height // 2))
            self.screen.blit(pause_surface, pause_rect)
            pygame.display.flip() # Updating the display. 

            while self.paused:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.paused = False
                
                self.clock.tick(10) # slow down and prevent busy waiting

    def step(self, action, repeat=4):
        total_reward = 0

        for i in range(repeat):
            reward, done, truncated = self._step(action)

            total_reward += reward

            if action == 5 or action == 6:
                action = 0

            if done:
                break

        return self._get_obs(), total_reward, done, truncated, self._get_info()


    def _step(self, action):

        self.total_frames += 1

        up = True if action == 1 else False
        down = True if action == 2 else False
        left = True if action == 3 else False
        right = True if action == 4 else False
        switch_gun = True if action == 5 else False # This would be action 5
        fire = True if action == 6 else False
        pause = False

        reward, truncated = 0, False

        # Track if player moved this step
        player_moved = False
        old_x, old_y = self.player.x, self.player.y

        # Frenzied Kick (instant hit, cooldown enforced by time)
        now = pygame.time.get_ticks()
        kick_used = False
        if switch_gun:
            if now >= self.last_kick_time + self.kick_cooldown_ms:
                self.perform_kick()
                self.last_kick_time = now
                kick_used = True
            else:
                # signal skill not ready
                self.out_of_ammo_message_displayed = True

        # Blood Demon Art: Blood Burst
        burst_used = False
        if fire:
            self.perform_blood_burst()
            burst_used = True

        if self.paused:
            return reward, self.done, truncated

        if len(self.zombies) < self.max_zombie_count and random.randint(1, 100) < 3:
            self.zombies.append(Zombie(world_height=self.world_height, world_width=self.world_width, speed=random.randint(1, self.zombie_top_speed)))
        

        new_player_x = self.player.x

        if left: # Left
            new_player_x -= self.player.speed
            self.player.direction = "left"
        if right: # Right
            new_player_x += self.player.speed
            self.player.direction = "right"

        new_player_rect = pygame.Rect(new_player_x, self.player.y, self.player.size, self.player.size)

        collision = check_collision(new_player_rect, self.walls)

        if not collision \
            and self.player.x != new_player_x \
            and (0 <= new_player_x <= self.world_width - self.player.size):

            self.player.x = new_player_x

            self.play_walking_sound()

        new_player_y = self.player.y

        if up: # Up
            new_player_y -= self.player.speed
            self.player.direction = "up"
        if down: # Down
            new_player_y += self.player.speed
            self.player.direction = "down"
        
        new_player_rect = pygame.Rect(self.player.x, new_player_y, self.player.size, self.player.size)

        collision = check_collision(new_player_rect, self.walls)

        if not collision \
        and self.player.y != new_player_y \
        and (0 <= new_player_y <= self.world_height - self.player.size):
            self.player.y = new_player_y
            self.play_walking_sound() 
        
        self.player.rect = pygame.Rect(self.player.x, self.player.y, self.player.size, self.player.size)

        collision = False

        # Check if player moved
        if self.player.x != old_x or self.player.y != old_y:
            player_moved = True

        # Apply movement rewards
        if player_moved:
            reward += 0.01  # Small bonus for moving
        else:
            reward -= 0.01  # Light penalty for standing still

        camera_x = self.player.x - self.window_width // 2
        camera_y = self.player.y - self.window_height // 2

        camera_x = max(0, min(camera_x, self.world_width - self.window_width))
        camera_y = max(0, min(camera_y, self.world_height - self.window_height))
        
        # Update animations
        self.player.update()  # Update player animation
        for zombie in self.zombies:
            zombie.update()   # Update zombie animations

        # Process projectile hits on zombies
        self.zombies_temp = []

        for zombie in self.zombies:
            hit_bullet = get_collision(zombie.rect, self.bullets)
            if hit_bullet:
                # Apply bullet damage
                damage = getattr(hit_bullet, 'damage', 1)
                zombie.hp -= damage

                # remove bullet
                if hit_bullet in self.bullets:
                    self.bullets.remove(hit_bullet)

                if self.sound:
                    self.zombie_hit.play()

                # If zombie died, reward and possible drop
                if zombie.hp <= 0:
                    self.player.score += 1
                    # Higher reward for Blood Burst kills to encourage strategic use
                    if any(isinstance(effect, BloodBurst) for effect in self.effects):
                        reward += 3  # Extra reward for efficient Blood Burst use
                    else:
                        reward += 2
                    if random.randint(1, 100) <= 20:
                        self.health_drop = HealthDrop(zombie.rect.x, zombie.rect.y)
                else:
                    self.zombies_temp.append(zombie)

            elif check_collision(zombie.rect, [self.player.rect]):
                # Zombie hits player
                self.player.health -= 1
                reward -= 5  # Increased penalty to encourage better survival
                if self.sound:
                    self.zombie_bite.play()
            else:
                self.zombies_temp.append(zombie)

        self.zombies = self.zombies_temp

        # Process non-projectile effects (melee, AOE)
        now = pygame.time.get_ticks()
        effects_to_keep = []
        kick_hits = 0
        burst_hits = 0
        for effect in self.effects:
            alive = effect.update()
            if not alive:
                continue

            # Melee attack: apply when active and not yet processed
            if isinstance(effect, MeleeAttack) and effect.active and not effect.processed:
                for zombie in list(self.zombies):
                    if effect.rect.colliderect(zombie.rect):
                        zombie.hp -= effect.damage
                        effect.processed = True
                        kick_hits += 1
                        # small screen shake
                        self.screen_shake_end = now + 120
                        if self.sound:
                            self.zombie_hit.play()
                        if zombie.hp <= 0:
                            self.player.score += 1
                            reward += 1
                            if random.randint(1, 100) <= 20:
                                self.health_drop = HealthDrop(zombie.rect.x, zombie.rect.y)
                            # remove zombie from list
                            if zombie in self.zombies:
                                self.zombies.remove(zombie)

            # BloodBurst: expand and apply initial damage + DOT
            if isinstance(effect, BloodBurst):
                # check zombies within current radius
                for zombie in list(self.zombies):
                    dx = zombie.x - effect.x
                    dy = zombie.y - effect.y
                    dist = (dx*dx + dy*dy)**0.5
                    if dist <= effect.current_radius:
                        if zombie not in effect.dot_targets:
                            # initial hit
                            zombie.hp -= effect.damage
                            effect.dot_targets[zombie] = now + effect.dot_duration_ms
                            burst_hits += 1
                            # schedule burning ticks
                            self.burning.append({
                                'zombie': zombie,
                                'end_time': now + effect.dot_duration_ms,
                                'next_tick': now + effect.tick_interval_ms
                            })
                            if self.sound:
                                self.zombie_hit.play()
                            if zombie.hp <= 0:
                                self.player.score += 1
                                reward += 1
                                if random.randint(1, 100) <= 20:
                                    self.health_drop = HealthDrop(zombie.rect.x, zombie.rect.y)
                                if zombie in self.zombies:
                                    self.zombies.remove(zombie)

            effects_to_keep.append(effect)

        self.effects = effects_to_keep

        # Bonus for hitting multiple monsters with skill
        if kick_used and kick_hits > 1:
            reward += 0.5 * (kick_hits - 1)  # Bonus for each additional hit
        if burst_used and burst_hits > 1:
            reward += 0.5 * (burst_hits - 1)  # Bonus for each additional hit

        # Process burning DOT
        now = pygame.time.get_ticks()
        burning_to_keep = []
        for burn in self.burning:
            if now >= burn['next_tick']:
                zombie = burn['zombie']
                if zombie in self.zombies:  # ensure zombie still exists
                    zombie.hp -= 1  # apply DOT tick damage
                    if zombie.hp <= 0:
                        self.player.score += 1
                        reward += 1
                        if random.randint(1, 100) <= 20:
                            self.health_drop = HealthDrop(zombie.rect.x, zombie.rect.y)
                        self.zombies.remove(zombie)
                    else:
                        burn['next_tick'] += 1000  # schedule next tick
                        if now < burn['end_time']:  # keep if not expired
                            burning_to_keep.append(burn)
        self.burning = burning_to_keep
        burning_keep = []
        now = pygame.time.get_ticks()
        for b in self.burning:
            zombie = b['zombie']
            if zombie not in self.zombies:
                continue
            if now >= b['next_tick'] and now <= b['end_time']:
                # apply tick damage
                zombie.hp -= 1
                b['next_tick'] = now + 1000
                if self.sound:
                    self.zombie_hit.play()
                if zombie.hp <= 0:
                    self.player.score += 1
                    reward += 1
                    if random.randint(1, 100) <= 20:
                        self.health_drop = HealthDrop(zombie.rect.x, zombie.rect.y)
                    if zombie in self.zombies:
                        self.zombies.remove(zombie)
                    continue
            if now < b['end_time']:
                burning_keep.append(b)
        self.burning = burning_keep

        # Move zombies after damage processing
        for zombie in self.zombies:
            zombie.move_toward_player(self.player.x, self.player.y, self.walls)

        self.fill_background()

        # Process and draw bullets
        bullets_to_remove = []
        for bullet in self.bullets:
            # move() now returns False if bullet exceeds max distance
            if not bullet.move() or check_collision(bullet.rect, self.walls):
                bullets_to_remove.append(bullet)
            else:
                bullet.draw(self.screen, camera_x, camera_y)
        
        # Remove bullets that exceeded distance or hit walls
        for bullet in bullets_to_remove:
            if bullet in self.bullets:
                self.bullets.remove(bullet)

        # Draw effects under everything else
        for effect in self.effects:
            effect.draw(self.screen, camera_x, camera_y)
            # burning indicator
            if isinstance(effect, BloodBurst):
                for zombie in self.zombies:
                    if zombie in effect.dot_targets:
                        # draw burning effect on affected zombies
                        z_center_x = zombie.rect.centerx - camera_x
                        z_center_y = zombie.rect.centery - camera_y
                        pygame.draw.circle(self.screen, (255, 120, 180, 120), (z_center_x, z_center_y), 25)

        # Draw entities
        self.player.draw(self.screen, camera_x, camera_y)
        for zombie in self.zombies:
            zombie.draw(self.screen, camera_x, camera_y)
            # draw health bar
            if hasattr(zombie, 'hp') and hasattr(zombie, 'max_hp'):
                bar_width = 40
                hp_ratio = max(0, zombie.hp / zombie.max_hp)
                pygame.draw.rect(self.screen, (255, 0, 0), 
                            (zombie.rect.x - camera_x, zombie.rect.y - camera_y - 5, bar_width, 3))
                pygame.draw.rect(self.screen, (0, 255, 0),
                            (zombie.rect.x - camera_x, zombie.rect.y - camera_y - 5, int(bar_width * hp_ratio), 3))

        if self.health_drop:
            self.health_drop.draw(self.screen, camera_x, camera_y) 

        pygame.draw.rect(self.screen, self.border_color, (0 - camera_x, 0 - camera_y, self.world_width, self.world_height), 5)

        for wall in self.walls:
            pygame.draw.rect(self.screen, self.wall_color, (wall.x - camera_x, wall.y - camera_y, wall.width, wall.height))

        if self.treasure_chest:
            self.treasure_chest.draw(self.screen, camera_x, camera_y)
        
        if self.treasure_chest and self.player.rect.colliderect(self.treasure_chest):
            if not self.treasure_chest.is_opened:
                self.treasure_chest.is_opened = True
                reward += 2  # Increased reward for finding treasure
                # Give random number of Blood Burst charges (1-3)
                new_charges = random.randint(1, 3)
                self.blood_burst_charges += new_charges
                # Show charges gained message
                unlock_msg = self.font.render(f"+{new_charges} Blood Burst charges!", True, (200, 50, 200))
                msg_rect = unlock_msg.get_rect(center=(self.window_width // 2, self.window_height // 2))
                self.screen.blit(unlock_msg, msg_rect)
        
        if self.health_drop and self.player.rect.colliderect(self.health_drop.rect):
            self.player.health = min(self.player.health + 1, 100)
            reward += 2
            #print("Heart collected!")
            self.health_drop = None


        pygame.display.flip() # Updates the display

        if self.player.health <= 0:
            self.game_over()

        if self.human:
            self.clock.tick(self.fps)
        else:
            self.clock.tick()

        if(self.level_goal <= self.player.score):
            reward += 20  # Big bonus for passing the stage
            self.start_next_level()

        return reward, self.done, truncated