# -*- coding: utf-8 -*-
"""
"一箭又一箭" 小游戏
课程：软件工程 第二次个人作业
运行：python one_arrow_game.py  （需先 pip install pygame）

玩法：
  - 棋盘中的箭头朝上/下/左/右。
  - 点击某个箭头，若它沿指向方向到棋盘边界之间没有其他箭头，箭头飞出棋盘；
    否则该箭头被挡住，不能消除，并且晃动变红一次，失误次数 -1。
  - 失误次数耗尽则本关失败，可重新开始；清空本关全部箭头则进入下一关。
"""

import sys
import math
import time
import pygame

# ---------- 常量 ----------
CELL_SIZE = 100          # 每格像素
BOARD_TOP = 130          # 棋盘顶部留出 HUD 空间
SCREEN_W, SCREEN_H = 600, 720
FPS = 60
MAX_MISSES = 5           # 每关允许的失误次数

# 颜色
BG_COLOR        = (245, 240, 230)
BOARD_COLOR     = (222, 212, 190)
GRID_LINE       = (185, 175, 155)
ARROW_COLOR     = (60, 95, 170)
BLOCKED_COLOR   = (200, 80, 80)
TEXT_COLOR      = (55, 55, 55)
BTN_COLOR       = (90, 130, 200)
BTN_HOVER       = (115, 155, 225)
WHITE           = (255, 255, 255)

# 方向 -> (行偏移, 列偏移)
DIRS = {
    'U': (-1, 0),
    'D': (1, 0),
    'L': (0, -1),
    'R': (0, 1),
}

# ---------- 关卡设计 ----------
# None 表示空格；'U'/'D'/'L'/'R' 表示箭头方向
# 每个关卡均已手工验证可通关。
LEVELS = [
    # 第 1 关（教学关，3x3）
    [
        ['R', None, 'D'],
        [None, None, None],
        ['U', None, None],
    ],
    # 第 2 关（4x4）
    [
        ['R', None, 'U', None],
        [None, None, None, None],
        ['D', None, None, 'L'],
        [None, 'R', None, None],
    ],
    # 第 3 关（4x5）
    [
        [None, 'R', None, 'D'],
        ['U', None, None, None],
        [None, None, 'L', None],
        ['D', None, 'U', None],
        [None, None, None, 'R'],
    ],
]


class ArrowGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("一箭又一箭")
        self.clock = pygame.time.Clock()
        # 直接加载字体文件，绕过部分 pygame/Python 版本下 SysFont 枚举系统字体的 bug
        import os
        _font_candidates = [
            r"C:\Windows\Fonts\msyh.ttc",   # 微软雅黑
            r"C:\Windows\Fonts\msyhbd.ttc",
            r"C:\Windows\Fonts\simhei.ttf",  # 黑体
        ]
        _font_path = next((p for p in _font_candidates if os.path.exists(p)), None)
        def _mkfont(size):
            return pygame.font.Font(_font_path, size) if _font_path else pygame.font.Font(None, size)
        self.font_big   = _mkfont(48)
        self.font_mid   = _mkfont(28)
        self.font_small = _mkfont(20)

        self.state = 'MENU'      # MENU / PLAY / LEVEL_COMPLETE / WIN / LOSE
        self.level_idx = 0
        self.restart_btn = pygame.Rect(470, 20, 110, 40)
        self.menu_btn = pygame.Rect(220, 370, 160, 60)
        self.load_level(0)

    # ---------- 关卡与状态 ----------
    def load_level(self, idx):
        """把第 idx 关载入，重置棋盘、失误次数、动画。"""
        self.grid = [row[:] for row in LEVELS[idx]]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.misses = MAX_MISSES
        self.flying = []     # 正在飞出的箭头动画
        self.shaking = {}    # (row, col) -> 开始时间
        self.board_w = self.cols * CELL_SIZE
        self.board_h = self.rows * CELL_SIZE
        self.board_x = (SCREEN_W - self.board_w) // 2
        self.board_y = BOARD_TOP

    def remaining_arrows(self):
        return sum(1 for row in self.grid for c in row if c is not None)

    # ---------- 核心：路径检测 ----------
    def is_blocked(self, row, col):
        """判断 (row, col) 处的箭头沿其指向方向到边界之间是否有其他箭头。"""
        d = self.grid[row][col]
        dr, dc = DIRS[d]
        r, c = row + dr, col + dc
        while 0 <= r < self.rows and 0 <= c < self.cols:
            if self.grid[r][c] is not None:
                return True   # 前方有箭头挡住
            r += dr
            c += dc
        return False          # 一路畅通，可飞出

    # ---------- 事件处理 ----------
    def handle_click(self, pos):
        mx, my = pos
        # 重新开始按钮
        if self.restart_btn.collidepoint(mx, my):
            self.load_level(self.level_idx)
            return
        # 棋盘坐标换算
        col = (mx - self.board_x) // CELL_SIZE
        row = (my - self.board_y) // CELL_SIZE
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        if self.grid[row][col] is None:
            return
        if (row, col) in self.shaking:      # 动画期间忽略
            return

        if self.is_blocked(row, col):
            # 被挡住：晃动 + 失误
            self.shaking[(row, col)] = time.time()
            self.misses -= 1
            if self.misses <= 0:
                self.state = 'LOSE'
        else:
            # 可飞出：从棋盘移除，加入飞行动画
            d = self.grid[row][col]
            dr, dc = DIRS[d]
            self.flying.append({
                'row': row, 'col': col, 'dir': d,
                'dr': dr, 'dc': dc, 'start': time.time(),
            })
            self.grid[row][col] = None

    # ---------- 帧更新 ----------
    def update(self):
        now = time.time()
        # 清理结束的飞行动画（0.4 秒）
        self.flying = [f for f in self.flying if now - f['start'] < 0.4]
        # 清理结束的晃动动画
        for key in list(self.shaking.keys()):
            if now - self.shaking[key] > 0.4:
                del self.shaking[key]
        # 胜利判定：棋盘空且无飞行中箭头
        if self.state == 'PLAY' and self.remaining_arrows() == 0 and not self.flying:
            if self.level_idx + 1 < len(LEVELS):
                self.state = 'LEVEL_COMPLETE'
            else:
                self.state = 'WIN'

    # ---------- 绘制 ----------
    def draw_arrow(self, x, y, direction, color=ARROW_COLOR, size=44):
        """以 (x, y) 为中心画一个三角形箭头。"""
        h = size // 2
        if direction == 'U':
            pts = [(x, y - h), (x - h, y + h), (x + h, y + h)]
        elif direction == 'D':
            pts = [(x, y + h), (x - h, y - h), (x + h, y - h)]
        elif direction == 'L':
            pts = [(x - h, y), (x + h, y - h), (x + h, y + h)]
        else:  # R
            pts = [(x + h, y), (x - h, y - h), (x - h, y + h)]
        pygame.draw.polygon(self.screen, color, pts)
        pygame.draw.polygon(self.screen, WHITE, pts, 2)

    def draw_menu(self):
        title = self.font_big.render("一箭又一箭", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 230)))
        tip = self.font_small.render("点击箭头，按正确顺序让它们全部飞出棋盘", True, TEXT_COLOR)
        self.screen.blit(tip, tip.get_rect(center=(SCREEN_W // 2, 300)))
        mouse = pygame.mouse.get_pos()
        color = BTN_HOVER if self.menu_btn.collidepoint(mouse) else BTN_COLOR
        pygame.draw.rect(self.screen, color, self.menu_btn, border_radius=10)
        txt = self.font_mid.render("开始游戏", True, WHITE)
        self.screen.blit(txt, txt.get_rect(center=self.menu_btn.center))

    def draw_hud(self):
        level_txt = self.font_mid.render(f"第 {self.level_idx + 1} 关 / 共 {len(LEVELS)} 关", True, TEXT_COLOR)
        self.screen.blit(level_txt, (20, 20))
        arrows_txt = self.font_small.render(f"剩余箭头：{self.remaining_arrows()}", True, TEXT_COLOR)
        self.screen.blit(arrows_txt, (20, 60))
        miss_color = BLOCKED_COLOR if self.misses <= 2 else TEXT_COLOR
        miss_txt = self.font_small.render(f"剩余失误：{self.misses}", True, miss_color)
        self.screen.blit(miss_txt, (20, 90))
        # 重新开始按钮
        mouse = pygame.mouse.get_pos()
        color = BTN_HOVER if self.restart_btn.collidepoint(mouse) else BTN_COLOR
        pygame.draw.rect(self.screen, color, self.restart_btn, border_radius=8)
        rb = self.font_small.render("重新开始", True, WHITE)
        self.screen.blit(rb, rb.get_rect(center=self.restart_btn.center))

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
        # 静态箭头（含晃动动画）
        for row in range(self.rows):
            for col in range(self.cols):
                d = self.grid[row][col]
                if d is None:
                    continue
                cx = self.board_x + col * CELL_SIZE + CELL_SIZE // 2
                cy = self.board_y + row * CELL_SIZE + CELL_SIZE // 2
                color = ARROW_COLOR
                if (row, col) in self.shaking:
                    elapsed = now - self.shaking[(row, col)]
                    color = BLOCKED_COLOR
                    cx += int(6 * math.sin(elapsed * 35))  # 左右晃动
                self.draw_arrow(cx, cy, d, color)
        # 正在飞出的箭头
        for f in self.flying:
            progress = (now - f['start']) / 0.4
            cx = self.board_x + f['col'] * CELL_SIZE + CELL_SIZE // 2 + f['dc'] * progress * 220
            cy = self.board_y + f['row'] * CELL_SIZE + CELL_SIZE // 2 + f['dr'] * progress * 220
            self.draw_arrow(cx, cy, f['dir'], ARROW_COLOR)

    def draw_overlay(self, title, sub, sub_color=WHITE):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        self.screen.blit(s, (0, 0))
        t = self.font_big.render(title, True, WHITE)
        self.screen.blit(t, t.get_rect(center=(SCREEN_W // 2, 310)))
        st = self.font_mid.render(sub, True, sub_color)
        self.screen.blit(st, st.get_rect(center=(SCREEN_W // 2, 390)))

    def draw(self):
        self.screen.fill(BG_COLOR)
        if self.state == 'MENU':
            self.draw_menu()
        else:
            self.draw_hud()
            self.draw_board()
            self.draw_arrows()
            if self.state == 'LEVEL_COMPLETE':
                self.draw_overlay("本关通过！", "点击任意处进入下一关")
            elif self.state == 'WIN':
                self.draw_overlay("恭喜全部通关！", "点击任意处返回主菜单")
            elif self.state == 'LOSE':
                self.draw_overlay("挑战失败", "点击任意处重新开始本关", sub_color=(255, 200, 200))
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
                        if self.menu_btn.collidepoint(event.pos):
                            self.state = 'PLAY'
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
                        self.level_idx = 0
                        self.load_level(0)
                        self.state = 'MENU'
            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == '__main__':
    ArrowGame().run()
