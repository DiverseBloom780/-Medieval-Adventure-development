# hud.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

import pygame
from ui_theme import UI_FG, WHITE, DIFF_COLORS, HEALTH_GREEN, HEALTH_YELLOW, HEALTH_RED
from ui_utils import clamp, tri_lerp_color, draw_text, draw_round_rect, format_score, pulse

@dataclass
class HUDState:
    # Required
    health: float
    health_max: float
    score: int
    difficulty: str

    # Optional stats
    ammo: Optional[int] = None
    ammo_max: Optional[int] = None
    fps: float = 0.0

class HUD:
    """
    Game HUD with:
    - Smoothed health bar (color shifts from red->yellow->green)
    - Low‑hp pulse vignette
    - Score, ammo (icons or numeric), difficulty (color‑coded), FPS
    - Resolution scaling & font caching
    """
    def __init__(self, screen_size: Tuple[int, int], base_ref: Tuple[int, int] = (1280, 720)) -> None:
        self.w, self.h = screen_size
        self.scale = min(self.w / base_ref[0], self.h / base_ref[1])
        self.margin = int(10 * self.scale)

        # Fonts
        self.font_large = self._get_font(pref="consolas", px=int(24 * self.scale))
        self.font_small = self._get_font(pref="consolas", px=int(16 * self.scale))

        # Smoothing state
        self._health_smoothed = None  # type: Optional[float]
        self._time_accum = 0.0

        # Precompute bar sizes
        self.health_bar_size = (int(180 * self.scale), int(18 * self.scale))
        self.ammo_icon_size = (int(8 * self.scale), int(12 * self.scale))  # little "bolt" rectangles

        # Vignette surface for low HP
        self._vignette = pygame.Surface((self.w, self.h), pygame.SRCALPHA)

    def _get_font(self, pref: str, px: int) -> pygame.font.Font:
        try:
            name = pygame.font.match_font(pref) or pygame.font.match_font("dejavusansmono") or None
            return pygame.font.Font(name, px) if name else pygame.font.SysFont(pref, px)
        except Exception:
            return pygame.font.SysFont("consolas", px)

    def update(self, state: HUDState, dt: float) -> None:
        self._time_accum += dt
        # Smooth health (exponential approach)
        cur = clamp(state.health, 0, max(1.0, state.health_max))
        if self._health_smoothed is None:
            self._health_smoothed = cur
        else:
            # 12 Hz-ish smoothing
            rate = 12.0
            self._health_smoothed += (cur - self._health_smoothed) * (1 - pow(2.71828, -rate * dt))

    # Public API
    def draw(self, s: pygame.Surface, state: HUDState) -> None:
        dt = 1.0 / max(1.0, state.fps)  # safe fallback
        self.update(state, dt)

        x = self.margin
        y = self.margin

        # --- Health numeric text ---
        health_int = int(round(state.health))
        draw_text(s, f"Health: {health_int}", self.font_large, WHITE, (x, y))

        # --- Health bar ---
        bar_w, bar_h = self.health_bar_size
        bar_rect = pygame.Rect(x, y + self.font_large.get_height() + int(4 * self.scale), bar_w, bar_h)
        pygame.draw.rect(s, (60, 60, 60), bar_rect, border_radius=int(6 * self.scale))  # background

        frac = 0.0
        if state.health_max > 0:
            frac = clamp((self._health_smoothed or 0) / state.health_max, 0, 1)

        fill_w = max(0, int(bar_w * frac))
        fill_rect = pygame.Rect(bar_rect.left, bar_rect.top, fill_w, bar_rect.height)

        fill_col = tri_lerp_color(HEALTH_RED, HEALTH_YELLOW, HEALTH_GREEN, frac)
        draw_round_rect(s, fill_col, fill_rect, radius=int(6 * self.scale))

        # Border
        pygame.draw.rect(s, (20, 20, 20), bar_rect, width=max(1, int(2 * self.scale)), border_radius=int(6 * self.scale))

        y = bar_rect.bottom + int(6 * self.scale)

        # --- Score ---
        score_str = format_score(state.score)
        draw_text(s, f"Score: {score_str}", self.font_large, UI_FG, (x, y))
        y += self.font_large.get_height() + int(2 * self.scale)

        # --- Ammo ---
        if state.ammo is not None:
            draw_text(s, "Ammo:", self.font_large, UI_FG, (x, y))
            ammo_x = x + self.font_large.size("Ammo: ")[0] + int(8 * self.scale)
            if state.ammo_max is not None and state.ammo_max <= 12:
                # icon mode for small mags
                self._draw_ammo_icons(s, ammo_x, y + 2, state.ammo, state.ammo_max)
            else:
                # text mode for larger pools
                draw_text(s, str(state.ammo), self.font_large, UI_FG, (ammo_x, y))
            y += self.font_large.get_height() + int(2 * self.scale)

        # --- Difficulty ---
        diff_key = str(state.difficulty).strip().lower()
        diff_col = DIFF_COLORS.get(diff_key, UI_FG)
        draw_text(s, f"Difficulty: {state.difficulty}", self.font_large, diff_col, (x, y))

        # --- FPS (top-right) ---
        fps_str = f"{state.fps:0.0f} FPS"
        rgt = self.w - self.margin - self.font_large.size(fps_str)[0]
        draw_text(s, fps_str, self.font_large, UI_FG, (rgt, self.margin))

        # --- Low-HP vignette pulse ---
        self._draw_low_hp_vignette(s, frac)

    def _draw_ammo_icons(self, s: pygame.Surface, x: int, y: int, ammo: int, ammo_max: int) -> None:
        w, h = self.ammo_icon_size
        gap = max(1, int(2 * self.scale))
        for i in range(ammo_max):
            col = (230, 230, 230) if i < ammo else (100, 100, 100)
            pygame.draw.rect(s, col, (x + i * (w + gap), y, w, h), border_radius=max(2, int(2 * self.scale)))

    def _draw_low_hp_vignette(self, s: pygame.Surface, health_frac: float) -> None:
        # Pulse and opacity increase as health goes down (<35%)
        if health_frac >= 0.35:
            return
        alpha_base = int((1.0 - (health_frac / 0.35)) * 150)  # 0..150
        alpha = int(alpha_base * pulse(self._time_accum, speed=1.3, lo=0.7, hi=1.0))
        self._vignette.fill((255, 0, 0, alpha))
        s.blit(self._vignette, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
