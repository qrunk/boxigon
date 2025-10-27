import sys 
import pygame 
from src .background import Background 
from src .baseplate import Baseplate 
from src .npc import NPC 
from src .fiddle import Fiddle 
from src import scaling 
from src .makersgun import MakersGun 


def main ():
    pygame .init ()

    DESIGN_W ,DESIGN_H =scaling .DESIGN_W ,scaling .DESIGN_H 
    WIDTH ,HEIGHT =DESIGN_W ,DESIGN_H 


    screen =pygame .display .set_mode ((WIDTH ,HEIGHT ),pygame .RESIZABLE )
    pygame .display .set_caption ('Boxigon - Blocky NPC playground')
    clock =pygame .time .Clock ()
    scaling .init (WIDTH ,HEIGHT )

    hud_font =pygame .font .SysFont ('Arial',16 )

    bg =Background (DESIGN_W ,DESIGN_H ,grid_size =40 ,speed =0 )
    base =Baseplate (DESIGN_W ,DESIGN_H ,y =480 )
    fiddle =Fiddle ()
    makersgun =MakersGun ()


    npcs =[NPC (300 ,360 ),NPC (520 ,340 )]

    running =True 
    paused =False 

    while running :
        dt =clock .tick (60 )/1000.0 



        dt =min (dt ,1.0 /30.0 )
        for event in pygame .event .get ():
            if event .type ==pygame .QUIT :
                running =False 
            elif event .type ==pygame .KEYDOWN :
                if event .key ==pygame .K_ESCAPE :
                    running =False 
                elif event .key ==pygame .K_SPACE :
                    paused =not paused 
                elif event .key ==pygame .K_m :

                    makersgun .toggle_menu ()
                elif event .key ==pygame .K_q :

                    makersgun .close_menu ()
            elif event .type ==pygame .VIDEORESIZE :

                screen =pygame .display .set_mode ((event .w ,event .h ),pygame .RESIZABLE )
                scaling .init (event .w ,event .h )

                fs =max (12 ,int (16 *scaling .get_scale ()))
                hud_font =pygame .font .SysFont ('Arial',fs )


            consumed =makersgun .handle_event (event ,npcs )
            if not consumed :
                fiddle .handle_event (event ,npcs )

        if not paused :
            bg .update (dt )
            for npc in npcs :

                npc .update (dt ,floor_y =base )
            fiddle .update (dt )
            makersgun .update (dt ,npcs =npcs ,floor =base )


        bg .draw (screen )
        base .draw (screen )

        for npc in npcs :
            npc .draw (screen )

        fiddle .draw (screen )


        makersgun .draw (screen )


        fps =int (clock .get_fps ())
        txt =hud_font .render (f'FPS: {fps }  NPCs: {len (npcs )}  SPACE pause',True ,(220 ,220 ,220 ))
        screen .blit (txt ,(8 ,8 ))

        pygame .display .flip ()

    pygame .quit ()


if __name__ =='__main__':
    try :
        main ()
    except Exception :
        pygame .quit ()
        raise 