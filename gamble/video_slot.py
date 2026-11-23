import os
import random
import tkinter as tk
from tkinter import messagebox

# 공용 지갑 파일 경로 (루트 폴더의 wallet.txt 연동)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLET_FILE = os.path.join(ROOT_DIR, "wallet.txt")

# 슬롯 규격 및 1회 비용 (4행 5열, 1회 100원)
ROWS = 4
COLS = 5
SPIN_COST = 100

# 숨김 천장 카운트 발동 기준 (누적 무당첨 횟수)
PITY_THRESHOLD = 100
ADJACENT_REROLL_TRIES = 3

# 열별 멈춤 틱 수 및 프레임 간격 
COLUMN_STOP_TICKS = [8, 15, 22, 29, 36]
SPIN_INTERVAL_MS = 85
HIGHLIGHT_STEP_MS = 650

# 직선 길이별 기본 배율 (3연속 / 4연속 / 5연속)
LINE_BASE_MULTS = {
    3: 0.7,
    4: 1.5,
    5: 2.5,
}

# 심볼 설정
# - mult: 심볼 배율
# - weight: 등장 가중치
# - dampen_prob: 상·좌측 인접 동일 심볼 재추첨 확률
SYMBOLS = [
    {"id": "SEVEN", "label": "🎰", "mult": 10.0, "weight": 10, "dampen_prob": 0.30, "fg": "#d32f2f"},
    {"id": "DIAMOND", "label": "💎", "mult": 5.0, "weight": 15, "dampen_prob": 0.25, "fg": "#1976d2"},
    {"id": "STAR", "label": "⭐", "mult": 2.8, "weight": 20, "dampen_prob": 0.20, "fg": "#f57c00"},
    {"id": "BELL", "label": "🔔", "mult": 1.6, "weight": 25, "dampen_prob": 0.15, "fg": "#7b1fa2"},
    {"id": "CHERRY", "label": "🍒", "mult": 1.1, "weight": 30, "dampen_prob": 0.10, "fg": "#c2185b"},
    {"id": "LEMON", "label": "🍋", "mult": 0.7, "weight": 35, "dampen_prob": 0.05, "fg": "#388e3c"},
]

SYMBOL_MAP = {s["id"]: s for s in SYMBOLS}
SYMBOL_IDS = [s["id"] for s in SYMBOLS]
SYMBOL_WEIGHTS = [s["weight"] for s in SYMBOLS]

# 모양 패턴 정의
LARGE_SHAPE_PATTERNS_4X5 = [
    {
        "name": "최대 O자 (가장자리 외곽)",
        "mult": 5.5,
        "coords": [
            (0, 1), (0, 2), (0, 3),
            (3, 1), (3, 2), (3, 3),
            (1, 0), (2, 0),
            (1, 4), (2, 4),
        ],
    },
    {
        "name": "최대 X자 (4x4 대각선 교차)",
        "mult": 4.2,
        "coords": [
            (0, 0), (1, 1), (2, 2), (3, 3),
            (0, 3), (1, 2), (2, 1), (3, 0),
        ],
    },
    {
        "name": "최대 V자 (4x5 확장 V)",
        "mult": 2.4,
        "coords": [
            (0, 0), (1, 1), (2, 2), (3, 2), (2, 3), (1, 4),
        ],
    },
]

FULL_BOARD_MULT = 25.0


def pick_symbol(exclude_id=None):
    """가중치 기반 랜덤 심볼 선택 (특정 심볼 제외 옵션 지원)"""
    if exclude_id and exclude_id in SYMBOL_MAP:
        candidates = [s for s in SYMBOLS if s["id"] != exclude_id]
        ids = [s["id"] for s in candidates]
        weights = [s["weight"] for s in candidates]
        return random.choices(ids, weights=weights, k=1)[0]
    return random.choices(SYMBOL_IDS, weights=SYMBOL_WEIGHTS, k=1)[0]


def generate_full_board(symbol_id=None):
    """4x5(20칸) 전체를 확률 기반 선택 심볼로 채운 보드 생성"""
    chosen = symbol_id if symbol_id in SYMBOL_MAP else pick_symbol()
    return [[chosen for _ in range(COLS)] for _ in range(ROWS)]


def pick_dampened_symbol(grid, r, c):
    """
    심볼별 인접 재추첨 확률(최대 40%)에 따라 상·좌측 동일 심볼 배치를 조절합니다.
    """
    sym = pick_symbol()
    neighbors = []
    if r > 0:
        neighbors.append(grid[r - 1][c])
    if c > 0:
        neighbors.append(grid[r][c - 1])

    for _ in range(ADJACENT_REROLL_TRIES):
        sym_dampen_prob = min(0.40, SYMBOL_MAP[sym]["dampen_prob"])
        if sym in neighbors and random.random() < sym_dampen_prob:
            sym = pick_symbol(exclude_id=sym)
        else:
            break
    return sym


def generate_board():
    """
    4x5 슬롯 보드 생성 (인접 동일 심볼 재추첨 적용, 당첨 후 강제 억제 없음)
    """
    board = [["" for _ in range(COLS)] for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            board[r][c] = pick_dampened_symbol(board, r, c)
    return board


def find_line_wins(grid):
    """
    가로, 세로, 대각선 방향에서 연속된 동일 심볼(3개 이상)을 찾되,
    한 직선 위에서는 가장 길게 연속된 구간만 채택합니다.
    """
    directions = [
        (0, 1, "가로"),
        (1, 0, "세로"),
        (1, 1, "대각선(우하향)"),
        (1, -1, "대각선(좌하향)"),
    ]
    found_lines = []

    for r in range(ROWS):
        for c in range(COLS):
            sym = grid[r][c]
            for dr, dc, dir_name in directions:
                prev_r, prev_c = r - dr, c - dc
                if 0 <= prev_r < ROWS and 0 <= prev_c < COLS and grid[prev_r][prev_c] == sym:
                    continue

                run_coords = [(r, c)]
                nr, nc = r + dr, c + dc
                while 0 <= nr < ROWS and 0 <= nc < COLS and grid[nr][nc] == sym:
                    run_coords.append((nr, nc))
                    nr += dr
                    nc += dc

                if len(run_coords) >= 3:
                    length = len(run_coords)
                    sym_icon = SYMBOL_MAP[sym]["label"]
                    found_lines.append({
                        "desc": f"{dir_name} {length}연속 ({sym_icon})",
                        "length": length,
                        "symbol": sym,
                        "coords": run_coords,
                    })

    return found_lines


def find_large_shape_wins(grid):
    """
    4x5 판에서 V자, X자, O자의 최대 크기 패턴이 동일 심볼로 완성되었는지 판정합니다.
    """
    found_shapes = []

    for pattern in LARGE_SHAPE_PATTERNS_4X5:
        coords = pattern["coords"]
        first_sym = grid[coords[0][0]][coords[0][1]]
        if all(grid[r][c] == first_sym for r, c in coords):
            sym_icon = SYMBOL_MAP[first_sym]["label"]
            found_shapes.append({
                "desc": f"{pattern['name']} ({sym_icon})",
                "shape_mult": pattern["mult"],
                "symbol": first_sym,
                "coords": coords,
            })

    return found_shapes


def find_full_board_win(grid):
    """
    4x5(20칸) 전체가 단일 심볼로 가득 찼는지 확인합니다.
    """
    first_sym = grid[0][0]
    if all(grid[r][c] == first_sym for r in range(ROWS) for c in range(COLS)):
        all_coords = [(r, c) for r in range(ROWS) for c in range(COLS)]
        sym_icon = SYMBOL_MAP[first_sym]["label"]
        return {
            "desc": f"올 심볼 20칸 완성 ({sym_icon})",
            "board_mult": FULL_BOARD_MULT,
            "symbol": first_sym,
            "coords": all_coords,
        }
    return None


def calculate_spin_payout(grid):
    """
    총 당첨금과 당첨 내역 리스트를 계산합니다. (중복 당첨 허용)
    """
    full_win = find_full_board_win(grid)
    if full_win:
        sym_mult = SYMBOL_MAP[full_win["symbol"]]["mult"]
        payout = int(SPIN_COST * full_win["board_mult"] * sym_mult)
        return payout, [(f"{full_win['desc']} -> {payout}원", full_win["coords"])]

    line_wins = find_line_wins(grid)
    shape_wins = find_large_shape_wins(grid)

    total_payout = 0
    details = []

    for lw in line_wins:
        length = lw["length"]
        base_line_mult = LINE_BASE_MULTS.get(length, 0.7 * (1.5 ** (length - 3)))
        sym_mult = SYMBOL_MAP[lw["symbol"]]["mult"]
        payout = int(SPIN_COST * base_line_mult * sym_mult)
        if payout > 0:
            total_payout += payout
            details.append((f"{lw['desc']} -> {payout}원", lw["coords"]))

    for sw in shape_wins:
        sym_mult = SYMBOL_MAP[sw["symbol"]]["mult"]
        payout = int(SPIN_COST * sw["shape_mult"] * sym_mult)
        if payout > 0:
            total_payout += payout
            details.append((f"{sw['desc']} -> {payout}원", sw["coords"]))

    return total_payout, details


class VideoSlotGame(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("비디오 슬롯 (Video Slot - 4x5)")
        self.geometry("760x790")
        self.configure(padx=20, pady=15, bg="#f4f4f4")

        self.is_spinning = False
        self.is_highlighting = False
        self.spin_tick = 0
        self.col_stopped = [False] * COLS
        # 비공개 누적 무당첨 카운터 (메모리 전용, 100회 도달 발동 또는 창 종료 시 초기화)
        self._total_misses = 0
        self.target_grid = generate_board()
        self.display_grid = [row[:] for row in self.target_grid]
        self.cell_labels = []

        self.setup_ui()
        self.grid = self.target_grid
        self.render_grid(self.grid)
        self.update_wallet_ui()

    # ------------------ 공용 지갑 연동 ------------------
    def get_money(self):
        if not os.path.exists(WALLET_FILE):
            with open(WALLET_FILE, "w") as f:
                f.write("1000")
            return 1000
        with open(WALLET_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return 0

    def set_money(self, amount):
        with open(WALLET_FILE, "w") as f:
            f.write(str(max(0, amount)))

    def is_busy(self):
        return self.is_spinning or self.is_highlighting

    def update_wallet_ui(self):
        money = self.get_money()
        self.wallet_label.config(text=f"소지금 : {money}원  |  1회 비용: {SPIN_COST}원")
        if not self.is_busy():
            if money < SPIN_COST:
                self.spin_btn.config(state="disabled", text="잔액 부족 (100원 필요)")
            else:
                self.spin_btn.config(state="normal", text=f"스핀 ({SPIN_COST}원)")

    # ------------------ UI 구성 ------------------
    def setup_ui(self):
        top_frame = tk.Frame(self, bg="#ffffff", bd=2, relief="ridge", padx=15, pady=10)
        top_frame.pack(fill="x", pady=(0, 10))

        tk.Label(top_frame, text="비디오 슬롯머신 (4x5)", font=("Malgun Gothic", 18, "bold"), bg="#ffffff").pack()
        self.wallet_label = tk.Label(top_frame, text="소지금 : -원", font=("Malgun Gothic", 13, "bold"), fg="#1b5e20", bg="#ffffff")
        self.wallet_label.pack(pady=(4, 0))

        info_text = (
            "심볼 배율: 🎰(x10) / 💎(x5) / ⭐(x2.8) / 🔔(x1.6) / 🍒(x1.1) / 🍋(x0.7)\n"
            "직선 기본 배율: 3연속(x0.7) / 4연속(x1.5) / 5연속(x2.5)  [최장 길이만 계산]\n"
            "최대 모양 배율: 최대 V자(x2.4) / 최대 X자(x4.2) / 최대 O자(x5.5) / 올 심볼 20칸(x25)  |  중복 당첨 가능"
        )
        tk.Label(self, text=info_text, font=("Malgun Gothic", 9), fg="#444444", bg="#eaeaea", pady=6).pack(fill="x", pady=(0, 12))

        board_frame = tk.Frame(self, bg="#263238", padx=12, pady=12, bd=3, relief="sunken")
        board_frame.pack()

        for r in range(ROWS):
            row_widgets = []
            for c in range(COLS):
                lbl = tk.Label(
                    board_frame,
                    text="",
                    font=("Segoe UI Emoji", 22),
                    width=4,
                    height=1,
                    bg="#ffffff",
                    relief="raised",
                    bd=2,
                    padx=6,
                    pady=6,
                )
                lbl.grid(row=r, column=c, padx=5, pady=5)
                row_widgets.append(lbl)
            self.cell_labels.append(row_widgets)

        self.status_label = tk.Label(self, text="스핀 버튼을 눌러 게임을 시작하세요.", font=("Malgun Gothic", 13, "bold"), bg="#f4f4f4", fg="#222222")
        self.status_label.pack(pady=(12, 4))

        self.detail_box = tk.Text(self, height=5, width=72, font=("Malgun Gothic", 10), state="disabled", bg="#ffffff")
        self.detail_box.pack(pady=(0, 12))

        btn_frame = tk.Frame(self, bg="#f4f4f4")
        btn_frame.pack()

        self.spin_btn = tk.Button(
            btn_frame,
            text=f"스핀 ({SPIN_COST}원)",
            font=("Malgun Gothic", 13, "bold"),
            width=18,
            height=2,
            bg="#ffd54f",
            cursor="hand2",
            command=self.start_spin,
        )
        self.spin_btn.grid(row=0, column=0, padx=10)

        self.exit_btn = tk.Button(
            btn_frame,
            text="게임 종료",
            font=("Malgun Gothic", 12, "bold"),
            width=14,
            height=2,
            bg="#e0e0e0",
            cursor="hand2",
            command=self.destroy,
        )
        self.exit_btn.grid(row=0, column=1, padx=10)

    def set_detail_text(self, lines):
        self.detail_box.config(state="normal")
        self.detail_box.delete("1.0", tk.END)
        for line in lines:
            self.detail_box.insert(tk.END, line + "\n")
        self.detail_box.config(state="disabled")

    def render_grid(self, grid, highlight_coords=None):
        highlight_set = set(highlight_coords) if highlight_coords else set()
        for r in range(ROWS):
            for c in range(COLS):
                sym_id = grid[r][c]
                sym_info = SYMBOL_MAP[sym_id]
                bg_color = "#fff59d" if (r, c) in highlight_set else "#ffffff"
                self.cell_labels[r][c].config(
                    text=sym_info["label"],
                    fg=sym_info["fg"],
                    bg=bg_color,
                )

    # ------------------ 스핀 및 열 단위 동기 멈춤 ------------------
    def start_spin(self):
        if self.is_busy():
            return

        current_money = self.get_money()
        if current_money < SPIN_COST:
            messagebox.showwarning("잔액 부족", f"1회 진행에 필요한 {SPIN_COST}원이 부족합니다.\n메인 화면에서 소지금을 충전해주세요.")
            self.update_wallet_ui()
            return

        self.set_money(current_money - SPIN_COST)
        self.is_spinning = True
        self.is_highlighting = False
        self.spin_tick = 0
        self.col_stopped = [False] * COLS

        # 누적 무당첨 100회 도달 시 20칸 올 심볼 보드 발동 후 카운트 초기화
        if self._total_misses >= PITY_THRESHOLD:
            self.target_grid = generate_full_board()
            self._total_misses = 0
        else:
            self.target_grid = generate_board()

        # 외부 화면용 display_grid는 회전 애니메이션 전용으로 분리
        self.display_grid = [[pick_symbol() for _ in range(COLS)] for _ in range(ROWS)]
        self.spin_btn.config(state="disabled", text="회전 중...")
        self.status_label.config(text="왼쪽 열부터 차례대로 릴이 멈춥니다...", fg="#333333")
        self.set_detail_text(["릴 회전 진행 중..."])
        self.update_wallet_ui()

        self.animate_spin()

    def animate_spin(self):
        self.spin_tick += 1
        stopped_count = 0

        for c in range(COLS):
            # 이미 멈춘 열은 건드리지 않고 확정 심볼 유지
            if self.col_stopped[c]:
                stopped_count += 1
                continue

            # 해당 열의 멈춤 틱에 도달하면 열 전체를 동시에 고정
            if self.spin_tick >= COLUMN_STOP_TICKS[c]:
                self.col_stopped[c] = True
                stopped_count += 1
                for r in range(ROWS):
                    self.display_grid[r][c] = self.target_grid[r][c]
            else:
                # 아직 회전 중인 열은 외부 애니메이션용 심볼만 갱신
                for r in range(ROWS):
                    self.display_grid[r][c] = pick_symbol()

        self.render_grid(self.display_grid)

        if stopped_count < COLS:
            self.status_label.config(text="릴 멈춤 진행 중...")
            self.after(SPIN_INTERVAL_MS, self.animate_spin)
        else:
            self.grid = [row[:] for row in self.target_grid]
            self.finish_spin()

    # ------------------ 결과 판정 및 순차 하이라이트 ------------------
    def finish_spin(self):
        self.is_spinning = False
        total_payout, details = calculate_spin_payout(self.grid)

        # 당첨이 나와도 누적 카운트는 유지하고, 무당첨일 때만 1씩 누적
        if total_payout == 0:
            self._total_misses += 1

        if total_payout > 0:
            new_money = self.get_money() + total_payout
            self.set_money(new_money)
            self.is_highlighting = True
            self.spin_btn.config(state="disabled", text="당첨 확인 중...")
            self.set_detail_text([line for line, _ in details])
            self.highlight_step(details, idx=0, total_payout=total_payout)
        else:
            self.render_grid(self.grid)
            self.status_label.config(text="당첨 조합이 없습니다.", fg="#c62828")
            self.set_detail_text(["당첨된 모양 조합이 없습니다."])
            self.update_wallet_ui()

    def highlight_step(self, details, idx, total_payout):
        """
        당첨된 조합을 하나씩 순서대로 하이라이트한 뒤,
        마지막 단계에서 당첨된 모든 조합을 한꺼번에 하이라이트
        """
        if idx < len(details):
            desc, coords = details[idx]
            self.render_grid(self.grid, highlight_coords=coords)
            self.status_label.config(
                text=f"당첨 확인 ({idx + 1}/{len(details)}): {desc}",
                fg="#1565c0",
            )
            self.after(HIGHLIGHT_STEP_MS, lambda: self.highlight_step(details, idx + 1, total_payout))
        else:
            all_coords = []
            for _, coords in details:
                all_coords.extend(coords)
            self.render_grid(self.grid, highlight_coords=all_coords)
            net_diff = total_payout - SPIN_COST
            diff_text = f"+{net_diff}원" if net_diff >= 0 else f"{net_diff}원"
            self.status_label.config(
                text=f"지급 {total_payout}원 ({diff_text})",
                fg="#1565c0" if net_diff >= 0 else "#ef6c00",
            )
            self.is_highlighting = False
            self.update_wallet_ui()


if __name__ == "__main__":
    app = VideoSlotGame()
    app.mainloop()