import pygame 


class Floor :
    def __init__ (self ,y ):
        self .y =y 

    def draw (self ,surf ):
        w ,h =surf .get_size ()
        pygame .draw .rect (surf ,(40 ,40 ,50 ),pygame .Rect (0 ,self .y ,w ,h -self .y ))
