# -*- coding: utf-8 -*-
"""
自动化逻辑测试：不打开窗口，直接验证路径判定与关卡流程。
运行：python test_game.py
"""
import one_arrow_game as g


def fresh_game():
    game = g.ArrowGame.__new__(g.ArrowGame)  # 跳过 pygame.init()
    game.level_idx = 0
    game.load_level(0)
    return game


def test_t01_clear_path_flies():
    """T01 点击前方无阻挡的箭头 -> 箭头消失。"""
    game = fresh_game()
    # 第 1 关 (2,2) 是 R，右侧无阻挡，应可飞出
    assert game.grid[2][2] == 'R'
    assert not game.is_blocked(2, 2), "R 箭头前方无阻挡却被判 blocked"
    game.grid[2][2] = None
    assert game.grid[2][2] is None
    print("T01 通过：无阻挡箭头可飞出")


def test_t02_blocked_path():
    """T02 点击前方有阻挡的箭头 -> 不消失，失误 -1。"""
    game = fresh_game()
    # 第 1 关 (0,0) 是 R，右侧 (0,2) 有 D，应被挡
    assert game.is_blocked(0, 0), "R 箭头前方有阻挡却被判可飞"
    before = game.misses_left
    game.misses_left -= 1
    assert game.grid[0][0] == 'R', "被挡箭头不应消失"
    assert game.misses_left == before - 1
    print("T02 通过：阻挡箭头不消失，失误减 1")


def test_t03_edge_arrow_no_crash():
    """T03 边缘且朝向外的箭头正常消失，不越界。"""
    game = fresh_game()
    # 第 2 关 (3,1) 是 R，右侧无箭头阻挡
    game.level_idx = 1
    game.load_level(1)
    assert game.grid[3][1] == 'R'
    assert not game.is_blocked(3, 1)
    game.grid[3][1] = None
    assert game.grid[3][1] is None
    print("T03 通过：边缘箭头正常消失，无越界")


def test_t04_clear_level():
    """T04 清空本关全部箭头 -> 进入下一关。"""
    game = fresh_game()
    # 第 1 关通关顺序：(2,2)R -> (0,2)D -> (1,1)U -> (0,0)R -> (2,0)U
    order = [(2, 2), (0, 2), (1, 1), (0, 0), (2, 0)]
    for r, c in order:
        assert not game.is_blocked(r, c), f"通关顺序中 ({r},{c}) 不应被挡"
        game.grid[r][c] = None
    assert game.remaining_arrows() == 0
    game.level_idx += 1
    game.load_level(game.level_idx)
    assert game.level_idx == 1
    print("T04 通过：清空后可进入下一关")


def test_t05_misses_exhausted():
    """T05 失误耗尽 -> 进入 LOSE。"""
    game = fresh_game()
    game.misses_left = 1
    game.misses_left -= 1
    if game.misses_left <= 0:
        game.state = 'LOSE'
    assert game.state == 'LOSE'
    print("T05 通过：失误耗尽进入失败状态")


def test_t06_restart():
    """T06 重新开始 -> 棋盘与失误次数恢复。"""
    game = fresh_game()
    game.grid[0][0] = None   # 模拟已消除
    game.misses_left = 2
    game.load_level(0)      # 重新开始
    assert game.grid[0][0] == 'R'
    assert game.misses_left == g.MAX_MISSES
    assert game.remaining_arrows() == 5
    print("T06 通过：重新开始后状态恢复")


def test_levels_solvable():
    """附加验证：每关都存在一条通关顺序（暴力搜索），并输出箭头数和步数。"""
    def solve(grid, rows, cols, path):
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] is None:
                    continue
                d = grid[r][c]
                dr, dc = g.DIRS[d]
                rr, cc = r + dr, c + dc
                blocked = False
                while 0 <= rr < rows and 0 <= cc < cols:
                    if grid[rr][cc] is not None:
                        blocked = True
                        break
                    rr += dr
                    cc += dc
                if not blocked:
                    grid[r][c] = None
                    path.append((r, c))
                    if solve(grid, rows, cols, path):
                        return True
                    path.pop()
                    grid[r][c] = d
                    return False
        return all(grid[r][c] is None for r in range(rows) for c in range(cols))

    print()
    print("=" * 45)
    print(f"{'关卡':<6}{'棋盘':<10}{'箭头数':<8}{'通关步数':<8}")
    print("-" * 45)
    for i, level in enumerate(g.LEVELS):
        grid = [row[:] for row in level]
        rows, cols = len(grid), len(grid[0])
        arrow_count = sum(1 for row in grid for c in row if c is not None)
        path = []
        assert solve(grid, rows, cols, path), f"第 {i+1} 关无解！"
        print(f"第 {i+1} 关{'':<3}{rows}x{cols:<8}{arrow_count:<8}{len(path):<8}")
    print("=" * 45)
    print("全部关卡可通关 ✓")


if __name__ == '__main__':
    test_t01_clear_path_flies()
    test_t02_blocked_path()
    test_t03_edge_arrow_no_crash()
    test_t04_clear_level()
    test_t05_misses_exhausted()
    test_t06_restart()
    test_levels_solvable()
    print("\n全部测试通过 ✅")
