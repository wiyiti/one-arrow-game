# -*- coding: utf-8 -*-
"""
"一箭又一箭" 小游戏
课程：软件工程 第二次个人作业
运行：python one_arrow_game.py  （需先 pip install pygame）

玩法：
  - 棋盘中的箭头朝上/下/左/右。
  - 点击某个箭头，若它沿指向方向到棋盘边界之间没有其他箭头，箭头飞出棋盘；
    否则该箭头被挡住，不能消除，晃动变红，失误 -1，星星 -1。
  - 每关限失误 3 次、限时 75 秒。耗尽则失败。
  - 清空本关全部箭头则通关，按失误次数评 1-3 星。
"""

import sys
import os
import json
import math
import time
import pygame

# ---------- 常量 ----------
CELL_SIZE = 90
BOARD_TOP = 140
SCREEN_W, SCREEN_H = 600, 720
FPS = 60
MAX_MISSES = 3
TIME_LIMIT = 75          # 每关秒数
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "progress.json")

# 颜色
BG_COLOR        = (245, 240, 230)
BOARD_COLOR     = (222, 212, 190)
GRID_LINE       = (185, 175, 155)
BLOCKED_COLOR   = (200, 80, 80)
TEXT_COLOR      = (55, 55, 55)
BTN_COLOR       = (90, 130, 200)
BTN_HOVER       = (115, 155, 225)
GOLD            = (240, 195, 60)
GRAY            = (170, 165, 155)
GREEN           = (80, 170, 100)
RED             = (200, 80, 80)
WHITE           = (255, 255, 255)

# 四种方向各自的颜色
DIR_COLORS = {
    'U': (60, 160, 90),    # 绿
    'D': (60, 95, 170),    # 蓝
    'L': (220, 140, 50),   # 橙
    'R': (150, 80, 170),   # 紫
}

DIRS = {'U': (-1, 0), 'D': (1, 0), 'L': (0, -1), 'R': (0, 1)}

# ---------- 关卡（按箭头数量由少到多排列，均已用求解器验证可通关） ----------
LEVELS = [
    # 1: 3x3, 5 箭头
    [
        ['R', None, 'D'],
        [None, 'U',  None],
        ['U', None, 'R'],
    ],
    # 2: 4x4, 6 箭头
    [
        ['R', None, 'D', None],
        [None, None, None, 'U'],
        ['D', None, None, 'L'],
        [None, 'R', None, None],
    ],
    # 3: 4x4, 8 箭头
    [
        ['R', 'D', None, 'U'],
        [None, None, 'L', None],
        ['U', None, None, 'R'],
        [None, 'L', 'D', None],
    ],
    # 4: 5x4, 10 箭头
    [
        ['R', None, 'D', None],
        [None, 'U', None, 'L'],
        ['L', None, 'R', None],
        [None, 'D', None, 'U'],
        ['R', None, None, 'D'],
    ],
    # 5: 5x5, 11 箭头
    [
        ['R', None, 'D', None, 'U'],
        [None, 'L', None, 'R', None],
        ['U', None, None, None, 'D'],
        [None, None, 'R', None, None],
        ['D', None, 'L', None, 'R'],
    ],
    # 6: 5x5, 12 箭头
    [
        ['R', 'U', 'D', None, 'U'],
        [None, 'L', None, 'R', None],
        ['U', None, None, None, 'D'],
        [None, None, 'R', None, None],
        ['D', None, 'L', None, 'R'],
    ],
    # 7: 5x5, 14 箭头
    [
        ['R', 'D', None, 'U', 'U'],
        [None, None, 'L', None, 'R'],
        ['U', None, 'R', None, 'D'],
        ['R', None, 'U', None, 'R'],
        [None, 'D', None, 'R', None],
    ],
]


class ArrowGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("一箭又一箭")
        self.clock = pygame.time.Clock()
        # 字体
        font_candidates = [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\msyhbd.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
        ]
        self._font_path = next((p for p in font_candidates if os.path.exists(p)), None)
        self.font_big   = self._mkfont(48)
        self.font_mid   = self._mkfont(28)
        self.font_small = self._mkfont(20)
        self.font_tiny  = self._mkfont(16)

        # 存档：{unlocked: int, stars: {str(level_idx): int}}
        self.progress = self._load_progress()

        self.state = 'MENU'   # MENU / LEVEL_SELECT / PLAY / LEVEL_COMPLETE / WIN / LOSE
        self.level_idx = 0
        self.lose_reason = ''
        self.menu_start_btn = pygame.Rect(180, 340, 240, 55)
        self.menu_select_btn = pygame.Rect(180, 415, 240, 55)
        self.restart_btn = pygame.Rect(460, 20, 120, 38)
        self.back_btn = pygame.Rect(20, 20, 100, 38)
        self.undo_btn = pygame.Rect(460, 65, 55, 32)
        self.hint_btn = pygame.Rect(525, 65, 55, 32)
        self.level_buttons = []  # 选关按钮
        self.load_level(0)

    def _mkfont(self, size):
        return pygame.font.Font(self._font_path, size) if self._font_path else pygame.font.Font(None, size)

    def _load_progress(self):
        try:
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data.setdefault('unlocked', 1)
                data.setdefault('stars', {})
                return data
        except Exception:
            return {'unlocked': 1, 'stars': {}}

    def _save_progress(self):
        try:
            with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- 关卡与状态 ----------
    def load_level(self, idx):
        self.grid = [row[:] for row in LEVELS[idx]]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.misses_left = MAX_MISSES
        self.stars = 3
        self.flying = []     # 飞出棋盘的箭头
        self.bouncing = []   # 被挡住后飞出又弹回的箭头
        self.history = []    # 已消除的箭头 [(row, col, dir)]
        self.hint_pos = None # 提示高亮的格子 (row, col)
        self.hint_start = 0
        self.board_w = self.cols * CELL_SIZE
        self.board_h = self.rows * CELL_SIZE
        self.board_x = (SCREEN_W - self.board_w) // 2
        self.board_y = BOARD_TOP
        self.level_start = time.time()
        self.time_left = TIME_LIMIT
        self.lose_reason = ''

    def remaining_arrows(self):
        return sum(1 for row in self.grid for c in row if c is not None)

    def is_blocked(self, row, col):
        d = self.grid[row][col]
        dr, dc = DIRS[d]
        r, c = row + dr, col + dc
        while 0 <= r < self.rows and 0 <= c < self.cols:
            if self.grid[r][c] is not None:
                return True
            r += dr
            c += dc
        return False

    # ---------- 事件 ----------
    def handle_click(self, pos):
        mx, my = pos
        if self.restart_btn.collidepoint(mx, my):
            self.load_level(self.level_idx)
            return
        if self.back_btn.collidepoint(mx, my):
            self.state = 'LEVEL_SELECT'
            return
        # 撤销按钮
        if self.undo_btn.collidepoint(mx, my):
            if self.history:
                r, c, d = self.history.pop()
                self.grid[r][c] = d
            return
        # 提示按钮：找一个可消除的箭头高亮
        if self.hint_btn.collidepoint(mx, my):
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.grid[r][c] is not None and not self.is_blocked(r, c):
                        self.hint_pos = (r, c)
                        self.hint_start = time.time()
                        return
            return
        col = (mx - self.board_x) // CELL_SIZE
        row = (my - self.board_y) // CELL_SIZE
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        if self.grid[row][col] is None:
            return
        if any(b['row'] == row and b['col'] == col for b in self.bouncing):
            return
        if self.is_blocked(row, col):
            d = self.grid[row][col]
            dr, dc = DIRS[d]
            self.bouncing.append({
                'row': row, 'col': col, 'dir': d,
                'dr': dr, 'dc': dc, 'start': time.time(),
            })
            self.misses_left -= 1
            self.stars = max(0, 3 - (MAX_MISSES - self.misses_left))
            if self.misses_left <= 0:
                self.lose_reason = "失误次数用完"
                self.state = 'LOSE'
        else:
            d = self.grid[row][col]
            dr, dc = DIRS[d]
            self.flying.append({
                'row': row, 'col': col, 'dir': d,
                'dr': dr, 'dc': dc, 'start': time.time(),
            })
            self.grid[row][col] = None
            self.history.append((row, col, d))

    # ---------- 更新 ----------
    def update(self):
        now = time.time()
        self.flying = [f for f in self.flying if now - f['start'] < 0.4]
        self.bouncing = [b for b in self.bouncing if now - b['start'] < 0.5]
        if self.state == 'PLAY':
            self.time_left = max(0, TIME_LIMIT - (now - self.level_start))
            if self.time_left <= 0:
                self.lose_reason = "时间用完"
                self.state = 'LOSE'
            elif self.remaining_arrows() == 0 and not self.flying:
                # 通关
                earned = self.stars
                prev = self.progress['stars'].get(str(self.level_idx), 0)
                if earned > prev:
                    self.progress['stars'][str(self.level_idx)] = earned
                if self.level_idx + 1 >= self.progress['unlocked']:
                    self.progress['unlocked'] = min(len(LEVELS), self.level_idx + 2)
                self._save_progress()
                if self.level_idx + 1 < len(LEVELS):
                    self.state = 'LEVEL_COMPLETE'
                else:
                    self.state = 'WIN'

    # ---------- 绘制 ----------
    def _draw_arrow_on(self, surf, x, y, direction, color, size):
        """在指定 surface 上画箭头（无抗锯齿，供离屏渲染后缩放用）。"""
        h = size // 2
        shaft_w = 10
        if direction in ('U', 'D'):
            shaft = pygame.Rect(x - shaft_w // 2, y - h + 6, shaft_w, size - 12)
        else:
            shaft = pygame.Rect(x - h + 6, y - shaft_w // 2, size - 12, shaft_w)
        pygame.draw.rect(surf, color, shaft, border_radius=3)
        if direction == 'U':
            pts = [(x, y - h), (x - h, y - h + 18), (x + h, y - h + 18)]
        elif direction == 'D':
            pts = [(x, y + h), (x - h, y + h - 18), (x + h, y + h - 18)]
        elif direction == 'L':
            pts = [(x - h, y), (x - h + 18, y - h), (x - h + 18, y + h)]
        else:
            pts = [(x + h, y), (x + h - 18, y - h), (x + h - 18, y + h)]
        pygame.draw.polygon(surf, color, pts)

    def draw_arrow(self, x, y, direction, color=None, size=40):
        """抗锯齿箭头：2倍离屏渲染后平滑缩放。"""
        if color is None:
            color = DIR_COLORS.get(direction, (100, 100, 100))
        S = 2  # 超采样倍数
        big = size * S
        tmp = pygame.Surface((big + 20, big + 20), pygame.SRCALPHA)
        self._draw_arrow_on(tmp, (big + 20) // 2, (big + 20) // 2, direction, color, big)
        scaled = pygame.transform.smoothscale(tmp, (size + 10, size + 10))
        self.screen.blit(scaled, (x - (size + 10) // 2, y - (size + 10) // 2))

    def draw_stars(self, cx, cy, count, star_size=24):
        """在 (cx, cy) 居中画 count 颗实心星，其余空心。"""
        total = 3
        spacing = star_size + 8
        start_x = cx - (total - 1) * spacing // 2
        for i in range(total):
            sx = start_x + i * spacing
            color = GOLD if i < count else GRAY
            # 画五角星（简化为多边形）
            self._draw_star(sx, cy, star_size // 2, color)

    def _draw_star(self, cx, cy, r, color):
        pts = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((cx + rr * math.cos(angle), cy + rr * math.sin(angle)))
        pygame.draw.polygon(self.screen, color, pts)

    def draw_menu(self):
        title = self.font_big.render("一箭又一箭", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 200)))
        tip = self.font_small.render("按正确顺序点击箭头，让它们全部飞出棋盘", True, TEXT_COLOR)
        self.screen.blit(tip, tip.get_rect(center=(SCREEN_W // 2, 270)))
        mouse = pygame.mouse.get_pos()
        for btn, text in [(self.menu_start_btn, "开始游戏"), (self.menu_select_btn, "选择关卡")]:
            color = BTN_HOVER if btn.collidepoint(mouse) else BTN_COLOR
            pygame.draw.rect(self.screen, color, btn, border_radius=10)
            t = self.font_mid.render(text, True, WHITE)
            self.screen.blit(t, t.get_rect(center=btn.center))

    def draw_level_select(self):
        title = self.font_big.render("选择关卡", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 80)))
        # 画返回按钮
        mouse = pygame.mouse.get_pos()
        color = BTN_HOVER if self.back_btn.collidepoint(mouse) else BTN_COLOR
        pygame.draw.rect(self.screen, color, self.back_btn, border_radius=8)
        bt = self.font_small.render("返回", True, WHITE)
        self.screen.blit(bt, bt.get_rect(center=self.back_btn.center))

        self.level_buttons = []
        cols = 4
        bw, bh = 110, 110
        gap = 20
        total_w = cols * bw + (cols - 1) * gap
        start_x = (SCREEN_W - total_w) // 2
        start_y = 180
        for i in range(len(LEVELS)):
            r = i // cols
            c = i % cols
            bx = start_x + c * (bw + gap)
            by = start_y + r * (bh + gap)
            rect = pygame.Rect(bx, by, bw, bh)
            locked = i >= self.progress['unlocked']
            stars_earned = self.progress['stars'].get(str(i), 0)
            if locked:
                pygame.draw.rect(self.screen, GRAY, rect, border_radius=10)
                lock_txt = self.font_mid.render("🔒", True, WHITE)
                self.screen.blit(lock_txt, lock_txt.get_rect(center=rect.center))
            else:
                hovered = rect.collidepoint(mouse)
                pygame.draw.rect(self.screen, BTN_HOVER if hovered else BTN_COLOR, rect, border_radius=10)
                num = self.font_big.render(str(i + 1), True, WHITE)
                self.screen.blit(num, num.get_rect(center=(rect.centerx, rect.centery - 15)))
                # 星星
                star_y = rect.centery + 25
                total = 3
                spacing = 20
                sx0 = rect.centerx - (total - 1) * spacing // 2
                for s in range(total):
                    sc = GOLD if s < stars_earned else (200, 200, 200)
                    self._draw_star(sx0 + s * spacing, star_y, 8, sc)
            self.level_buttons.append((rect, i, locked))

    def draw_hud(self):
        level_txt = self.font_mid.render(f"第 {self.level_idx + 1} 关 / 共 {len(LEVELS)} 关", True, TEXT_COLOR)
        self.screen.blit(level_txt, (20, 20))
        arrows_txt = self.font_small.render(f"剩余箭头：{self.remaining_arrows()}", True, TEXT_COLOR)
        self.screen.blit(arrows_txt, (20, 60))
        # 失误/星星
        miss_color = RED if self.misses_left <= 1 else TEXT_COLOR
        miss_txt = self.font_small.render(f"剩余失误：{self.misses_left}", True, miss_color)
        self.screen.blit(miss_txt, (20, 90))
        # 实时星星
        for s in range(3):
            sx = 220 + s * 24
            sc = GOLD if s < self.stars else GRAY
            self._draw_star(sx, 100, 9, sc)
        # 倒计时
        t = int(self.time_left)
        time_color = RED if t <= 10 else TEXT_COLOR
        time_txt = self.font_small.render(f"{t}s", True, time_color)
        self.screen.blit(time_txt, time_txt.get_rect(topright=(580, 90)))
        # 重新开始按钮
        mouse = pygame.mouse.get_pos()
        color = BTN_HOVER if self.restart_btn.collidepoint(mouse) else BTN_COLOR
        pygame.draw.rect(self.screen, color, self.restart_btn, border_radius=8)
        rb = self.font_small.render("重开本关", True, WHITE)
        self.screen.blit(rb, rb.get_rect(center=self.restart_btn.center))
        # 撤销按钮
        undo_color = BTN_HOVER if self.undo_btn.collidepoint(mouse) else (130, 130, 130)
        pygame.draw.rect(self.screen, undo_color, self.undo_btn, border_radius=6)
        ub = self.font_tiny.render("撤销", True, WHITE)
        self.screen.blit(ub, ub.get_rect(center=self.undo_btn.center))
        # 提示按钮
        hint_color = BTN_HOVER if self.hint_btn.collidepoint(mouse) else (130, 130, 130)
        pygame.draw.rect(self.screen, hint_color, self.hint_btn, border_radius=6)
        hb = self.font_tiny.render("提示", True, WHITE)
        self.screen.blit(hb, hb.get_rect(center=self.hint_btn.center))

    def draw_board(self):
        pygame.draw.rect(self.screen, BOARD_COLOR,
                         (self.board_x, self.board_y, self.board_w, self.board_h),
                         border_radius=8)
        for i in range(self.cols + 1):
            pygame.draw.line(self.screen, GRID_LINE,
                             (self.board_x + i * CELL_SIZE, self.board_y),
                             (self.board_x + i * CELL_SIZE, self.board_y + self.board_h))
        for i in range(self.rows + 1):
            pygame.draw.line(self.screen, GRID_LINE,
                             (self.board_x, self.board_y + i * CELL_SIZE),
                             (self.board_x + self.board_w, self.board_y + i * CELL_SIZE))

    def draw_arrows(self):
        now = time.time()
        bouncing_set = {(b['row'], b['col']) for b in self.bouncing}
        # 提示高亮（2 秒后消失）
        if self.hint_pos and now - self.hint_start > 2.5:
            self.hint_pos = None
        # 静态箭头
        for row in range(self.rows):
            for col in range(self.cols):
                d = self.grid[row][col]
                if d is None:
                    continue
                if (row, col) in bouncing_set:
                    continue
                cx = self.board_x + col * CELL_SIZE + CELL_SIZE // 2
                cy = self.board_y + row * CELL_SIZE + CELL_SIZE // 2
                # 提示高亮框（闪烁）
                if self.hint_pos == (row, col):
                    pulse = 3 + int(2 * math.sin(now * 8))
                    cell_rect = pygame.Rect(
                        self.board_x + col * CELL_SIZE + 3,
                        self.board_y + row * CELL_SIZE + 3,
                        CELL_SIZE - 6, CELL_SIZE - 6)
                    pygame.draw.rect(self.screen, GOLD, cell_rect, pulse, border_radius=6)
                self.draw_arrow(cx, cy, d)
        # 飞出棋盘的箭头
        for f in self.flying:
            progress = (now - f['start']) / 0.4
            cx = self.board_x + f['col'] * CELL_SIZE + CELL_SIZE // 2 + f['dc'] * progress * 200
            cy = self.board_y + f['row'] * CELL_SIZE + CELL_SIZE // 2 + f['dr'] * progress * 200
            self.draw_arrow(cx, cy, f['dir'])
        # 被挡住后弹出又弹回的箭头（红色）
        for b in self.bouncing:
            progress = (now - b['start']) / 0.5
            if progress < 0.6:
                offset = (progress / 0.6) * 30
            else:
                offset = (1 - (progress - 0.6) / 0.4) * 30
            cx = self.board_x + b['col'] * CELL_SIZE + CELL_SIZE // 2 + b['dc'] * offset
            cy = self.board_y + b['row'] * CELL_SIZE + CELL_SIZE // 2 + b['dr'] * offset
            self.draw_arrow(cx, cy, b['dir'], BLOCKED_COLOR)

    def draw_overlay(self, title, sub, sub_color=WHITE):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        self.screen.blit(s, (0, 0))
        t = self.font_big.render(title, True, WHITE)
        self.screen.blit(t, t.get_rect(center=(SCREEN_W // 2, 280)))
        st = self.font_mid.render(sub, True, sub_color)
        self.screen.blit(st, st.get_rect(center=(SCREEN_W // 2, 360)))

    def draw(self):
        self.screen.fill(BG_COLOR)
        if self.state == 'MENU':
            self.draw_menu()
        elif self.state == 'LEVEL_SELECT':
            self.draw_level_select()
        else:
            self.draw_hud()
            self.draw_board()
            self.draw_arrows()
            if self.state == 'LEVEL_COMPLETE':
                self.draw_overlay("本关通过！", f"获得 {self.stars} 颗星  剩余时间 {int(self.time_left)}s")
                hint = self.font_small.render("点击任意处进入下一关", True, (220, 220, 220))
                self.screen.blit(hint, hint.get_rect(center=(SCREEN_W // 2, 440)))
                self.draw_stars(SCREEN_W // 2, 320, self.stars)
            elif self.state == 'WIN':
                self.draw_overlay("恭喜全部通关！", "点击任意处返回主菜单")
            elif self.state == 'LOSE':
                self.draw_overlay("挑战失败", f"原因：{self.lose_reason}，点击任意处重玩",
                                  sub_color=(255, 200, 200))
        pygame.display.flip()

    # ---------- 主循环 ----------
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.state == 'MENU':
                        if self.menu_start_btn.collidepoint(event.pos):
                            self.state = 'LEVEL_SELECT'
                        elif self.menu_select_btn.collidepoint(event.pos):
                            self.state = 'LEVEL_SELECT'
                    elif self.state == 'LEVEL_SELECT':
                        if self.back_btn.collidepoint(event.pos):
                            self.state = 'MENU'
                        else:
                            for rect, idx, locked in self.level_buttons:
                                if rect.collidepoint(event.pos) and not locked:
                                    self.level_idx = idx
                                    self.load_level(idx)
                                    self.state = 'PLAY'
                                    break
                    elif self.state == 'PLAY':
                        self.handle_click(event.pos)
                    elif self.state == 'LEVEL_COMPLETE':
                        self.level_idx += 1
                        self.load_level(self.level_idx)
                        self.state = 'PLAY'
                    elif self.state == 'LOSE':
                        self.load_level(self.level_idx)
                        self.state = 'PLAY'
                    elif self.state == 'WIN':
                        self.state = 'MENU'
            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == '__main__':
    ArrowGame().run()
