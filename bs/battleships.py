from random import randint
def board(board):
    for i in range(10):
        board.append(["0"]*10)
    return board
def place_boat_cpu(x):
    boats=[5,4,3,3,2]
    for i in range(len(boats)):
        a=randint(0,len(x)-boats[i])
        b=randint(0,len(x)-boats[i])
        if a%2==0:
            while check_free(x,a,b,boats[i])==False:
                a=randint(0,len(x)-boats[i]) 
            x[a][b]="X"
            place=1 
            while place<boats[i]:
                x[a+place][b]="X"
                place+=1
        else:
            while check_free(x,a,b,boats[i])==False:
                b=randint(0,len(x)-boats[i])
            x[a][b]="X"
            place=1
            while place<boats[i]:
                x[a][b+place]="X"
                place+=1
    return x
def check_free(x,a,b,boat):
    if a%2==0:
        for i in range(boat):
            if x[a+i][b]=="X":
                return False
    else:
        for i in range(boat):
            if x[a][b+i]=="X":
                return False
    return True
def check_free_player(x,a,b,c,boat):
    if a==0 and b==9 and c==1:
        return True
    elif c%2==0:
        if b+boat>len(x):
            return False
        for i in range(boat):
            if x[b+i][a]=="X":
                return False
    else:
        if a+boat>len(x):
            return False
        for i in range(boat):
            if x[b][a+i]=="X":
                return False
    return True
def place_boat_player(x):
    boats=[5,4,3,3,2]
    for i in range(len(boats)):
        a=int(input(f"Enter first coordinate of {boats[i]} long boat: "))
        b=int(input(f"Enter second coordinate of {boats[i]} long boat: "))
        c=int(input("Vertical or horizontal (even number=vertical): "))
        if a>9 or b>9:
            print("Thats not even in the ocean!")
            a=int(input(f"Enter first coordinate of {boats[i]} long boat: "))
            b=int(input(f"Enter second coordinate of {boats[i]} long boat: "))
            c=int(input("Vertical or horizontal (even number=vertical): "))
        if c%2==0:
            while check_free_player(x,a,b,c,boats[i])==False:
                a=int(input(f"Space not free, Enter first coordinate of {boats[i]} long boat: "))
                b=int(input(f"Enter second coordinate of {boats[i]} long boat: "))
                c=int(input("Vertical or horizontal (even number=vertical): "))
            x[b][a]="X"
            place=1 
            while place<boats[i]:
                x[b+place][a]="X"
                place+=1
        else:
            while check_free_player(x,a,b,c,boats[i])==False:
                a=int(input(f"Space not free, Enter first coordinate of {boats[i]} long boat: "))
                b=int(input(f"Enter second coordinate of {boats[i]} long boat: "))
            x[b][a]="X"
            place=1
            while place<boats[i]:
                x[b][a+place]="X"
                place+=1
        for i in x:
            print(*i)
    return x
def guess_player(x):
    a=int(input("x coordinate: "))
    b=int(input("y coordinate: "))
    if a>9 or b>9:
        print("Thats not even in the ocean!")
        return x
    elif boardcpu_boats[b][a]=="X":
        print("Hit!")
        x[b][a]="V"
    else:
        print("Miss!")
        x[b][a]="/"
    return x
def win(x,y):
    counter=0
    for i in range(len(x)):
        for j in range(len(x)):
            if x[i][j]=="V":
                counter+=1
    if counter==17:
        return True
    else:
        return False
    return True
def guess_cpu(x):
    guesses=[]
    guess=randint(0,9),randint(0,9)
    guesses.append(guess)
    while guess in guesses:
        guess=randint(0,9),randint(0,9)
    print("Cpu guess: ",guess,)
    if x[guess[1]][guess[0]]=="X":
        x[guess[1]][guess[0]]="V"
        print("Cpu Hit!")
    else:
        x[guess[1]][guess[0]]="/"
        print("Cpu Miss!")
    return x

empty_boardplayer=[]
boardplayer_boats=[]
empty_boardcpu=[]
boardcpu_boats=[]

empty_boardcpu=board(empty_boardcpu)

print("  0 1 2 3 4 5 6 7 8 9")
for i in range(len(empty_boardcpu)-1):
    print(i,*empty_boardcpu[i])
    

empty_boardplayer=board(empty_boardplayer)
boardplayer_boats=place_boat_player(board(boardplayer_boats))
boardcpu_boats=place_boat_cpu(board(boardcpu_boats))

'''
boardcpu=[]
empty_boardcpu=board(boardcpu)
boardplayer=[]
empty_boardplayer=board(boardplayer)
boardcpu_boats=place_boat_cpu(empty_boardcpu)
boardplayer_boats=place_boat_player(empty_boardplayer)

print()
for i in boardcpu_boats:
    print(*i)
print()
'''

while True:
    print()
    print()
    print("Cpu board: ")
    for i in empty_boardcpu:
        print(*i)
    print()
    print()
    print("Friendly board: ")
    for i in boardplayer_boats:
        print(*i)
    guess_player(empty_boardcpu)
    if win(empty_boardcpu,boardcpu_boats)==True:
        print("You Win!")
        break
    guess_cpu(boardplayer_boats)
    if win(empty_boardplayer,boardplayer_boats)==True:
        print("You Lose!")
        break