import os
import random
import tkinter as tk
from tkinter import messagebox, simpledialog
from collections import Counter
from itertools import combinations

# 공용 지갑 연동
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLET_FILE = os.path.join(ROOT_DIR, "wallet.txt")

# 레이즈 제한 횟수 설정 (라운드당)
MAX_RAISES_PER_ROUND = 3

# --- 1. 족보 판정 로직 ---
def evaluate_hand(hand):
    rank_map = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
    suits = [card[0] for card in hand]
    ranks = [rank_map[card[1:]] for card in hand]
    
    is_flush = len(set(suits)) == 1
    sorted_ranks = sorted(ranks, reverse=True)
    is_straight = False
    
    if sorted_ranks == [14, 5, 4, 3, 2]:
        is_straight = True
        sorted_ranks = [5, 4, 3, 2, 1]
    elif len(set(sorted_ranks)) == 5 and sorted_ranks[0] - sorted_ranks[-1] == 4:
        is_straight = True

    counts = Counter(sorted_ranks)
    sorted_counts = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    freqs = [x[1] for x in sorted_counts]
    vals = [x[0] for x in sorted_counts]

    if is_straight and is_flush: return (8, vals, "스트레이트 플러시")
    if freqs == [4, 1]: return (7, vals, "포카드")
    if freqs == [3, 2]: return (6, vals, "풀하우스")
    if is_flush: return (5, vals, "플러시")
    if is_straight: return (4, vals, "스트레이트")
    if freqs == [3, 1, 1]: return (3, vals, "트리플")
    if freqs == [2, 2, 1]: return (2, vals, "투페어")
    if freqs == [2, 1, 1, 1]: return (1, vals, "원페어")
    return (0, vals, "하이카드")

def get_best_hand(hole_cards, community_cards):
    available_cards = hole_cards + community_cards
    if len(available_cards) < 5: return (0, [], "진행중")
    best_score = (-1, [], "")
    for combo in combinations(available_cards, 5):
        score = evaluate_hand(list(combo))
        if score > best_score: best_score = score
    return best_score

# --- 2. 텍사스 홀덤 메인 클래스 ---
class TexasHoldem(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.withdraw() 
        init_capital = simpledialog.askinteger(
            "AI 초기 자본금 설정",
            "각 AI에게 지급할 초기 자본금을 입력하세요 (최소 1000):",
            initialvalue=5000,
            minvalue=1000
        )
        self.ai_initial_capital = init_capital if init_capital else 5000
        self.deiconify() 
        
        self.title("텍사스 홀덤 (Texas Hold'em - 5 Players)")
        self.geometry("950x850")
        self.configure(padx=10, pady=10)

        self.deck = []
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.stage = 0 
        self.dealer_idx = -1 
        self.raises_in_round = 0 

        self.players = []
        for i in range(5):
            name = "당신 (User)" if i == 0 else f"AI {i}"
            money = self.get_money() if i == 0 else self.ai_initial_capital 
            self.players.append({"id": i, "name": name, "hand": [], "active": True, "all_in": False, "bet_in_round": 0, "total_bet": 0, "money": money})
        
        self.current_turn = 0
        self.acted_players = set()

        self.setup_ui()
        self.start_new_game()

    def get_money(self):
        if not os.path.exists(WALLET_FILE): return 0
        with open(WALLET_FILE, "r") as f:
            try: return int(f.read().strip())
            except: return 0

    def set_money(self, amount):
        with open(WALLET_FILE, "w") as f: f.write(str(amount))
        self.wallet_label.config(text=f"소지금 : {amount}원")
        self.players[0]["money"] = amount 

    def setup_ui(self):
        self.ai_frame = tk.Frame(self, bg="#dcdcdc", pady=15)
        self.ai_frame.pack(fill="x")
        
        self.inner_ai_frame = tk.Frame(self.ai_frame, bg="#dcdcdc")
        self.inner_ai_frame.pack(anchor="center")
        
        self.ai_labels = {}
        for i in range(1, 5):
            lbl = tk.Label(self.inner_ai_frame, text=f"AI {i}\n준비중", font=("Malgun Gothic", 12, "bold"), width=16, height=5, bg="white", relief="ridge")
            lbl.pack(side="left", padx=10)
            self.ai_labels[i] = lbl

        self.center_frame = tk.Frame(self, pady=20)
        self.center_frame.pack()
        
        self.pot_label = tk.Label(self.center_frame, text="총 판돈(Pot): 0원", font=("Malgun Gothic", 20, "bold"), fg="gold", bg="darkgreen", padx=30, pady=10)
        self.pot_label.pack(pady=10)
        
        self.comm_label = tk.Label(self.center_frame, text="[ ? ] [ ? ] [ ? ] [ ? ] [ ? ]", font=("Malgun Gothic", 28, "bold"), fg="white", bg="darkgreen", padx=30, pady=15)
        self.comm_label.pack()

        self.log_text = tk.Text(self, height=7, width=75, font=("Malgun Gothic", 10), state="disabled")
        self.log_text.pack(pady=15)

        self.player_frame = tk.Frame(self, bd=2, relief="groove", pady=10)
        self.player_frame.pack(fill="x")
        self.wallet_label = tk.Label(self.player_frame, text="소지금: 불러오는 중...", font=("Malgun Gothic", 14, "bold"))
        self.wallet_label.pack()
        
        self.my_bet_label = tk.Label(self.player_frame, text="총 베팅 : 0원", font=("Malgun Gothic", 12, "bold"), fg="#b22222")
        self.my_bet_label.pack(pady=(5, 0))
        
        self.my_hand_label = tk.Label(self.player_frame, text="내 카드 : ", font=("Malgun Gothic", 18, "bold"), fg="blue")
        self.my_hand_label.pack(pady=10)

        self.btn_frame = tk.Frame(self)
        self.btn_frame.pack(pady=10)
        
        self.fold_btn = tk.Button(self.btn_frame, text="폴드", font=("Malgun Gothic", 13, "bold"), width=10, bg="gray", command=lambda: self.player_action("fold"))
        self.fold_btn.grid(row=0, column=0, padx=5)
        
        self.call_btn = tk.Button(self.btn_frame, text="체크 / 콜", font=("Malgun Gothic", 13, "bold"), width=18, bg="lightgreen", command=lambda: self.player_action("call"))
        self.call_btn.grid(row=0, column=1, padx=5)
        
        tk.Label(self.btn_frame, text="+ 추가금액 : ", font=("Malgun Gothic", 13, "bold")).grid(row=0, column=2, padx=(15, 0))
        self.raise_entry = tk.Entry(self.btn_frame, font=("Malgun Gothic", 14), width=8)
        self.raise_entry.grid(row=0, column=3, padx=5)
        self.raise_entry.insert(0, "100")
        
        self.raise_btn = tk.Button(self.btn_frame, text="레이즈", font=("Malgun Gothic", 13, "bold"), width=12, bg="lightcoral", command=lambda: self.player_action("raise"))
        self.raise_btn.grid(row=0, column=4, padx=5)

        self.next_game_btn = tk.Button(self, text="다음 판 시작", font=("Malgun Gothic", 13), command=self.start_new_game)
        self.next_game_btn.pack(pady=10)

    def log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def get_next_active_player(self, start_idx):
        idx = (start_idx + 1) % 5
        while self.players[idx]["money"] <= 0:
            idx = (idx + 1) % 5
            if idx == start_idx: break 
        return idx

    # --- 게임 규칙 및 흐름 제어 ---
    def start_new_game(self):
        self.players[0]["money"] = self.get_money()
        if self.players[0]["money"] < 100:
            messagebox.showwarning("잔액 부족", "최소 참가비(BB 100원)가 부족합니다.")
            self.destroy()
            return

        all_ai_bankrupt = all(p["money"] <= 0 for p in self.players[1:])
        if all_ai_bankrupt:
            messagebox.showinfo("알림", "모든 AI가 파산했습니다. 초기 자본금을 지급하여 다시 시작합니다.")
            for p in self.players[1:]:
                p["money"] = self.ai_initial_capital

        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
        
        self.next_game_btn.config(state="disabled")
        self.pot = 0
        self.community_cards = []
        self.stage = 0
        
        for p in self.players:
            p["active"] = p["money"] > 0
            p["all_in"] = False
            p["bet_in_round"] = 0
            p["total_bet"] = 0 

        self.dealer_idx = self.get_next_active_player(self.dealer_idx)

        self.log(f"게임 시작 (딜러 버튼 : {self.players[self.dealer_idx]['name']})")
        
        suits, ranks = ["♠", "♥", "♦", "♣"], ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        self.deck = [f"{s}{r}" for s in suits for r in ranks]
        random.shuffle(self.deck)

        for p in self.players:
            if p["active"]: p["hand"] = [self.deck.pop(), self.deck.pop()]

        self.update_ui()
        self.start_pre_flop()

    def start_pre_flop(self):
        self.stage = 0
        self.current_bet = 100
        self.acted_players = set()
        self.raises_in_round = 0 
        
        sb_idx = self.get_next_active_player(self.dealer_idx)
        bb_idx = self.get_next_active_player(sb_idx)
        utg_idx = self.get_next_active_player(bb_idx)
        
        self.log(f"{self.players[sb_idx]['name']} : 스몰 블라인드 (50원)")
        self.log(f"{self.players[bb_idx]['name']} : 빅 블라인드 (100원)")
        
        self.pay(self.players[sb_idx], 50)
        self.pay(self.players[bb_idx], 100)
        
        self.current_turn = utg_idx
        self.log("\n--- 프리플랍(Pre-flop) 베팅 ---")
        self.turn_loop()

    def start_betting_round(self):
        for p in self.players: p["bet_in_round"] = 0
        self.current_bet = 0
        self.acted_players = set()
        self.raises_in_round = 0 
        
        self.current_turn = self.get_next_active_player(self.dealer_idx)
        
        stage_name = ["", "플랍(Flop)", "턴(Turn)", "리버(River)"][self.stage]
        self.log(f"\n--- {stage_name} 베팅 ---")
        self.turn_loop()

    def turn_loop(self):
        active_players = [p for p in self.players if p["active"]]
        if len(active_players) == 1:
            self.showdown() 
            return

        acting_players = [p for p in active_players if not p["all_in"]]
        
        if len(acting_players) > 0:
            all_matched = all(p["bet_in_round"] == self.current_bet for p in acting_players)
            if all_matched and len(self.acted_players) >= len(acting_players):
                self.next_stage()
                return
        elif len(acting_players) == 0:
            self.next_stage()
            return

        p = None
        while True:
            p = self.players[self.current_turn % 5]
            if p["active"] and not p["all_in"]:
                break
            self.current_turn += 1

        if p["id"] == 0:
            self.enable_buttons(p)
        else:
            self.after(800, lambda: self.ai_action(p))

    # --- 돈 계산 및 올인 처리 ---
    def pay(self, p, amount):
        if amount <= 0: return 0
        actual_pay = min(p["money"], amount)
        
        p["money"] -= actual_pay
        p["bet_in_round"] += actual_pay
        p["total_bet"] += actual_pay 
        self.pot += actual_pay
        
        if p["money"] == 0:
            p["all_in"] = True
            
        if p["id"] == 0: self.set_money(p["money"])
        return actual_pay

    def player_action(self, action):
        p = self.players[0]
        self.fold_btn.config(state="disabled")
        self.call_btn.config(state="disabled")
        self.raise_btn.config(state="disabled")
        self.raise_entry.config(state="disabled")

        raise_amt = 0
        if action == "raise":
            try:
                raise_amt = int(self.raise_entry.get())
                if raise_amt < 100: 
                    messagebox.showwarning("오류", "최소 레이즈 금액은 100원입니다.")
                    self.enable_buttons(p)
                    return
            except ValueError:
                messagebox.showwarning("오류", "숫자만 입력해주세요.")
                self.enable_buttons(p)
                return
                
        self.process_action(p, action, raise_amt)

    def ai_action(self, p):
        to_call = self.current_bet - p["bet_in_round"]
        best_score, _, _ = get_best_hand(p["hand"], self.community_cards)
        
        action = "fold"
        raise_amt = 0
        is_strong = (best_score >= 2) or (self.stage == 0 and ('A' in [c[1:] for c in p["hand"]] or 'K' in [c[1:] for c in p["hand"]]))
        
        rand = random.random()
        if self.current_bet > 1000 and not is_strong:
            action = "fold" if to_call > 0 else "call"
        else:
            if is_strong:
                if rand < 0.5: 
                    action = "raise"
                    raise_amt = 100 if p["money"] > 100 else p["money"]
                else: action = "call"
            else:
                if to_call == 0:
                    action = "raise" if rand < 0.1 else "call" 
                    raise_amt = 100
                elif to_call <= 300:
                    action = "call" if rand < 0.5 else "fold"
                else:
                    action = "fold"
                    
        if action == "raise":
            if self.raises_in_round >= MAX_RAISES_PER_ROUND or p["money"] <= to_call:
                action = "call"
            
        self.process_action(p, action, raise_amt)

    def process_action(self, p, action, raise_amt):
        to_call = self.current_bet - p["bet_in_round"]
        
        if action == "fold":
            p["active"] = False
            self.log(f"{p['name']} 폴드")
        elif action == "call":
            actual = self.pay(p, to_call)
            msg = "콜" if actual > 0 else "체크"
            if p["all_in"]: msg = "올인 (All-in) 콜"
            self.log(f"{p['name']} {msg} (지불: {actual}원)")
        elif action == "raise":
            self.raises_in_round += 1 
            total_req = to_call + raise_amt
            actual = self.pay(p, total_req)
            self.current_bet = p["bet_in_round"] 
            
            msg = "올인 (All-in) 레이즈" if p["all_in"] else "레이즈"
            if to_call > 0:
                self.log(f"{p['name']} {msg} (콜 {to_call}원 + 추가 {raise_amt}원 = 총 {actual}원 지불)")
            else:
                self.log(f"{p['name']} {msg} (추가 {raise_amt}원 = 총 {actual}원 지불)")
            
            self.acted_players.clear()
            
        self.acted_players.add(p["id"])
        self.update_ui()
        self.current_turn += 1
        self.turn_loop()

    def enable_buttons(self, p):
        self.log("당신의 차례입니다.")
        to_call = self.current_bet - p["bet_in_round"]
        
        self.fold_btn.config(state="normal")
        self.call_btn.config(state="normal", text=f"콜 ({to_call}원 지불)" if to_call > 0 else "체크")
        
        if p["money"] > to_call and self.raises_in_round < MAX_RAISES_PER_ROUND:
            self.raise_btn.config(state="normal", text="레이즈")
            self.raise_entry.config(state="normal")
        else:
            limit_msg = "레이즈 (횟수제한)" if self.raises_in_round >= MAX_RAISES_PER_ROUND else "레이즈 (금액부족)"
            self.raise_btn.config(state="disabled", text=limit_msg)
            self.raise_entry.config(state="disabled") 

    # --- 스테이지 전환 (딜레이 연출) ---
    def next_stage(self):
        self.stage += 1
        if self.stage == 1:
            self.log("\n플랍(Flop) 3장 오픈 중...")
            self.after(800, lambda: self.reveal_card(3))
        elif self.stage == 2:
            self.log("\n턴(Turn) 카드 오픈 중...")
            self.after(800, lambda: self.reveal_card(4))
        elif self.stage == 3:
            self.log("\n리버(River) 카드 오픈 중...")
            self.after(800, lambda: self.reveal_card(5))
        elif self.stage == 4:
            self.showdown()

    def reveal_card(self, target_count):
        self.community_cards.append(self.deck.pop())
        self.update_ui()
        if len(self.community_cards) < target_count:
            self.after(600, lambda: self.reveal_card(target_count)) 
        else:
            self.after(600, self.start_betting_round) 

    def update_ui(self):
        self.pot_label.config(text=f"총 판돈(Pot) : {self.pot}원")
        
        # update_ui가 호출될 때마다 유저의 소지금 표시가 즉시 반영되도록 갱신
        self.wallet_label.config(text=f"소지금 : {self.players[0]['money']}원")
        
        comm_str = ""
        for i in range(5):
            comm_str += f"[{self.community_cards[i]}] " if i < len(self.community_cards) else "[ ? ] "
        self.comm_label.config(text=comm_str.strip())
        
        _, _, hand_name = get_best_hand(self.players[0]["hand"], self.community_cards)
        self.my_hand_label.config(text=f"내 카드: {' / '.join(self.players[0]['hand'])} (현재 족보 : {hand_name})")

        self.my_bet_label.config(text=f"총 베팅 : {self.players[0]['total_bet']}원")

        for i in range(1, 5):
            p = self.players[i]
            
            if p["all_in"]: status = "올인"
            elif p["active"]: status = "참가 중"
            elif p["money"] <= 0: status = "파산" 
            else: status = "폴드"
            
            btn_txt = "(SB)" if self.get_next_active_player(self.dealer_idx) == i else "(BB)" if self.get_next_active_player(self.get_next_active_player(self.dealer_idx)) == i else ""
            if self.dealer_idx == i: btn_txt = "(Dealer)"
            
            self.ai_labels[i].config(text=f"{p['name']} {btn_txt}\n{status}\n잔액 : {p['money']}원\n총 베팅 : {p['total_bet']}")
            if not p["active"]: self.ai_labels[i].config(fg="gray")
            else: self.ai_labels[i].config(fg="black")

    def showdown(self):
        self.log("\n--- 결과 발표 (Showdown) ---")
        best_score = (-1, [], "")
        winners = []
        
        for p in self.players:
            if not p["active"]: continue
            score = get_best_hand(p["hand"], self.community_cards)
            if p["id"] != 0:
                self.log(f"{p['name']} 패 공개 : {'/'.join(p['hand'])} ({score[2]})")
            
            if score > best_score:
                best_score = score
                winners = [p]
            elif score == best_score:
                winners.append(p)
                
        prize = self.pot // len(winners)
        win_names = ", ".join([w["name"] for w in winners])
        
        if len(winners) == 1:
            self.log(f"\n단독 승리 : {win_names} ({best_score[2]})\n상금 {prize}원을 획득했습니다")
        else:
            self.log(f"\n무승부 (스플릿) : {win_names} ({best_score[2]})\n각각 상금 {prize}원씩 나눠 가집니다")
            
        for w in winners:
            if w["id"] == 0:
                self.set_money(self.players[0]["money"] + prize)
            else:
                w["money"] += prize
                
        self.update_ui()
        self.next_game_btn.config(state="normal")

if __name__ == "__main__":
    app = TexasHoldem()
    app.mainloop()