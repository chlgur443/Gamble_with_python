import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

GAMBLE_DIR = "gamble"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
WALLET_FILE = os.path.join(ROOT_DIR, "wallet.txt") # [요구사항 2] 공용 돈 저장 파일

GAME_LIST = [
    {"name": "Blackjack", "script": "blackjack.py"},
    {"name": "Poker", "script": "video_poker.py"},
]

def run_script(script_path):
    if not os.path.exists(script_path):
        messagebox.showerror("실행 오류", f"'{script_path}' 파일을 찾을 수 없습니다.")
        return
    try:
        subprocess.Popen([sys.executable, script_path])
    except Exception as e:
        messagebox.showerror("알 수 없는 오류", str(e))

class CasinoMainMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Casino Games Launcher")
        self.geometry("400x600")
        self.configure(padx=30, pady=20)

        # 타이틀
        tk.Label(self, text="Casino Lobby", font=("Malgun Gothic", 24, "bold")).pack(pady=(0, 15))

        # 소지금 UI 및 1000원 추가 버튼
        wallet_frame = tk.Frame(self, bd=2, relief="groove", padx=10, pady=10)
        wallet_frame.pack(fill="x", pady=(0, 20))

        self.wallet_label = tk.Label(wallet_frame, text="로딩 중...", font=("Malgun Gothic", 14, "bold"))
        self.wallet_label.pack(side="left")

        charge_btn = tk.Button(wallet_frame, text="+1000원", font=("Malgun Gothic", 10, "bold"), bg="gold", command=self.add_money)
        charge_btn.pack(side="right")

        # 게임 버튼 프레임
        self.games_frame = tk.Frame(self)
        self.games_frame.pack(fill="both", expand=True)

        for game in GAME_LIST:
            full_path = os.path.join(GAMBLE_DIR, game["script"])
            btn = tk.Button(self.games_frame, text=game["name"], font=("Malgun Gothic", 14), height=2, cursor="hand2",
                            command=lambda path=full_path: run_script(path))
            btn.pack(fill="x", pady=8)

        separator = tk.Frame(self, height=2, bd=1, relief="sunken")
        separator.pack(fill="x", pady=(20, 20))

        bottom_frame = tk.Frame(self)
        bottom_frame.pack(fill="x", side="bottom")

        tk.Button(bottom_frame, text="옵션", font=("Malgun Gothic", 11), height=2,
                  command=lambda: run_script(os.path.join(ROOT_DIR, "options.py"))).pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(bottom_frame, text="종료", font=("Malgun Gothic", 11), height=2,
                  command=self.quit).pack(side="right", fill="x", expand=True, padx=(5, 0))

        # 실시간 잔액 감지 시작
        self.update_wallet_loop()

    # ---------------- 돈 관리 로직 ----------------
    def get_money(self):
        """지갑 파일에서 돈을 읽어옴. 파일이 없으면 생성후 1000원 지급"""
        if not os.path.exists(WALLET_FILE):
            with open(WALLET_FILE, "w") as f:
                f.write("1000")
            return 1000
        with open(WALLET_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except:
                return 0

    def add_money(self):
        current = self.get_money()
        with open(WALLET_FILE, "w") as f:
            f.write(str(current + 1000))
        self.update_wallet_loop() # 즉시 반영

    def update_wallet_loop(self):
        """0.5초마다 백그라운드에서 wallet.txt 파일을 읽어와 잔액 업데이트"""
        money = self.get_money()
        self.wallet_label.config(text=f"소지금 : {money}원")
        self.after(500, self.update_wallet_loop)

if __name__ == "__main__":
    app = CasinoMainMenu()
    app.mainloop()