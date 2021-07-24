
class Ship:
    """Battleship class for the ships in the game."""

    def __init__(self, hitpoints, posX, posY, name, alive=True):
        self.hitpoints = hitpoints
        self.posX = posX
        self.posY = posY
        self.alive = alive
        self.name = name

    def shipHit(self):
        self.hitpoints = self.hitpoints - 1

        if self.hitpoints <= 0:
            print(f'{self.name} has been destroyed!')
            self.alive = False
        else:
            print(f'{self.name} has been hit! {self.name} has {self.hitpoints} left')

    def shipDestroyed(self, playerID):
        print(f'{self.name} sinks into the ocean slowly...')

        if playerID.shipsDestroyed >= 1:
            print(f'{playerID.name} has destroyed another ship!')
        else:
            print(f'{playerID.name} has destroyed a ship!')


