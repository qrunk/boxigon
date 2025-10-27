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

        tl =scaling .to_screen ((0 ,self .y ))
        br =scaling .to_screen ((self .width ,self .height ))
        rect =pygame .Rect (tl [0 ],tl [1 ],max (0 ,br [0 ]-tl [0 ]),max (0 ,br [1 ]-tl [1 ]))
        pygame .draw .rect (surf ,self .color ,rect )

    def get_floor_y (self ):
        return self .y 

    def get_friction (self ):
        return self .friction 
