# lightning.py
# Procedural lightning bolts with branching, theming, events, and screen flash.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Iterable, Optional, Dict, Any
import pygame
import random
import math

from lightning_theme import LightningStyle, default_style

Point = Tuple[int, int]

# ---------------------------------------------------------------------------
# Midpoint displacement (jagged path generator)
# ---------------------------------------------------------------------------

def _mid_displace(p0: Point, p1: Point, roughness: float, depth: int, rng: random.Random) -> List[Point]:
    """Recursive midpoint displacement to create a jagged polyline."""
    if depth <= 0:
        return [p0, p1]
    x0, y0 = p0; x1, y1 = p1
    mx = (x0 + x1) * 0.5
    my = (y0 + y1) * 0.5
    # perpendicular offset
    dx, dy = (x1 - x0), (y1 - y0)
    length = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length
    # bias offset a little downward so bolts prefer going toward ground
    bias = 0.35
    perp = rng.uniform(-1.0, 1.0)
    along = rng.uniform(-1.0, 1.0) * 0.25  # tiny longitudinal wobble
    offset = perp * roughness * max(6.0, length * 0.12)
    mid = (int(mx + nx * offset + dx * along * 0.1),
           int(my + ny * offset + dy * along * 0.1 + bias * roughness * 4.0))
    left = _mid_displace(p0, mid, roughness * 0.65, depth - 1, rng)
    right = _mid_displace(mid, p1, roughness * 0.65, depth - 1, rng)
    return left[:-1] + right


# ---------------------------------------------------------------------------
# Bolt
# ---------------------------------------------------------------------------

@dataclass
class LightningBolt:
    points: List[Point]
    style: LightningStyle
    ttl: float = 0.12
    thickness: int = 3
    life: float = 0.12
    children: List["LightningBolt"] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Ensure life stores the initial TTL for a sane alpha curve
        if self.life <= 0:
            self.life = max(self.ttl, 0.001)

    def update(self, dt: float) -> None:
        self.ttl = max(0.0, self.ttl - dt)
        for c in self.children:
            c.update(dt)
        self.children = [c for c in self.children if c.alive]

    @property
    def alive(self) -> bool:
        return self.ttl > 0.0

    # -- drawing helpers -----------------------------------------------------

    def _bounds(self) -> pygame.Rect:
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        pad = max(self.thickness, self.style.outer_glow_thickness) + 8
        return pygame.Rect(min(xs) - pad, min(ys) - pad,
                           (max(xs) - min(xs)) + pad * 2,
                           (max(ys) - min(ys)) + pad * 2)

    def _rel_points(self, offset: Tuple[int, int]) -> List[Point]:
        ox, oy = offset
        return [(x - ox, y - oy) for (x, y) in self.points]

    def draw(self, s: pygame.Surface) -> None:
        if len(self.points) < 2 or not self.alive:
            return

        # Fraction of life remaining (ease-out for nicer fade)
        f = max(0.0, min(1.0, self.ttl / self.life))
        f = pow(f, 0.55)

        rect = self._bounds()
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pts = self._rel_points((rect.left, rect.top))

        # Layer 1: outer glow (largest, faint)
        if self.style.outer_glow_thickness > 0:
            c = (*self.style.outer_glow_color[:3], int(self.style.outer_glow_color[3] * f))
            pygame.draw.lines(overlay, c, False, pts, max(1, self.style.outer_glow_thickness))

        # Layer 2: inner glow
        if self.style.glow_thickness > 0:
            c = (*self.style.glow_color[:3], int(self.style.glow_color[3] * f))
            pygame.draw.lines(overlay, c, False, pts, max(1, self.style.glow_thickness))

        # Layer 3: core (bright, thinner)
        core_thickness = max(1, min(self.thickness, self.style.core_thickness))
        c = (*self.style.core_color[:3], int(self.style.core_color[3] * f))
        pygame.draw.lines(overlay, c, False, pts, core_thickness)

        # Composite additively for a light bloom effect
        s.blit(overlay, rect.topleft, special_flags=pygame.BLEND_ADD)

        # Draw branches
        for c in self.children:
            c.draw(s)


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

@dataclass
class LightningManager:
    width: int
    height: int
    seed: int = 0
    style: LightningStyle = field(default_factory=default_style)
    max_bolts: int = 18
    bolts: List[LightningBolt] = field(default_factory=list)
    flash_alpha: float = 0.0
    _rng: random.Random = field(default_factory=random.Random)
    _events: List[Tuple[str, Dict[str, Any]]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._rng.seed(self.seed)

    # -- Events --------------------------------------------------------------

    def poll_events(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Retrieve and clear queued events. e.g., ('strike', {'start':(x,y),'end':(x,y)})"""
        ev = self._events[:]
        self._events.clear()
        return ev

    # -- Spawning ------------------------------------------------------------

    def maybe_strike(self, probability: float) -> bool:
        """Random strike using manager's screen bounds."""
        if self._rng.random() < probability:
            # Start somewhere near the top quarter, end in bottom half-ish
            start = (self._rng.randint(0, self.width),
                     self._rng.randint(0, int(self.height * 0.25)))
            end = (self._rng.randint(int(self.width * 0.15), int(self.width * 0.85)),
                   self._rng.randint(int(self.height * 0.45), int(self.height * 0.92)))
            self.strike_between(start, end)
            return True
        return False

    def strike_to(self, target: Point, cloud_band: Tuple[int, int] = (0, 25)) -> None:
        """Strike from a random x at the top cloud band (in % of height) down to a target."""
        top_min, top_max = cloud_band
        y0 = int(self.height * (top_min / 100.0))
        y1 = int(self.height * (top_max / 100.0))
        start = (self._rng.randint(0, self.width), self._rng.randint(y0, max(y0, y1)))
        self.strike_between(start, target)

    def strike_between(self, start: Point, end: Point) -> None:
        """Spawn a main bolt (with branches) between two points."""
        if len(self.bolts) >= self.max_bolts:
            # Drop the oldest to keep CPU reasonable
            self.bolts.pop(0)

        pts = _mid_displace(start, end, self.style.roughness, self.style.depth, self._rng)
        ttl = 0.10 + self._rng.uniform(0.04, 0.12)
        main = LightningBolt(
            points=pts,
            style=self.style,
            ttl=ttl,
            life=ttl,
            thickness=self._rng.randint(self.style.core_thickness, self.style.core_thickness + 2),
        )
        self._spawn_branches(main, self.style)
        self.bolts.append(main)

        # Flash & event
        self.flash_alpha = max(self.flash_alpha, self.style.flash_alpha_base + self._rng.uniform(0.0, self.style.flash_alpha_jitter))
        self._events.append(("strike", {"start": start, "end": end}))

    def _spawn_branches(self, bolt: LightningBolt, style: LightningStyle) -> None:
        """Create short offshoot branches from the main bolt."""
        if style.branch_chance <= 0.0 or style.branch_depth <= 0:
            return
        pts = bolt.points
        if len(pts) < 4:
            return

        # Choose some indices along the main path to sprout branches
        count = self._rng.randint(0, 2)
        for _ in range(count):
            if self._rng.random() > style.branch_chance:
                continue
            idx = self._rng.randint(1, max(1, len(pts) - 2))
            base = pts[idx]
            # Aim the branch generally downward, with sideways spread
            angle = math.atan2(pts[-1][1] - pts[0][1], pts[-1][0] - pts[0][0])
            spread = self._rng.uniform(-0.9, 0.9)
            length = self._rng.uniform(40, 120)
            ang = angle + spread
            end = (int(base[0] + math.cos(ang) * length),
                   int(base[1] + math.sin(ang) * length))
            bpts = _mid_displace(base, end, style.roughness * 0.8, max(1, style.branch_depth - 1), self._rng)
            ttl = bolt.life * self._rng.uniform(0.55, 0.85)
            child = LightningBolt(
                points=bpts,
                style=style,
                ttl=ttl,
                life=ttl,
                thickness=max(1, bolt.thickness - 1),
            )
            bolt.children.append(child)

    # -- Lifetime ------------------------------------------------------------

    def update(self, dt: float) -> None:
        for b in self.bolts:
            b.update(dt)
        self.bolts = [b for b in self.bolts if b.alive]
        # Fade the flash
        self.flash_alpha = max(0.0, self.flash_alpha - dt * self.style.flash_fade_speed)

    # -- Drawing -------------------------------------------------------------

    def draw(self, s: pygame.Surface) -> None:
        """Draw all bolts (glow + core)."""
        for b in self.bolts:
            b.draw(s)

    def draw_flash(self, s: pygame.Surface) -> None:
        """Draw a full-screen flash overlay (call after world, before UI)."""
        if self.flash_alpha <= 0.0:
            return
        veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        # Tint toward the glow color for a cohesive look
        r, g, b, _ = self.style.glow_color
        veil.fill((r, g, b, int(255 * self.flash_alpha)))
        s.blit(veil, (0, 0), special_flags=pygame.BLEND_ADD)

    # -- Utilities -----------------------------------------------------------

    def respawn(self, *, seed: Optional[int] = None) -> None:
        """Reset RNG and clear bolts/flash."""
        if seed is not None:
            self._rng.seed(seed)
        else:
            self._rng.seed(self.seed)
        self.bolts.clear()
        self.flash_alpha = 0.0
        self._events.clear()
