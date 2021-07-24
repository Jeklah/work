"""Ship Draw class to draw the ships and remove them as the game goes on."""

import Ship
import Player


class ShipDraw:
    """Class to place and remove ships as the game starts and goes on."""

    def startGame(player1=Player.playerID, player2=Player.playerID, gameboard):
        for ship in player1.ships:
            if gameBoard.posX == ship.posX and gameBoard.posY == ship.posY:
                print('*')

