import os
import random
import tkinter as tk
from tkinter import messagebox

# 공용 지갑 파일 경로 찾기 (gamble 폴더의 상위 폴더(루트)에 있는 wallet.txt 접근)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLET_FILE = os.path.join(ROOT_DIR, "wallet.txt")

class BlackjackGame(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Blackjack")
        self.geometry("600x580")
        self.configure(padx=20, pady=10)

        self.deck = []
        self.dealer_hand = []
        self.player_hand = []
        self.current_bet = 0

        self.setup_ui()
        self.start_new_game()

    # ------------------ 공용 지갑 연동 ------------------
    def get_money(self):
        if not os.path.exists(WALLET_FILE):
            return 0
        with open(WALLET_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except:
                return 0

    def set_money(self, amount):
        with open(WALLET_FILE, "w") as f:
            f.write(str(amount))

    def setup_ui(self):
        # 배팅 UI 영역
        self.bet_frame = tk.Frame(self, bd=2, relief="ridge", padx=10, pady=10, bg="#f9f9f9")
        self.bet_frame.pack(fill="x", pady=(0, 10))
        
        self.wallet_label = tk.Label(self.bet_frame, text="소지금 : 불러오는 중...", font=("Malgun Gothic", 12, "bold"), bg="#f9f9f9")
        self.wallet_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        tk.Label(self.bet_frame, text="배팅 금액:", font=("Malgun Gothic", 12), bg="#f9f9f9").grid(row=1, column=0)
        self.bet_entry = tk.Entry(self.bet_frame, font=("Malgun Gothic", 12), width=10)
        self.bet_entry.insert(0, "100") # 기본값
        self.bet_entry.grid(row=1, column=1, padx=10)

        self.bet_btn = tk.Button(self.bet_frame, text="배팅 & 게임시작", font=("Malgun Gothic", 10, "bold"), bg="gold", command=self.place_bet)
        self.bet_btn.grid(row=1, column=2)

        # 게임 영역
        tk.Label(self, text="딜러의 카드", font=("Malgun Gothic", 14, "bold")).pack(pady=(10, 5))
        self.dealer_label = tk.Label(self, text="", font=("Malgun Gothic", 16), fg="red")
        self.dealer_label.pack(pady=(0, 15))

        tk.Label(self, text="플레이어의 카드", font=("Malgun Gothic", 14, "bold")).pack(pady=(0, 5))
        self.player_label = tk.Label(self, text="", font=("Malgun Gothic", 16), fg="blue")
        self.player_label.pack(pady=(0, 15))

        self.status_label = tk.Label(self, text="배팅을 먼저 진행해주세요.", font=("Malgun Gothic", 14))
        self.status_label.pack(pady=10)

        # 액션 버튼
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        self.hit_btn = tk.Button(btn_frame, text="히트 (받기)", font=("Malgun Gothic", 12), width=12, bg="lightgreen", command=self.hit)
        self.hit_btn.grid(row=0, column=0, padx=10)
        self.stand_btn = tk.Button(btn_frame, text="스탠드 (멈춤)", font=("Malgun Gothic", 12), width=12, bg="lightcoral", command=self.stand)
        self.stand_btn.grid(row=0, column=1, padx=10)

        # 하단 컨트롤 (다시 시작 버튼 삭제됨)
        control_frame = tk.Frame(self)
        control_frame.pack(pady=(10, 0))
        self.exit_btn = tk.Button(control_frame, text="게임 종료", font=("Malgun Gothic", 12), width=15, bg="#f0f0f0", command=self.destroy)
        self.exit_btn.pack(pady=5)

    # ------------------ 배팅 및 게임 흐름 ------------------
    def start_new_game(self):
        """최초 실행 시 1회 호출되어 초기 상태 세팅"""
        # 액션 버튼 잠금, 배팅창 활성화
        self.hit_btn.config(state="disabled")
        self.stand_btn.config(state="disabled")
        
        self.bet_entry.config(state="normal")
        self.bet_btn.config(state="normal")

        self.status_label.config(text="금액을 입력하고 배팅 버튼을 누르세요.", fg="black")
        self.update_wallet_ui()

    def update_wallet_ui(self):
        money = self.get_money()
        self.wallet_label.config(text=f"소지금 : {money}원")

    def place_bet(self):
        """배팅 진행 검증 및 게임(카드 분배) 시작"""
        try:
            bet_amount = int(self.bet_entry.get())
        except ValueError:
            messagebox.showwarning("입력 오류", "숫자만 입력해주세요.")
            return

        current_money = self.get_money()

        if bet_amount < 100:
            messagebox.showwarning("배팅 오류", "최소 배팅 금액은 100원입니다.")
            return
        if bet_amount > current_money:
            messagebox.showwarning("잔액 부족", f"소지금이 부족합니다.\n(현재 소지금: {current_money}원)")
            return

        # 배팅금 차감
        self.set_money(current_money - bet_amount)
        self.current_bet = bet_amount
        self.update_wallet_ui()

        # 배팅창 비활성화 & 액션 활성화
        self.bet_entry.config(state="disabled")
        self.bet_btn.config(state="disabled")
        self.hit_btn.config(state="normal")
        self.stand_btn.config(state="normal")
        
        self.status_label.config(text=f"{bet_amount}원 배팅 완료.\n카드를 받을지 멈출지 선택하세요.", fg="black")
        self.deal_cards()

    def deal_cards(self):
        """실제 카드 분배"""
        suits = ["♠", "♥", "♦", "♣"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        self.deck = [f"{suit}{rank}" for suit in suits for rank in ranks]
        random.shuffle(self.deck)

        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.player_hand = [self.deck.pop(), self.deck.pop()]

        self.update_ui(dealer_hidden=True)

    def calculate_score(self, hand):
        score, aces = 0, 0
        for card in hand:
            rank = card[1:]
            if rank in ["J", "Q", "K"]: score += 10
            elif rank == "A": 
                score += 11
                aces += 1
            else: score += int(rank)
        while score > 21 and aces > 0:
            score -= 10
            aces -= 1
        return score

    def update_ui(self, dealer_hidden=False):
        p_score = self.calculate_score(self.player_hand)
        self.player_label.config(text=f"{' / '.join(self.player_hand)}\n(점수: {p_score})")

        if dealer_hidden:
            self.dealer_label.config(text=f"❓ / {self.dealer_hand[1]}\n(점수: ?)")
        else:
            d_score = self.calculate_score(self.dealer_hand)
            self.dealer_label.config(text=f"{' / '.join(self.dealer_hand)}\n(점수: {d_score})")

    def hit(self):
        self.player_hand.append(self.deck.pop())
        self.update_ui(dealer_hidden=True)
        if self.calculate_score(self.player_hand) > 21:
            self.status_label.config(text="버스트 배팅금을 잃었습니다.", fg="red")
            self.game_over()

    def stand(self):
        self.hit_btn.config(state="disabled")
        self.stand_btn.config(state="disabled")
        self.update_ui(dealer_hidden=False)
        self.status_label.config(text="딜러가 카드를 뽑고 있습니다...")
        self.after(800, self.dealer_turn_step)

    def dealer_turn_step(self):
        if self.calculate_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())
            self.update_ui(dealer_hidden=False)
            self.after(800, self.dealer_turn_step)
        else:
            self.check_winner()

    def check_winner(self):
        p_score = self.calculate_score(self.player_hand)
        d_score = self.calculate_score(self.dealer_hand)
        
        current_money = self.get_money()

        if d_score > 21 or p_score > d_score:
            winnings = self.current_bet * 2 # 원금 포함 2배 획득
            self.set_money(current_money + winnings)
            self.status_label.config(text=f"승리 {winnings}원을 획득했습니다!", fg="blue")
        elif p_score < d_score:
            self.status_label.config(text="패배 배팅금을 잃었습니다.", fg="red")
            # 이미 배팅 시점에 차감했으므로 돈을 뺄 필요 없음
        else:
            self.set_money(current_money + self.current_bet) # 원금 반환
            self.status_label.config(text="무승부 배팅금을 돌려받았습니다.", fg="black")

        self.game_over()

    def game_over(self):
        """게임 종료 시 액션 버튼을 끄고 배팅을 다시 활성화"""
        self.hit_btn.config(state="disabled")
        self.stand_btn.config(state="disabled")

        self.bet_entry.config(state="normal")
        self.bet_btn.config(state="normal")
        
        self.update_wallet_ui()

if __name__ == "__main__":
    app = BlackjackGame()
    app.mainloop()