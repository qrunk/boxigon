import math 
import pygame 
from src import scaling 


class Particle :
    def __init__ (self ,pos ,mass =1.0 ):
        self .pos =pygame .math .Vector2 (pos )
        self .prev =pygame .math .Vector2 (pos )
        self .acc =pygame .math .Vector2 (0 ,0 )
        self .mass =mass 

    def apply_force (self ,f ):
        self .acc +=f /max (self .mass ,1e-6 )

    def update (self ,dt ):

        vel =self .pos -self .prev 
        self .prev =self .pos .copy ()
        self .pos +=vel +self .acc *(dt *dt )

        self .acc .update (0 ,0 )


class NPC :
    """A blocky NPC composed of rectangular parts connected with constraints."""

    def __init__ (self ,x ,y ):


        self .particles =[]
        self .constraints =[]


        head =Particle ((x ,y -100 ))
        t1 =Particle ((x ,y -60 ))
        t2 =Particle ((x ,y -20 ))
        t3 =Particle ((x ,y +20 ))
        t4 =Particle ((x ,y +60 ))

        l_arm =Particle ((x -30 ,y -10 ))
        r_arm =Particle ((x +30 ,y -10 ))
        l_leg =Particle ((x -8 ,y +140 ))
        r_leg =Particle ((x +8 ,y +140 ))


        self .particles =[head ,t1 ,t2 ,t3 ,t4 ,l_arm ,r_arm ,l_leg ,r_leg ]

        def connect (a ,b ,slack =0.0 ):
            pa =self .particles [a ]
            pb =self .particles [b ]
            dist =(pa .pos -pb .pos ).length ()*(1.0 +slack )
            self .constraints .append ((a ,b ,dist ))


        connect (0 ,1 )
        connect (1 ,2 )
        connect (2 ,3 )
        connect (3 ,4 )


        connect (2 ,5 )
        connect (2 ,6 )


        connect (4 ,7 )
        connect (4 ,8 )


        connect (1 ,3 ,slack =0.05 )
        connect (2 ,4 ,slack =0.05 )


        self .size =14 

        self .head_size =32 

        self .color =(54 ,160 ,60 )
        self .outline =(16 ,40 ,18 )
        self .gravity =pygame .math .Vector2 (0 ,900 )

        self .cut_particles =set ()

    def apply_global_force (self ,f ):
        for p in self .particles :
            p .apply_force (f )

    def update (self ,dt ,floor_y =None ):


        floor_obj =None 
        friction =0.6 
        if floor_y is not None :
            if hasattr (floor_y ,'get_floor_y'):
                floor_obj =floor_y 
                fy =floor_obj .get_floor_y ()
                friction =getattr (floor_obj ,'get_friction',lambda :friction )()
            else :
                fy =floor_y 
        else :
            fy =None 


        for p in self .particles :
            p .apply_force (self .gravity *p .mass )

        for p in self .particles :
            p .update (dt )


        for _ in range (5 ):
            for i ,j ,rest in self .constraints :
                pa =self .particles [i ]
                pb =self .particles [j ]
                delta =pb .pos -pa .pos 
                d =delta .length ()
                if d ==0 :
                    continue 
                diff =(d -rest )/d 

                pa .pos +=delta *0.5 *diff 
                pb .pos -=delta *0.5 *diff 



        if fy is not None :
            for idx ,p in enumerate (self .particles ):
                if p .pos .y >fy -(self .size /2 ):

                    p .pos .y =fy -(self .size /2 )

                    vel =p .pos -p .prev 

                    vel .y =0 

                    vel .x *=max (0.0 ,friction )

                    p .prev =p .pos -vel 

    def apply_bullet_hit (self ,pos ):
        """Apply bullet damage at world-space position pos.
        Cuts out nearest particle (if within a reasonable distance) and
        removes constraints attached to it so the NPC can deform.
        """
        idx =self .nearest_particle_index (pos ,max_dist =40 )
        if idx is None :
            return 

        try :
            self .cut_particles .add (idx )
        except Exception :
            pass 

        try :
            self .constraints =[c for c in self .constraints if idx not in (c [0 ],c [1 ])]
        except Exception :
            pass 

        try :
            hit =self .particles [idx ]
            for i ,p in enumerate (self .particles ):
                d =(p .pos -hit .pos ).length ()
                if d <60 and d >0 :
                    push =(p .pos -hit .pos ).normalize ()*(60.0 /max (4.0 ,d ))
                    p .pos +=push 
        except Exception :
            pass 

    def draw (self ,surf ):

        torso_indices =[0 ,1 ,2 ,3 ,4 ]
        outline_w =max (1 ,scaling .to_screen_length (self .size *2.0 ))
        inner_w =max (1 ,scaling .to_screen_length (self .size *1.4 ))
        for a ,b in zip (torso_indices [:-1 ],torso_indices [1 :]):
            pa =scaling .to_screen_vec (self .particles [a ].pos )
            pb =scaling .to_screen_vec (self .particles [b ].pos )

            if a in self .cut_particles or b in self .cut_particles :
                continue 
            pygame .draw .line (surf ,self .outline ,(pa .x ,pa .y ),(pb .x ,pb .y ),outline_w )
            pygame .draw .line (surf ,self .color ,(pa .x ,pa .y ),(pb .x ,pb .y ),inner_w )


        for idx in torso_indices :

            if idx in self .cut_particles :
                continue 
            ppos =scaling .to_screen_vec (self .particles [idx ].pos )
            pygame .draw .circle (surf ,self .outline ,(int (ppos .x ),int (ppos .y )),scaling .to_screen_length (self .size *1.2 ))
            pygame .draw .circle (surf ,self .color ,(int (ppos .x ),int (ppos .y )),scaling .to_screen_length (self .size *0.9 ))


        arm_outline =max (1 ,scaling .to_screen_length (self .size *1.4 ))
        arm_inner =max (1 ,scaling .to_screen_length (self .size *1.0 ))
        for idx in (5 ,6 ):

            if idx in self .cut_particles or 2 in self .cut_particles :
                continue 
            p =scaling .to_screen_vec (self .particles [idx ].pos )
            attach =scaling .to_screen_vec (self .particles [2 ].pos )
            pygame .draw .line (surf ,self .outline ,(attach .x ,attach .y ),(p .x ,p .y ),arm_outline )
            pygame .draw .line (surf ,self .color ,(attach .x ,attach .y ),(p .x ,p .y ),arm_inner )

            pygame .draw .circle (surf ,self .color ,(int (p .x ),int (p .y )),scaling .to_screen_length (self .size *0.8 ))


        leg_outline =max (1 ,scaling .to_screen_length (self .size *1.6 ))
        leg_inner =max (1 ,scaling .to_screen_length (self .size *1.1 ))
        for idx in (7 ,8 ):

            if idx in self .cut_particles or 4 in self .cut_particles :
                continue 
            p =scaling .to_screen_vec (self .particles [idx ].pos )
            attach =scaling .to_screen_vec (self .particles [4 ].pos )
            pygame .draw .line (surf ,self .outline ,(attach .x ,attach .y ),(p .x ,p .y ),leg_outline )
            pygame .draw .line (surf ,self .color ,(attach .x ,attach .y ),(p .x ,p .y ),leg_inner )

            pygame .draw .circle (surf ,self .color ,(int (p .x ),int (p .y )),scaling .to_screen_length (self .size *0.9 ))



        if 0 not in self .cut_particles :
            head_pos =scaling .to_screen_vec (self .particles [0 ].pos )
            hs =scaling .to_screen_length (self .head_size )
            head_rect =pygame .Rect (0 ,0 ,hs ,hs )
            head_rect .center =(int (head_pos .x ),int (head_pos .y ))
            pygame .draw .rect (surf ,self .outline ,head_rect )
            inner =head_rect .inflate (-max (2 ,scaling .to_screen_length (3 )),-max (2 ,scaling .to_screen_length (3 )))
            pygame .draw .rect (surf ,self .color ,inner )


            eye_x =int (head_pos .x +hs *0.18 )
            eye_y =int (head_pos .y -hs *0.05 )
            eye_w =max (1 ,scaling .to_screen_length (4 ))
            pygame .draw .rect (surf ,(10 ,10 ,10 ),pygame .Rect (eye_x ,eye_y ,eye_w ,eye_w ))

    def nearest_particle_index (self ,pos ,max_dist =40 ):
        best =None 
        best_d =max_dist 
        v =pygame .math .Vector2 (pos )
        for i ,p in enumerate (self .particles ):
            d =(p .pos -v ).length ()
            if d <best_d :
                best_d =d 
                best =i 
        return best 
