import pygame 
from src import scaling 


class Baseplate :
    """A simple 2D floor / baseplate.

    It provides collision information for NPCs and draws the floor graphic.
    Includes a friction coefficient to reduce sliding.
    """

    def __init__ (self ,width ,height ,y =500 ,color =(80 ,80 ,90 ),friction =0.12 ):
        self .width =width 
        self .height =height 
        self .y =y 
        self .color =color 


        self .friction =friction 

    def draw (self ,surf ):
        # Draw baseplate so it spans the entire window width and reaches
        # to the bottom of the surface. Compute the top Y using scaling
        # so the visual lines up with world coordinates, but use the
        # surface's full width/height to guarantee full coverage.
        tl = scaling.to_screen((0, self.y))
        top_y = tl[1]
        sw, sh = surf.get_size()
        rect = pygame.Rect(0, top_y, sw, max(0, sh - top_y))
        pygame.draw.rect(surf, self.color, rect)

    def get_floor_y (self ):
        return self .y 

    def get_friction (self ):
        return self .friction 
