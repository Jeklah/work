"""Game Board class for battleships."""

class GameBoard:
    """Game board class to represent the game area for where the
    ships can be placed in the battleships game."""

    def __init__(self, shipDrawer, gameArea):
        self.gameArea = gameArea

        self.drawBoard(self.gameArea)

    def drawBoard(area):
        for _ in range(area):
            print('~~~~~~~~~~')
