import time
import threading
import os
import sys

class ChessClock:
    def __init__(self, player1_time, player2_time, time_unit='minutes', bonus=0):
        self.player1_time = self.convert_to_seconds(player1_time, time_unit)
        self.player2_time = self.convert_to_seconds(player2_time, time_unit)
        self.time_unit = time_unit
        self.bonus = bonus
        self.current_player = 1
        self.running = False
        self.lock = threading.Lock()
        self.move_count = 0
        self.max_moves = None  # Used for aggregate mode
        self.aggregate_second_period = None  # Used for aggregate mode
        self.switch_event = threading.Event()
        self.input_thread = None
        self.clock_thread = None

    def convert_to_seconds(self, val, unit):
        if unit == 'minutes':
            return val * 60
        elif unit == 'seconds':
            return val
        else:
            raise ValueError('Invalid time unit')

    def format_time(self, secs):
        mins = int(secs // 60)
        secs = int(secs % 60)
        return f"{mins:02d}:{secs:02d}"

    def clear_console(self):
        # Cross-platform clear screen
        os.system('cls' if os.name == 'nt' else 'clear')

    def display(self):
        self.clear_console()
        print(f"Player 1 Clock: {self.format_time(self.player1_time)}")
        print(f"Player 2 Clock: {self.format_time(self.player2_time)}")
        print(f"Current Player: {self.current_player}")
        print("Press Enter after your move to switch clocks.")

    def switch_player(self):
        with self.lock:
            if self.current_player == 1:
                self.current_player = 2
                if self.bonus:
                    self.player1_time += self.bonus
            else:
                self.current_player = 1
                if self.bonus:
                    self.player2_time += self.bonus

    def run_clock(self):
        while self.running:
            with self.lock:
                self.display()
                if self.current_player == 1:
                    self.player1_time -= 1
                    if self.player1_time <= 0:
                        self.display()
                        print("\nPlayer 1's time has run out. Player 2 wins!")
                        self.running = False
                        self.switch_event.set()
                        break
                else:
                    self.player2_time -= 1
                    if self.player2_time <= 0:
                        self.display()
                        print("\nPlayer 2's time has run out. Player 1 wins!")
                        self.running = False
                        self.switch_event.set()
                        break
            # Wait 1 second, but check if switch_event is set to break immediately
            if self.switch_event.wait(1):
                self.switch_event.clear()

    def input_listener(self):
        while self.running:
            input()  # Wait for user to press Enter after move
            self.move_count += 1
            # Aggregate time: after max_moves, add second period time
            if self.max_moves and self.move_count == self.max_moves:
                print("\nFirst period complete. Adding remaining time to second period for each player.")
                with self.lock:
                    self.player1_time += self.aggregate_second_period
                    self.player2_time += self.aggregate_second_period
                self.max_moves = None  # Don't trigger again
                time.sleep(2)
            self.switch_player()
            self.switch_event.set()

    def start(self):
        self.running = True
        self.switch_event.clear()
        self.clock_thread = threading.Thread(target=self.run_clock)
        self.input_thread = threading.Thread(target=self.input_listener)
        self.clock_thread.start()
        self.input_thread.start()
        self.clock_thread.join()
        self.input_thread.join()

def get_int_input(prompt, min_val, max_val):
    while True:
        try:
            val = int(input(prompt))
            if min_val <= val <= max_val:
                return val
            else:
                print(f"Enter a value between {min_val} and {max_val}.")
        except ValueError:
            print("Invalid number. Try again.")

def main():
    print("Select clock type:")
    print("1. Simple time (per move)")
    print("2. Game time (total per player)")
    print("3. Aggregate time (two periods)")
    print("4. Game/aggregate time with bonus")

    clock_type = get_int_input("Enter choice (1-4): ", 1, 4)

    if clock_type == 1:
        n = get_int_input("Enter time per move (5-60 minutes): ", 5, 60)
        clock = ChessClock(n, n, 'minutes')
    elif clock_type == 2:
        n = get_int_input("Enter total game time per player (5-120 minutes): ", 5, 120)
        clock = ChessClock(n, n, 'minutes')
    elif clock_type == 3:
        m = get_int_input("Enter number of moves in first period (1-60): ", 1, 60)
        n = get_int_input("Enter minutes for first period (1-120): ", 1, 120)
        sec_period = get_int_input("Enter minutes for second period (1-120): ", 1, 120)
        clock = ChessClock(n, n, 'minutes')
        clock.max_moves = m
        clock.aggregate_second_period = sec_period * 60
    elif clock_type == 4:
        bonus = get_int_input("Enter bonus time per move (10-30 seconds): ", 10, 30)
        print("Apply bonus to (1) Game time or (2) Aggregate time?")
        sub_choice = get_int_input("Enter choice (1-2): ", 1, 2)
        if sub_choice == 1:
            n = get_int_input("Enter total game time per player (5-120 minutes): ", 5, 120)
            clock = ChessClock(n, n, 'minutes', bonus)
        else:
            m = get_int_input("Enter number of moves in first period (1-60): ", 1, 60)
            n = get_int_input("Enter minutes for first period (1-120): ", 1, 120)
            sec_period = get_int_input("Enter minutes for second period (1-120): ", 1, 120)
            clock = ChessClock(n, n, 'minutes', bonus)
            clock.max_moves = m
            clock.aggregate_second_period = sec_period * 60

    print("\nStarting clock. Player 1 moves first. Press Enter to switch clocks after each move.")
    time.sleep(2)
    clock.start()

if __name__ == "__main__":
    main()