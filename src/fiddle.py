
import pygame 
from src import scaling 


class Fiddle :
    """User interaction to pick and drag NPC particles.

    Usage: call `handle_event(event)` and `update(dt)` then `draw(surface)` as needed.
    """

    def __init__ (self ):
        self .dragging =False 
        self .target =None 
        self .offset =pygame .math .Vector2 (0 ,0 )

    def handle_event (self ,event ,npcs ):
        if event .type ==pygame .MOUSEBUTTONDOWN :
            if event .button ==1 :


                pos =scaling .to_world (event .pos )

                best =None 
                best_d =9999 
                for npc in npcs :
                    idx =npc .nearest_particle_index (pos ,max_dist =60 )
                    if idx is None :
                        continue 
                    p =npc .particles [idx ]
                    d =(p .pos -pygame .math .Vector2 (pos )).length ()
                    if d <best_d :
                        best_d =d 
                        best =(npc ,idx )
                if best is not None :
                    self .dragging =True 
                    self .target =best 
                    p =best [0 ].particles [best [1 ]]
                    self .offset =p .pos -pygame .math .Vector2 (pos )

        elif event .type ==pygame .MOUSEBUTTONUP :
            if event .button ==1 :
                self .dragging =False 
                self .target =None 

    def update (self ,dt ):
        if self .dragging and self .target is not None :
            npc ,idx =self .target 

            m_screen =pygame .mouse .get_pos ()
            mpos =pygame .math .Vector2 (scaling .to_world (m_screen ))
            desired =mpos +self .offset 
            p =npc .particles [idx ]

            p .pos =desired 

    def draw (self ,surf ):
        if self .dragging and self .target is not None :
            npc ,idx =self .target 
            p =npc .particles [idx ]
            pygame .draw .circle (surf ,(255 ,120 ,80 ),(int (p .pos .x ),int (p .pos .y )),8 )
