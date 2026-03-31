###   Knight's Tour v13 ##

# section 1 - initial values

    # algebraic notation values

rank_string = ["1", "2", "3", "4", "5", "6", "7", "8"]
file_string = ["a", "b", "c", "d", "e", "f", "g", "h"]

position = []
position_color = []

for x in range(0, 8):
    for y in range(0, 8):
        position.append(file_string[y] + rank_string[x])
        position_color.append(4)

    # square exit values

exit_value = [2, 3, 4, 4, 4, 4, 3, 2, 3, 4, 6, 6, 6, 6, 4, 3, 4, 6, 8, 8, 8, 8, 6, 4, 4, 6, 8, 8, 8, 8, 6, 4, 4, 6, 8, 8, 8,
              8, 6, 4, 4, 6, 8, 8, 8, 8, 6, 4, 3, 4, 6, 6, 6, 6, 4, 3, 2, 3, 4, 4, 4, 4, 3, 2]

# knight's wheel

wheel_rank = [-2, -2, -1, -1, 1, 1, 2, 2]
wheel_file = [-1, 1, -2, 2, -2, 2, -1, 1]

    # tour values

tour_square = []
tour_pos = []
tour_color = []

    # starting square

import random

square = 0
next_square = random.randint(0, 63)

rank = 0

# section 2 - display routines

    # color values

class Mcolor:
    white = '\033[0m'
    red = '\033[31m'
    blue = '\033[34m'
    magenta = '\033[35m'
    gray = '\033[90m'
    green = '\033[92m'
    yellow = '\033[93m'
    cyan = '\033[96m'

color = (Mcolor.magenta, Mcolor.yellow, Mcolor.green, Mcolor.red, Mcolor.gray, Mcolor.cyan, Mcolor.white, Mcolor.blue)

def header():
    print(color[2] + "move #", move_number,
          color[2] + "to",
          file_string[file] + rank_string[rank], "\n")

def rank_and_file():
    for yy in range(0, 8):
        z = 55 - yy * 8 + 1

        print(color[position_color[z]] + position[z], color[position_color[z + 1]] + position[z + 1],
              color[position_color[z + 2]] + position[z + 2], color[position_color[z + 3]] + position[z + 3],
              color[position_color[z + 4]] + position[z + 4], color[position_color[z + 5]] + position[z + 5],
              color[position_color[z + 6]] + position[z + 6], color[position_color[z + 7]] + position[z + 7])

    print("")

def end_of_tour():

    if reentrant_check == 1:
        print(color[5] + "reentrant ", end="")

    print(color[2] + "tour", color[tour_color[0]] + tour_pos[0] + color[2], ">>",
          color[tour_color[63]] + ending_square + color[2], "complete", "\n")

def tour_output():
    for t in range(0, 8):
        print(color[tour_color[t * 8]] + tour_pos[t * 8], color[2] + ">",
              color[tour_color[t * 8 + 1]] + tour_pos[t * 8 + 1], color[2] + ">",
              color[tour_color[t * 8 + 2]] + tour_pos[t * 8 + 2], color[2] + ">",
              color[tour_color[t * 8 + 3]] + tour_pos[t * 8 + 3], color[2] + ">",
              color[tour_color[t * 8 + 4]] + tour_pos[t * 8 + 4], color[2] + ">",
              color[tour_color[t * 8 + 5]] + tour_pos[t * 8 + 5], color[2] + ">",
              color[tour_color[t * 8 + 6]] + tour_pos[t * 8 + 6], color[2] + ">",
              color[tour_color[t * 8 + 7]] + tour_pos[t * 8 + 7], color[2] + ">")

# section 3 - the tour

for move in range(0, 64):

    # position values for each move

    square = next_square
    rank = int(square / 8)
    file = square - rank * 8

    tour_square.append(square)
    tour_pos.append(file_string[file] + rank_string[rank])
    tour_color.append((rank + file) % 2)

    if move < 10:
        move_number = "0" + str(move)
    else:
        move_number = str(move)

    position[square] = move_number
    position_color[square] = 2

    # find valid squares

    exit_value[square] = -1
    exit_color = [0, 0, 0, 0, 0, 0, 0, 0]

    valid_count = 0
    square_valid = [0, 0, 0, 0, 0, 0, 0, 0]

    for b in range(0, 8):
        r = int(square / 8)
        f = square - (r * 8)

        check_rank = r + wheel_rank[b]
        checkfile = f + wheel_file[b]
        square_check = check_rank * 8 + checkfile

        if 0 <= checkfile <= 7 and 0 <= check_rank <= 7:
            if exit_value[square_check] >= 0:
                valid_count += 1
                square_valid[valid_count - 1] = square_check
                exit_color[valid_count - 1] = square_check
                exit_value[square_check] -= 1
                position_color[square_check] = 3

    # find lowest exit value

    lowest_exit = 9

    for c in range(0, valid_count):
        exit_check = exit_value[square_valid[c]]

        if 0 <= exit_check < lowest_exit:
            lowest_exit = exit_check

    # find lowest squares

    lowest_square = [0, 0, 0, 0, 0, 0, 0, 0]
    lowest_count = 0

    for d in range(0, valid_count):
        lowest_check = square_valid[d]

        if exit_value[lowest_check] == lowest_exit:
            lowest_count += 1
            lowest_square[lowest_count] = lowest_check

    # find next square

    if lowest_count > 0:
        pick_exit = random.randint(1, lowest_count)
        next_square = lowest_square[pick_exit]
        ending_square = position[next_square]

    # display board

    header()
    rank_and_file()

    # update exit colors

    position_color[square] = (rank + file) % 2

    for e in range(0, valid_count):
        position_color[exit_color[e]] = 4

    # wait = input()

# section 4 - end of tour

    # check reentrant tour

reentrant_check = 0

for x in range(0, 8):
    r = int(square / 8)
    f = square - rank * 8

    checkfile = f + wheel_file[x]
    check_rank = r + wheel_rank[x]
    square_check = check_rank * 8 + checkfile

    if 0 <= checkfile <= 7 and 0 <= check_rank <= 7:
        if square_check == tour_square[0]:
            reentrant_check += 1

    # end of tour display

end_of_tour()
tour_output()