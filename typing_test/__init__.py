"""
Copyright (c) 2019 Emil Lynegaard
Distributed under the MIT software license, see the
accompanying LICENSE.md or https://opensource.org/licenses/MIT

Minimal 10fastfingers like typing game using Python3 with ncurses.
Supports vocab files as arguments, as well as adjustable
word length, game time and word frequency (if using sorted vocab).
"""
import argparse
import time
import random
import curses
import os

VOCAB_PATH = os.path.join(os.path.dirname(__file__), "data", "vocab")

# Used for WPM calculation
CHARS_PER_WORD = 5

QUEUE_SIZE = 10

# pylint: disable=too-few-public-methods
class Game:
    """
    Class encapsulating the Game.
    Includes game stats, input management, game display.
    """

    def __init__(self, args):
        self.word_generator = self._word_generator(args)
        self.game_time = args.game_time
        self.next_words = [self._get_word() for _ in range(QUEUE_SIZE)]
        self.correct = []
        self.wrong = []
        self.input = ""

    @staticmethod
    def _word_generator(args):
        words = []
        for line in open(args.vocab):
            word = line.strip()
            if args.min_length <= len(word) <= args.max_length:
                words.append(word)

            if len(words) >= args.words:
                break

        while True:
            yield random.choice(words)

    def calculate_cpm(self, time_played):
        """Calculate CPM given time_played in seconds"""
        if time_played == 0:
            return 0
        correct_chars = len(" ".join(self.correct))
        cpm = 60 / time_played * correct_chars
        return cpm

    def calculate_wpm(self, time_played):
        """Calculate WPM given time_played in seconds"""
        if time_played == 0:
            return 0
        correct_chars = len(" ".join(self.correct))
        wpm = 60 / time_played * correct_chars / CHARS_PER_WORD
        return wpm

    def _get_word(self):
        return next(self.word_generator)

    def _finish_word_event(self):
        target = self.next_words.pop(0)
        if self.input == target:
            self.correct.append(target)
        else:
            self.wrong.append(target)

        self.next_words.append(self._get_word())
        self.input = ""

    def _update_display(self, stdscr, time_left):
        # TODO: display using two lines
        _height, width = stdscr.getmaxyx()

        stdscr.clear()
        wpm = self.calculate_wpm(self.game_time - time_left)
        stdscr.addstr(f"Time left: {time_left}, WPM: {int(round(wpm))}\n")
        target = " ".join(self.next_words)
        for idx, char in enumerate(self.input):
            target_char = target[idx]
            if target_char == char:
                stdscr.addstr(char, curses.color_pair(1))
            else:
                stdscr.addstr(target_char, curses.color_pair(2))

        stdscr.addstr(target[len(self.input) : width])
        stdscr.refresh()

    def _handle_key(self, key):
        char = curses.keyname(key).decode()
        if char == "^R":
            self.restart()
        if key in (curses.KEY_BACKSPACE, 127):
            self.input = self.input[:-1]
        elif chr(key) == " ":
            self._finish_word_event()
        else:
            self.input += chr(key)

    @staticmethod
    def _setup_ncurses(stdscr):
        # hide cursor
        curses.curs_set(0)

        # setup colors for printing text to screen
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)

        # don't wait for user input when calling getch()/getkey()
        stdscr.nodelay(True)

        # allow 100ms sleep on getch()/getkey() avoiding busy-wait
        # early returns when key is pressed, meaning no input delay
        stdscr.timeout(100)

    def _game_loop(self, stdscr):
        self._setup_ncurses(stdscr)
        self._update_display(stdscr, self.game_time)

        started = False
        start = time.time()
        time_left = self.game_time
        while time_left > 0:
            if not started:
                start = time.time()

            key = stdscr.getch()
            new_time_left = int(round(self.game_time - (time.time() - start)))
            if key == -1:
                # only update display when necessary
                if time_left != new_time_left:
                    time_left = new_time_left
                    self._update_display(stdscr, time_left)

                continue

            time_left = new_time_left
            started = True
            self._handle_key(key)
            self._update_display(stdscr, time_left)

    def print_stats(self):
        """Print ACC/CPM/WPM to console"""
        correct = len(self.correct)
        total = correct + len(self.wrong)
        print(f"ACC: {correct/total*100:.2f}%")
        cpm = self.calculate_cpm(self.game_time)
        print(f"CPM: {int(round(cpm))}")
        wpm = self.calculate_wpm(self.game_time)
        print(f"WPM: {int(round(wpm))}")

    def restart(self):
        """
        Reset the Game class, effective starting a new game
        with new words, but based on same configuration.
        """
        self.input = ""
        self.correct = []
        self.wrong = []
        self.next_words = [self._get_word() for _ in range(QUEUE_SIZE)]
        self.play()

    def play(self):
        """Start typing game and print results to terminal"""
        curses.wrapper(self._game_loop)
        self.print_stats()


def main():
    """Parse arguments and start game based thereof"""
    parser = argparse.ArgumentParser(
        description="Start a minimal 10fastfingers-like typing game on the command line"
    )
    parser.add_argument(
        "-v",
        "--vocab",
        type=str,
        metavar="vocab-file-path",
        default=VOCAB_PATH,
        help="path to newline separated vocab file",
    )
    parser.add_argument(
        "-t",
        "--game_time",
        type=int,
        metavar="gametime-seconds",
        default=60,
        help="the duration in seconds of the typing game",
    )
    parser.add_argument(
        "-min",
        "--min_length",
        type=int,
        metavar="min-word-length",
        default=2,
        help="the minimum word length",
    )
    parser.add_argument(
        "-max",
        "--max_length",
        type=int,
        metavar="max-word-length",
        default=10,
        help="the maximum word length",
    )
    parser.add_argument(
        "-w",
        "--words",
        type=int,
        metavar="words-to-read",
        default=1000,
        help="the amount of words to read from vocab file",
    )
    args = parser.parse_args()
    game = Game(args)
    try:
        game.play()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()