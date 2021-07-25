"""Game Board class for battleships."""

class GameBoard:
    """Game board class to represent the game area for where the
    ships can be placed in the battleships game."""

    def __init__(self, shipDrawer, boardGrid):
        self.drawBoard(10)
        self.boardGrid = [10][10]

    def drawBoard(area):
        for _ in range(area):
            for boardX in range(area):
                if boardX == 10:
                    print('~')
                else:
                    print('~ ', end = '')


