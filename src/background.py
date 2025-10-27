import pygame 
from src import scaling 


class Background :
    """Static green grid background using design-space units.

    The background no longer scrolls. It is drawn using the design
    coordinate system and scaled to the current window using `src.scaling`.
    """

    def __init__ (self ,width ,height ,grid_size =40 ,speed =0 ):

        self .width =width 
        self .height =height 
        self .grid =grid_size 

        self .speed =speed 



        self ._design_surf =pygame .Surface ((int (self .width ),int (self .height )))
        self ._render_design_surface ()

        self ._cached_scale =None 
        self ._cached_scaled =None 

    def update (self ,dt ):

        return 

    def draw (self ,surf ):


        sw =int (round (self .width *scaling .get_scale ()))
        sh =int (round (self .height *scaling .get_scale ()))
        if sw <=0 or sh <=0 :
            return 
        cur_scale =scaling .get_scale ()

        if self ._cached_scaled is None or self ._cached_scale !=cur_scale :
            try :
                self ._cached_scaled =pygame .transform .smoothscale (self ._design_surf ,(sw ,sh ))
            except Exception :
                self ._cached_scaled =pygame .transform .scale (self ._design_surf ,(sw ,sh ))
            self ._cached_scale =cur_scale 

        ox ,oy =scaling .get_offset ()
        surf .fill ((10 ,18 ,12 ))
        surf .blit (self ._cached_scaled ,(int (ox ),int (oy )))

    def _render_design_surface (self ):
        """Render the static background into the design-space surface."""
        s =self ._design_surf 
        s .fill ((10 ,18 ,12 ))

        center_rect =pygame .Rect (self .width *0.05 ,self .height *0.1 ,self .width *0.9 ,self .height *0.7 )
        pygame .draw .rect (s ,(6 ,10 ,8 ),center_rect )

        color =(38 ,180 ,85 )

        x =0 
        while x <=int (self .width )+self .grid :
            pygame .draw .line (s ,color ,(x ,0 ),(x ,int (self .height )),1 )
            x +=self .grid 

        y =0 
        while y <=int (self .height )+self .grid :
            pygame .draw .line (s ,color ,(0 ,y ),(int (self .width ),y ),1 )
            y +=self .grid 
