# weather.py
# Tiny weather controller for Pygame scenes (clear, clouds, rain, storm, fog, snow),
# with layered clouds, wind gusts, optional lightning bolts, and smooth transitions.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Optional, Dict
import pygame
import random
import math

from clouds import CloudLayer
from lightning import LightningManager

Color = Tuple[int, int, int]


@dataclass
class Raindrop:
    x: float
    y: float
    vx: float
    vy: float
    life: float

    def update(self, dt: float, width: int, height: int) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.y > height + 8:
            self.life = 0.0

    def draw(self, s: pygame.Surface) -> None:
        end = (int(self.x - self.vx * 0.02), int(self.y - self.vy * 0.02))
        pygame.draw.line(s, (170, 170, 200), (int(self.x), int(self.y)), end, 1)


@dataclass
class Snowflake:
    x: float
    y: float
    vx: float
    vy: float
    sway_t: float
    life: float

    def update(self, dt: float, width: int, height: int) -> None:
        # Gentle sway
        self.sway_t += dt
        sway = math.sin(self.sway_t * 2.2) * 18.0
        self.x += (self.vx + sway * 0.4) * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.y > height + 6:
            self.life = 0.0

    def draw(self, s: pygame.Surface) -> None:
        pygame.draw.circle(s, (245, 245, 255), (int(self.x), int(self.y)), 1)


@dataclass
class WeatherController:
    width: int
    height: int
    seed: int = 4242

    # state machine
    state: str = "clear"              # "clear" | "cloudy" | "rain" | "storm" | "fog" | "snow"
    density: float = 0.0              # 0..1 intensity
    wind: float = -60.0               # px/s (negative = left)

    # transition support
    target_state: Optional[str] = None
    transition_time: float = 0.0      # seconds total
    transition_timer: float = 0.0     # counts down
    _density_from: float = 0.0
    _density_to: float = 0.0

    # particles
    drops: List[Raindrop] = field(default_factory=list)
    flakes: List[Snowflake] = field(default_factory=list)

    # layers / fx
    clouds_back: CloudLayer = field(init=False)
    clouds_front: CloudLayer = field(init=False)
    lightning: LightningManager = field(init=False)

    # internals
    _rng: random.Random = field(default_factory=random.Random)
    _flash: float = 0.0        # legacy screen flash timer (still used subtly in storm)
    _fog_phase: float = 0.0
    _wind_t: float = 0.0       # wind gust timer (low frequency)
    on_lightning: Optional[Callable[[], None]] = None

    def __post_init__(self) -> None:
        self._rng.seed(self.seed)
        # Layered clouds: slower high layer + faster front layer
        self.clouds_back = CloudLayer(self.width, self.height, seed=self.seed ^ 0xA5, speed=10.0, alpha=120)
        self.clouds_front = CloudLayer(self.width, self.height, seed=self.seed ^ 0x5A, speed=26.0, alpha=170, scale=1.3)
        self.lightning = LightningManager(self.width, self.height, seed=self.seed ^ 0x33)

        # Start with light clouds on clear
        self._apply_cloud_preset()

    # ------------------- Public API -------------------

    def set_state(self, state: str, density: float = 0.6) -> None:
        """Hard‑set weather immediately."""
        self.state = state
        self.target_state = None
        self.density = max(0.0, min(1.0, density))
        self._apply_cloud_preset()

    def transition_to(self, state: str, density: float, duration: float = 2.0) -> None:
        """Smoothly transition from current state/density to target over duration."""
        self.target_state = state
        self.transition_time = max(0.01, duration)
        self.transition_timer = self.transition_time
        self._density_from = self.density
        self._density_to = max(0.0, min(1.0, density))

    def to_dict(self) -> Dict:
        return {
            "state": self.state,
            "density": self.density,
            "wind": self.wind,
            "seed": self.seed,
            "clouds": self.clouds_back.to_dict(),  # same schema for both
        }

    def from_dict(self, data: Dict) -> None:
        self.state = str(data.get("state", self.state))
        self.density = float(data.get("density", self.density))
        self.wind = float(data.get("wind", self.wind))
        new_seed = int(data.get("seed", self.seed))
        if new_seed != self.seed:
            self.seed = new_seed
            self._rng.seed(self.seed)
            self.clouds_back.respawn(seed=self.seed ^ 0xA5)
            self.clouds_front.respawn(seed=self.seed ^ 0x5A)
            self.lightning.respawn(seed=self.seed ^ 0x33)
        # cloud overrides
        clouds_cfg = data.get("clouds")
        if isinstance(clouds_cfg, dict):
            self.clouds_back.from_dict(clouds_cfg)
            self.clouds_front.from_dict(clouds_cfg)

    def ambient_darkening(self) -> float:
        """
        Extra darkness for world tint (0..1).
        Incorporates cloud cover and precipitation type.
        """
        base = 0.0
        # cloud cover contributes
        base += 0.15 * self._cloud_coverage()
        if self.state == "fog":
            base += 0.12 * self.density
        elif self.state == "rain":
            base += 0.18 * self.density
        elif self.state == "storm":
            base += 0.35 * self.density
        elif self.state == "snow":
            base += 0.10 * self.density
        return max(0.0, min(1.0, base))

    # ------------------- Update & Draw -------------------

    def update(self, dt: float) -> None:
        # Wind gusts (slow oscillation)
        self._wind_t += dt
        gust = math.sin(self._wind_t * 0.25)  # very slow
        gust2 = math.sin(self._wind_t * 0.07 + 1.3) * 0.5
        effective_wind = self.wind + 30.0 * gust + 18.0 * gust2

        # Handle transition
        if self.target_state and self.transition_timer > 0.0:
            self.transition_timer = max(0.0, self.transition_timer - dt)
            k = 1.0 - (self.transition_timer / self.transition_time)
            # smoothstep for nicer easing
            k = k * k * (3 - 2 * k)
            self.density = self._density_from + (self._density_to - self._density_from) * k
            if self.transition_timer == 0.0:
                self.state = self.target_state
                self.target_state = None
                self._apply_cloud_preset()

        # Clouds
        cover = self._cloud_coverage()
        self.clouds_back.set_density(cover * 0.6)
        self.clouds_front.set_density(cover)
        self.clouds_back.update(dt, wind=effective_wind * 0.2)
        self.clouds_front.update(dt, wind=effective_wind * 0.6)

        # Precipitation spawns
        if self.state in ("rain", "storm"):
            want = int(420 * self.density)
            while len(self.drops) < want:
                x = self._rng.uniform(-20, self.width + 20)
                y = self._rng.uniform(-50, -4)
                vx = effective_wind + self._rng.uniform(-30, 10)
                vy = self._rng.uniform(400, 720) * (1.25 if self.state == "storm" else 1.0)
                life = self._rng.uniform(0.6, 2.0)
                self.drops.append(Raindrop(x, y, vx, vy, life))

        elif self.state == "snow":
            want = int(220 * self.density)
            while len(self.flakes) < want:
                x = self._rng.uniform(-20, self.width + 20)
                y = self._rng.uniform(-50, -6)
                vx = effective_wind * 0.25 + self._rng.uniform(-20, 20)
                vy = self._rng.uniform(35, 70)
                life = self._rng.uniform(2.0, 6.0)
                self.flakes.append(Snowflake(x, y, vx, vy, self._rng.uniform(0, math.tau), life))

        # Update particles
        for d in self.drops:
            d.update(dt, self.width, self.height)
        self.drops = [d for d in self.drops if d.life > 0.0]

        for f in self.flakes:
            f.update(dt, self.width, self.height)
        self.flakes = [f for f in self.flakes if f.life > 0.0]

        # Fog phase for subtle motion
        if self.state == "fog":
            self._fog_phase += dt * 0.1

        # Lightning
        if self.state == "storm" and self.density > 0.25:
            # Probability scales with density
            strike_p = 0.015 * self.density
            if self.lightning.maybe_strike(strike_p):
                if self.on_lightning:
                    try:
                        self.on_lightning()
                    except Exception:
                        pass
        self.lightning.update(dt)

        # Legacy subtle flash (soft global brightening during storm)
        if self.lightning.flash_alpha > 0.0:
            self._flash = self.lightning.flash_alpha
        else:
            self._flash = max(0.0, self._flash - dt)

    # Background effects (behind world)
    def draw_background(self, s: pygame.Surface, ground_y: int) -> None:
        # Far clouds
        self.clouds_back.draw(s, y=0, height=int(ground_y * 0.9))
        # Low-lying fog bank behind world
        if self.state == "fog":
            fog = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            for i in range(6):
                y = int(ground_y - 30 + i * 12 + math.sin(self._fog_phase + i) * 6)
                alpha = int(26 + i * 12 * self.density)
                pygame.draw.rect(fog, (210, 210, 210, alpha), (0, y, self.width, 14))
            s.blit(fog, (0, 0))

    # Foreground effects (in front of world)
    def draw_foreground(self, s: pygame.Surface) -> None:
        # Near clouds
        self.clouds_front.draw(s)

        # Precipitation
        if self.state in ("rain", "storm"):
            for d in self.drops:
                d.draw(s)
        elif self.state == "snow":
            for f in self.flakes:
                f.draw(s)

        # Lightning & screen flash overlay
        self.lightning.draw(s)
        if self._flash > 0.0:
            veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            veil.fill((255, 255, 255, int(140 * min(1.0, self._flash * 10))))
            s.blit(veil, (0, 0))

        # Foreground general fog veil
        if self.state == "fog":
            alpha = int(90 * self.density)
            fog = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            fog.fill((220, 220, 220, alpha))
            s.blit(fog, (0, 0))

    # ------------------- Internals -------------------

    def _cloud_coverage(self) -> float:
        """Map current state+density to cloud coverage 0..1."""
        if self.state == "clear":
            return 0.15 * self.density
        if self.state == "cloudy":
            return 0.35 + 0.55 * self.density
        if self.state == "rain":
            return 0.65 + 0.35 * self.density
        if self.state == "storm":
            return 0.85
        if self.state == "fog":
            return 0.5 * self.density
        if self.state == "snow":
            return 0.6 + 0.3 * self.density
        return 0.0

    def _apply_cloud_preset(self) -> None:
        """Tune cloud visuals when state changes (parallax balance, alpha)."""
        cover = self._cloud_coverage()
        self.clouds_back.set_density(cover * 0.6)
        self.clouds_front.set_density(cover)
        if self.state == "storm":
            self.clouds_back.alpha = 160
            self.clouds_front.alpha = 200
        elif self.state == "rain":
            self.clouds_back.alpha = 140
            self.clouds_front.alpha = 185
        elif self.state == "cloudy":
            self.clouds_back.alpha = 120
            self.clouds_front.alpha = 170
        elif self.state == "snow":
            self.clouds_back.alpha = 140
            self.clouds_front.alpha = 190
        else:  # clear/fog
            self.clouds_back.alpha = 110
            self.clouds_front.alpha = 150
