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
        # Draw the background grid directly to the target surface so it
        # always fills the whole window regardless of the letterbox/scale
        sw, sh = surf.get_size()
        if sw <= 0 or sh <= 0:
            return

        surf.fill((10, 18, 12))

        # Draw the slightly darker center rectangle scaled from design coords
        # Map design-space rect to screen-space
        ox, oy = scaling.get_offset()
        cur_scale = scaling.get_scale()
        center_rect = pygame.Rect(
            int(round(self.width * 0.05 * cur_scale + ox)),
            int(round(self.height * 0.1 * cur_scale + oy)),
            int(round(self.width * 0.9 * cur_scale)),
            int(round(self.height * 0.7 * cur_scale)),
        )
        pygame.draw.rect(surf, (6, 10, 8), center_rect)

        # Draw grid lines across entire surface. Use scaled grid spacing so
        # the grid remains consistent with design units when scaling is used.
        color = (38, 180, 85)
        grid_px = max(1, int(round(self.grid * cur_scale)))

        x = 0
        while x <= sw:
            pygame.draw.line(surf, color, (x, 0), (x, sh), 1)
            x += grid_px

        y = 0
        while y <= sh:
            pygame.draw.line(surf, color, (0, y), (sw, y), 1)
            y += grid_px

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
