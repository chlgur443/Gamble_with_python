import os
import random
import tkinter as tk
from tkinter import messagebox
from collections import Counter

# 공용 지갑 파일 경로 찾기
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLET_FILE = os.path.join(ROOT_DIR, "wallet.txt")

# 족보에 따른 배당률 (원금 포함 배수)
PAYOUT_TABLE = {
    "로열 플러시": 250,
    "스트레이트 플러시": 50,
    "포카드": 25,
    "풀하우스": 9,
    "플러시": 6,
    "스트레이트": 4,
    "트리플": 3,
    "투페어": 2,
    "잭스 오어 배터 (J-A 원페어)": 1,
    "로우 페어 (10 이하 원페어)": 0.5,
    "하이카드": 0
}

def evaluate_hand(hand):
    """5장의 카드를 분석하여 족보 이름과 승리 배수를 반환합니다."""
    rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    suits = [card[0] for card in hand]
    ranks = [rank_map[card[1:]] for card in hand]
    
    is_flush = len(set(suits)) == 1
    sorted_ranks = sorted(ranks, reverse=True)
    
    is_straight = False
    if sorted_ranks == [14, 5, 4, 3, 2]:
        is_straight = True
    elif len(set(sorted_ranks)) == 5 and sorted_ranks[0] - sorted_ranks[-1] == 4:
        is_straight = True

    counts = Counter(sorted_ranks)
    sorted_counts = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    freqs = [x[1] for x in sorted_counts]
    
    if is_straight and is_flush:
        if 14 in ranks and 13 in ranks: return "로열 플러시"
        return "스트레이트 플러시"
    if freqs == [4, 1]: return "포카드"
    if freqs == [3, 2]: return "풀하우스"
    if is_flush: return "플러시"
    if is_straight: return "스트레이트"
    if freqs == [3, 1, 1]: return "트리플"
    if freqs == [2, 2, 1]: return "투페어"
    if freqs == [2, 1, 1, 1]:
        pair_val = sorted_counts[0][0]
        # J(11) 이상이면 잭스 오어 배터, 10 이하면 로우 페어
        if pair_val >= 11: 
            return "잭스 오어 배터 (J-A 원페어)"
        else:
            return "로우 페어 (10 이하 원페어)"
        
    return "하이카드"


class PokerGame(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Poker")
        self.geometry("600x640") 
        self.configure(padx=20, pady=10)

        self.deck = []
        self.player_hand = []
        self.current_bet = 0

        self.setup_ui()
        self.start_new_game()

    def get_money(self):
        if not os.path.exists(WALLET_FILE):
            return 0
        with open(WALLET_FILE, "r") as f:
            try: return int(f.read().strip())
            except: return 0

    def set_money(self, amount):
        with open(WALLET_FILE, "w") as f:
            f.write(str(amount))

    def setup_ui(self):
        # 배팅 UI 프레임
        self.bet_frame = tk.Frame(self, bd=2, relief="ridge", padx=10, pady=10, bg="#f9f9f9")
        self.bet_frame.pack(fill="x", pady=(0, 10))
        
        self.wallet_label = tk.Label(self.bet_frame, text="소지금: 불러오는 중...", font=("Malgun Gothic", 12, "bold"), bg="#f9f9f9")
        self.wallet_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        tk.Label(self.bet_frame, text="배팅 금액:", font=("Malgun Gothic", 12), bg="#f9f9f9").grid(row=1, column=0)
        self.bet_entry = tk.Entry(self.bet_frame, font=("Malgun Gothic", 12), width=10)
        self.bet_entry.insert(0, "100")
        self.bet_entry.grid(row=1, column=1, padx=10)

        self.bet_btn = tk.Button(self.bet_frame, text="배팅 & 게임시작", font=("Malgun Gothic", 10, "bold"), bg="gold", command=self.place_bet)
        self.bet_btn.grid(row=1, column=2)

        # 배당표 안내
        payout_text = "배당률 안내 : 로열 플러시(x250), 스트레이트 플러시(x50), 포카드(x25), 풀하우스(x9)\n플러시(x6), 스트레이트(x4), 트리플(x3), 투페어(x2), J-A 원페어(x1) , 로우페어(x0.5), 하이카드(x0)"
        tk.Label(self, text=payout_text, font=("Malgun Gothic", 10), fg="gray").pack(pady=(0, 20))

        # 플레이어 게임 영역
        tk.Label(self, text="내 카드", font=("Malgun Gothic", 14, "bold")).pack(pady=(0, 5))
        self.player_label = tk.Label(self, text="", font=("Malgun Gothic", 18), fg="blue")
        self.player_label.pack(pady=(0, 10))

        # 카드 교환 체크박스
        self.check_frame = tk.Frame(self)
        self.check_frame.pack(pady=(0, 10))
        
        self.check_vars = [tk.BooleanVar() for _ in range(5)]
        self.check_btns = []
        for i in range(5):
            cb = tk.Checkbutton(self.check_frame, text=f"{i+1}번 교환", variable=self.check_vars[i], font=("Malgun Gothic", 11))
            cb.grid(row=0, column=i, padx=5)
            self.check_btns.append(cb)

        self.status_label = tk.Label(self, text="배팅을 먼저 진행해주세요.", font=("Malgun Gothic", 14))
        self.status_label.pack(pady=10)

        # 액션 버튼
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        self.draw_btn = tk.Button(btn_frame, text="선택 교환", font=("Malgun Gothic", 12), width=12, bg="lightgreen", command=self.draw_cards)
        self.draw_btn.grid(row=0, column=0, padx=10)
        self.stand_btn = tk.Button(btn_frame, text="그대로 (Stand)", font=("Malgun Gothic", 12), width=15, bg="lightcoral", command=self.stand_cards)
        self.stand_btn.grid(row=0, column=1, padx=10)

        # 종료 버튼
        control_frame = tk.Frame(self)
        control_frame.pack(pady=(10, 0))
        self.exit_btn = tk.Button(control_frame, text="게임 종료", font=("Malgun Gothic", 11), width=15, bg="#f0f0f0", command=self.destroy)
        self.exit_btn.pack(pady=5)

    def start_new_game(self):
        self.draw_btn.config(state="disabled")
        self.stand_btn.config(state="disabled")
        for cb in self.check_btns:
            cb.config(state="disabled")
            
        self.bet_entry.config(state="normal")
        self.bet_btn.config(state="normal")
        
        self.status_label.config(text="금액을 입력하고 배팅 버튼을 누르세요.", fg="black")
        self.update_wallet_ui()

    def update_wallet_ui(self):
        money = self.get_money()
        self.wallet_label.config(text=f"소지금 : {money}원")

    def place_bet(self):
        try: bet_amount = int(self.bet_entry.get())
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

        self.set_money(current_money - bet_amount)
        self.current_bet = bet_amount
        self.update_wallet_ui()

        self.bet_entry.config(state="disabled")
        self.bet_btn.config(state="disabled")
        self.draw_btn.config(state="normal")
        self.stand_btn.config(state="normal")
        for i, cb in enumerate(self.check_btns):
            self.check_vars[i].set(False) 
            cb.config(state="normal")
        
        self.status_label.config(text=f"{bet_amount}원 배팅 완료!\n바꿀 카드를 체크한 뒤 [선택 교환]을 누르세요.", fg="black")
        self.deal_cards()

    def deal_cards(self):
        suits = ["♠", "♥", "♦", "♣"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        self.deck = [f"{suit}{rank}" for suit in suits for rank in ranks]
        random.shuffle(self.deck)

        self.player_hand = [self.deck.pop() for _ in range(5)]
        self.update_ui()

    def update_ui(self):
        hand_name = evaluate_hand(self.player_hand)
        self.player_label.config(text=f"{' / '.join(self.player_hand)}\n(현재 족보: {hand_name})")

    # ------------------ 버튼 동작 로직 ------------------
    def draw_cards(self):
        """선택한 카드를 교환하기 전, 교환할 카드들의 인덱스를 수집하고 순차 교환 시작"""
        # UI 버튼 및 체크박스 잠금 (도중 클릭 방지)
        self.draw_btn.config(state="disabled")
        self.stand_btn.config(state="disabled")
        for cb in self.check_btns:
            cb.config(state="disabled")

        # 교환(체크)하기로 한 카드의 인덱스들만 리스트에 담음
        self.cards_to_replace = [i for i, var in enumerate(self.check_vars) if var.get()]
        
        # 교환할 카드가 없다면 바로 결과 판정으로 넘어감
        if not self.cards_to_replace:
            self.check_result()
            return

        # 하단 텍스트가 너무 빨리 바뀌는 문제를 해결하기 위해 상태 메시지를 깔끔하게 통일
        self.status_label.config(text="🃏 결과를 기다리는 중...", fg="gray")
        
        # 교환 연출 시작
        self.replace_step()

    def replace_step(self):
        """0.6초 간격으로 카드를 한 장씩 새 카드로 교체하는 애니메이션 효과"""
        if self.cards_to_replace:
            # 리스트 맨 앞의 카드 인덱스를 꺼냄
            target_idx = self.cards_to_replace.pop(0)
            
            # 새 카드로 교체
            self.player_hand[target_idx] = self.deck.pop()
            
            self.player_label.config(text=f"{' / '.join(self.player_hand)}\n(카드 교체 중...)")
            
            # 0.6초(600ms) 뒤에 다음 카드를 교체하도록 예약
            self.after(600, self.replace_step)
        else:
            # 모든 교환이 끝났으면 결과 판정
            self.check_result()

    def stand_cards(self):
        """카드 교환 없이 바로 결과 판정"""
        self.draw_btn.config(state="disabled")
        self.stand_btn.config(state="disabled")
        for cb in self.check_btns:
            cb.config(state="disabled")
            
        self.check_result()

    def check_result(self):
        """최종 족보에 따른 상금 지급 및 게임 종료"""
        hand_name = evaluate_hand(self.player_hand)
        multiplier = PAYOUT_TABLE[hand_name]
        
        current_money = self.get_money()
        winnings = int(self.current_bet * multiplier) 
        
        # 최종 카드와 족보 UI 업데이트
        self.update_ui()
        
        if winnings > 0:
            self.set_money(current_money + winnings)
            if multiplier == 1:
                self.status_label.config(text=f"{hand_name} 배팅금 {winnings}원을 돌려받았습니다.", fg="blue")
            elif multiplier == 0.5:
                self.status_label.config(text=f"{hand_name} 배팅금의 절반({winnings}원)을 돌려받았습니다.", fg="black")
            else:
                self.status_label.config(text=f"{hand_name} \n배팅금의 {multiplier}배인 {winnings}원을 획득했습니다", fg="blue")
        else:
            self.status_label.config(text=f"{hand_name} 배팅금을 모두 잃었습니다.", fg="red")
            
        self.game_over()

    def game_over(self):
        self.bet_entry.config(state="normal")
        self.bet_btn.config(state="normal")
        self.update_wallet_ui()

if __name__ == "__main__":
    app = PokerGame()
    app.mainloop()