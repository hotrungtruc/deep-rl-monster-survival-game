import pygame, math
from PIL import Image
import random

def load_gif_frames(path, scale=1.0):
    """Load all frames from a GIF file and return list of Pygame surfaces."""
    frames = []
    gif = Image.open(path)
    try:
        while True:
            frame = gif.copy().convert("RGBA")
            w, h = frame.size
            frame = frame.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            surf = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode)
            frames.append(surf)
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass
    return frames


class MeleeAttack:
    """Melee attack using directional slash GIF animation with scaled size."""

    slash_gifs = {
        "up":    load_gif_frames("gifs/slash_up.gif", 0.2),
        "down":  load_gif_frames("gifs/slash_down.gif", 0.2),
        "left":  load_gif_frames("gifs/slash_left.gif", 0.2),
        "right": load_gif_frames("gifs/slash_right.gif", 0.2),
    }

    def __init__(self, x, y, direction, delay_ms=80, active_ms=300, reach=90, damage=1):
        self.x = x
        self.y = y
        self.direction = direction
        self.start_time = pygame.time.get_ticks()
        self.delay_ms = delay_ms
        self.active_ms = active_ms
        self.reach = reach
        self.damage = damage

        self.active = False
        self.processed = False
        self.end_time = self.start_time + self.delay_ms + self.active_ms

        self.frames = MeleeAttack.slash_gifs[self.direction]
        self.frame_duration = self.active_ms / max(1, len(self.frames))
        self.current_frame = 0

        # Kích thước ban đầu
        self.rect = pygame.Rect(x, y, reach, reach)

    def update(self):
        now = pygame.time.get_ticks()

        if not self.active and now >= self.start_time + self.delay_ms:
            self.active = True
            fw, fh = self.frames[0].get_size()


            horizontal_offset = 25 
            vertical_offset = 15

            if self.direction == "right":
                self.rect = pygame.Rect(self.x + 40 + horizontal_offset, self.y + vertical_offset, fw, fh)
            elif self.direction == "left":
                self.rect = pygame.Rect(self.x - fw + 40 - horizontal_offset, self.y + vertical_offset, fw, fh)
            elif self.direction == "up":
                self.rect = pygame.Rect(self.x - fw // 4, self.y - fh + 20, fw, fh)
            else:  # down
                self.rect = pygame.Rect(self.x - fw // 4, self.y + 40, fw, fh)

        if self.active:
            elapsed = now - (self.start_time + self.delay_ms)
            self.current_frame = int(elapsed / self.frame_duration)
            if self.current_frame >= len(self.frames):
                self.current_frame = len(self.frames) - 1

        return now < self.end_time

    def draw(self, screen, camera_x, camera_y):
        if not self.active or self.current_frame >= len(self.frames):
            return

        frame = self.frames[self.current_frame]
        fx = self.rect.x - camera_x
        fy = self.rect.y - camera_y
        screen.blit(frame, (fx, fy))





class BloodBurst:
    """AOE burst that expands outward and applies initial damage + burn DOT.

    Visual upgrades:
    - Smooth expanding multi-layer gradient circle
    - A pulsing outer ring (gives impact feeling)
    - Sparks/particles emitted outward at moment of burst
    - Lingering ember particles that fade during DOT duration
    """

    def __init__(self, x, y, max_radius=200, expand_ms=300,
                 dot_duration_ms=3000, damage=1, dot_damage_per_tick=1,
                 tick_interval_ms=1000):
        self.x = x
        self.y = y
        self.start_time = pygame.time.get_ticks()
        self.max_radius = max_radius
        self.expand_ms = expand_ms
        self.dot_duration_ms = dot_duration_ms
        self.damage = damage
        self.dot_damage = dot_damage_per_tick
        self.tick_interval_ms = tick_interval_ms

        self.current_radius = 0
        self.active = True
        self.processed = False
        # store zombies that received the DOT: {zombie: end_time}
        self.dot_targets = {}

        # Visual / particle data
        self.particles = []     # sparks (short-lived) emitted at burst moment
        self.embers = []        # lingering embers during DOT
        self.pulse_phase = 0.0
        self._spawned = False   # whether initial particles were spawned

    def _spawn_particles(self, n=22):
        """Spawn outward sparks at burst moment."""
        for i in range(n):
            ang = random.uniform(0, math.tau)
            speed = random.uniform(self.max_radius * 0.006, self.max_radius * 0.03)
            life = random.randint(int(self.expand_ms * 0.4), int(self.expand_ms * 1.4))
            size = random.randint(2, 5)
            color = (
                random.randint(220, 255),    # r (pinkish)
                random.randint(80, 160),     # g
                random.randint(120, 200),    # b
                255
            )
            self.particles.append({
                'x': self.x, 'y': self.y,
                'vx': math.cos(ang) * speed,
                'vy': math.sin(ang) * speed,
                'life': life,
                'age': 0,
                'size': size,
                'color': color
            })

        # spawn a few embers that last through DOT
        for i in range(max(6, n//6)):
            ang = random.uniform(0, math.tau)
            r = random.uniform(self.max_radius * 0.1, self.max_radius * 0.6)
            ex = self.x + math.cos(ang) * r
            ey = self.y + math.sin(ang) * r
            life = self.dot_duration_ms + random.randint(-500, 500)
            self.embers.append({
                'x': ex, 'y': ey,
                'vx': random.uniform(-0.2, 0.2),
                'vy': random.uniform(-0.1, -0.4),
                'life': life,
                'age': 0,
                'size': random.uniform(2.0, 5.0),
                'color': (255, random.randint(100, 160), random.randint(140, 220), 200)
            })

    def update(self):
        now = pygame.time.get_ticks()
        elapsed = now - self.start_time

        # expand radius smoothly
        if elapsed <= self.expand_ms and self.expand_ms > 0:
            t = elapsed / self.expand_ms
            # ease-out expansion
            t_ease = 1 - (1 - t) * (1 - t)
            self.current_radius = int(self.max_radius * t_ease)
        else:
            self.current_radius = self.max_radius

        # spawn particles once at the start of expansion
        if not self._spawned and elapsed >= 0:
            self._spawned = True
            self._spawn_particles(n=28)

        # update pulse phase for ring animation
        self.pulse_phase += 0.06

        # update sparks (short-lived)
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['age'] += 16  # approximate per-frame ms (fine without dt)
            # slow down a bit
            p['vx'] *= 0.96
            p['vy'] *= 0.96
            p['vy'] += 0.08  # gravity-ish downwards

        # remove dead sparks
        self.particles = [p for p in self.particles if p['age'] < p['life']]

        # update embers (linger and slowly fade)
        for e in self.embers:
            e['x'] += e['vx']
            e['y'] += e['vy']
            e['age'] += 16
        self.embers = [e for e in self.embers if e['age'] < e['life']]

        # expire after expand + dot duration
        if elapsed > (self.expand_ms + self.dot_duration_ms):
            return False

        return True

    def draw(self, screen, camera_x, camera_y):
        """Draw burst: multi-layer gradient, pulsing ring, sparks, embers."""
        radius = int(self.current_radius)
        if radius <= 0:
            return

        # Draw multi-layer gradient circle by drawing stacked circles with decreasing alpha
        layers = 10
        for i in range(layers, 0, -1):
            r = int(radius * (i / layers))
            alpha = int(100 * (i / layers) * 0.9)
            # color shifts: inner more pink/white, outer more orange/pink
            rr = int(255)
            gg = int(120 + (i / layers) * 80)  # 120-200
            bb = int(170 + (i / layers) * 60)  # 170-230
            col = (rr, gg, bb, alpha)
            surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, col, (r, r), r)
            screen.blit(surf, (self.x - r - camera_x, self.y - r - camera_y))

        # Pulsing outer ring (gives impact)
        pulse_radius = radius + int(6 * math.sin(self.pulse_phase) + 6)
        ring_surf = pygame.Surface((pulse_radius*2+4, pulse_radius*2+4), pygame.SRCALPHA)
        ring_alpha = int(180 * (1 - (pulse_radius - radius) / 20.0))
        pygame.draw.circle(ring_surf, (255, 200, 220, max(0, ring_alpha)), (pulse_radius+2, pulse_radius+2), pulse_radius, width=4)
        screen.blit(ring_surf, (self.x - pulse_radius - 2 - camera_x, self.y - pulse_radius - 2 - camera_y))

        # Inner core flash at growth moment (brighter when still expanding)
        now = pygame.time.get_ticks()
        elapsed = now - self.start_time
        if elapsed < self.expand_ms:
            core_alpha = int(220 * (1 - elapsed / self.expand_ms))
            core_r = max(8, int(radius * 0.12))
            core_surf = pygame.Surface((core_r*2, core_r*2), pygame.SRCALPHA)
            pygame.draw.circle(core_surf, (255, 255, 255, core_alpha), (core_r, core_r), core_r)
            screen.blit(core_surf, (self.x - core_r - camera_x, self.y - core_r - camera_y))

        # Draw sparks (small moving particles)
        for p in self.particles:
            px = int(p['x'] - camera_x)
            py = int(p['y'] - camera_y)
            a = max(0, min(255, int(255 * (1 - p['age'] / p['life']))))
            color = (p['color'][0], p['color'][1], p['color'][2], a)
            s = max(1, int(p['size'] * (1 - p['age'] / p['life'])))
            surf = pygame.Surface((s*2, s*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (s, s), s)
            screen.blit(surf, (px - s, py - s))

        # Draw embers (lingering)
        for e in self.embers:
            ex = int(e['x'] - camera_x)
            ey = int(e['y'] - camera_y)
            a = max(0, min(200, int(200 * (1 - e['age'] / e['life']))))
            size = max(1, int(e['size'] * (1 - e['age'] / e['life'])))
            surf = pygame.Surface((size*3, size*3), pygame.SRCALPHA)
            pygame.draw.circle(surf, (e['color'][0], e['color'][1], e['color'][2], a), (size+1, size+1), size)
            screen.blit(surf, (ex - size - 1, ey - size - 1))