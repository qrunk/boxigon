import os 
import pygame 
from src import scaling 
from src .npc import Particle, NPC 
from src.worldman import get_world_manager
from src import colison


class Brick :
    """A simple square 'lego-like' brick backed by a single Verlet particle.

    This is a lightweight object (single particle) so it behaves like a
    point with a drawn square. It supports gravity and simple floor collision.
    """

    def __init__ (self ,pos ,size =40 ,mass =1.0 ,color =(180 ,30 ,30 )):
        self .p =Particle (pos ,mass =mass )
        self .size =size 
        self .color =color 
        self .outline =(30 ,10 ,10 )
        # If welded_to is not None this brick will follow that brick's
        # position with a fixed offset. This implements simple "lego-like"
        # stacking: when bricks touch gently from above they snap and stay
        # attached.
        self.welded_to = None
        self.welded_offset = pygame.math.Vector2(0, 0)
        # children welded to this brick (so we can move/iterate group)
        self.welded_children = []

    def get_root(self):
        """Return the top-most ancestor in the welded chain (self if none)."""
        cur = self
        seen = set()
        while getattr(cur, 'welded_to', None) is not None:
            # defensive: break cycles
            if id(cur) in seen:
                break
            seen.add(id(cur))
            cur = cur.welded_to
        return cur

    def add_weld(self, parent, offset=None):
        """Weld this brick to parent. Handles list bookkeeping."""
        # remove from previous parent if any
        try:
            if getattr(self, 'welded_to', None) is not None and self.welded_to is not parent:
                try:
                    self.welded_to.welded_children.remove(self)
                except Exception:
                    pass
        except Exception:
            pass
        self.welded_to = parent
        if offset is None:
            try:
                self.welded_offset = self.p.pos - parent.p.pos
            except Exception:
                self.welded_offset = pygame.math.Vector2(0, 0)
        else:
            self.welded_offset = offset
        try:
            if self not in parent.welded_children:
                parent.welded_children.append(self)
        except Exception:
            pass

    def remove_weld(self):
        """Unweld this brick from its parent (if any)."""
        try:
            if getattr(self, 'welded_to', None) is not None:
                try:
                    self.welded_to.welded_children.remove(self)
                except Exception:
                    pass
        except Exception:
            pass
        self.welded_to = None

    def apply_force (self ,f ):
        self .p .apply_force (f )

    def update (self ,dt ,floor_y =None ,other_bricks =None ):

        # If welded to another brick, follow that brick and don't simulate
        # independent physics. We'll still return early so stacked bricks
        # remain locked in place relative to their parent.
        if self.welded_to is not None:
            try:
                # If the target was removed, un-weld
                if other_bricks is not None and self.welded_to not in other_bricks:
                    self.remove_weld()
                else:
                    # follow parent but copy parent's velocity so group moves
                    parent = self.welded_to
                    self.p.pos = parent.p.pos + self.welded_offset
                    # give child the same velocity as parent for smooth group motion
                    parent_vel = parent.p.pos - parent.p.prev
                    self.p.prev = self.p.pos - parent_vel
                    # continue and participate in collision resolution so grouped
                    # bricks interact correctly with the world
            except Exception:
                # fallback: clear weld and continue physics
                self.remove_weld()

        gravity =pygame .math .Vector2 (0 ,900 )
        self .p .apply_force (gravity *self .p .mass )
        self .p .update (dt )


        if floor_y is not None :
            if hasattr (floor_y ,'get_floor_y'):
                fy =floor_y .get_floor_y ()
            else :
                fy =floor_y 
            if fy is not None and self .p .pos .y >fy -(self .size /2 ):
                self .p .pos .y =fy -(self .size /2 )
                if hasattr (floor_y ,'get_friction'):
                    friction =floor_y .get_friction ()
                else :
                    friction =0.35 

                vel =self .p .pos -self .p .prev 
                vel .y =0 
                vel .x *=friction 
                self .p .prev =self .p .pos -vel 


        if other_bricks :
            for other in other_bricks :
                if other !=self :
                    # skip internal collisions within a welded group to avoid
                    # pushing apart bricks that are intentionally attached
                    try:
                        if hasattr(self, 'get_root') and hasattr(other, 'get_root'):
                            if self.get_root() is other.get_root():
                                continue
                    except Exception:
                        pass

                    diff =self .p .pos -other .p .pos 
                    dist =diff .length ()
                    min_dist =(self .size +other .size )/2 

                    if dist <min_dist and dist >0 :

                        norm =diff /dist 

                        overlap =min_dist -dist 

                        total_mass =self .p .mass +other .p .mass 
                        self_ratio =other .p .mass /total_mass 
                        other_ratio =self .p .mass /total_mass 


                        self .p .pos +=norm *overlap *self_ratio 


                        self_vel =self .p .pos -self .p .prev 
                        other_vel =other .p .pos -other .p .prev 
                        rel_vel =self_vel -other_vel 
                        vel_along_normal =rel_vel .dot (norm )


                        if vel_along_normal <0 :
                            restitution =0.3 
                            j =-(1 +restitution )*vel_along_normal 
                            j /=1 /self .p .mass +1 /other .p .mass 

                            impulse =norm *j 

                            self .p .prev =self .p .pos -(self_vel +(impulse /self .p .mass ))
                            other .p .prev =other .p .pos -(other_vel -(impulse /other .p .mass ))

                        # Simple "snap/weld" behavior: if this brick gently
                        # lands on top of another brick (normal mostly
                        # vertical and pointing upward toward this brick)
                        # and relative velocity is low, attach it so it
                        # stays stacked like lego.
                        try:
                            rel_speed = rel_vel.length()
                            # norm is a vector from other -> self. If its y is
                            # strongly negative, self is above other.
                            vertical_indicator = norm.y
                            horiz_sep = abs(diff.x)
                            horiz_tol = (self.size + other.size) * 0.35
                            # thresholds chosen heuristically
                            if vertical_indicator < -0.7 and rel_speed < 120 and horiz_sep < horiz_tol:
                                # Weld the higher brick (self) to the lower (other)
                                try:
                                    self.add_weld(other)
                                    # align prev to parent velocity to avoid jitter
                                    parent_vel = other.p.pos - other.p.prev
                                    self.p.prev = self.p.pos - parent_vel
                                except Exception:
                                    # fallback to simple assignment
                                    self.welded_to = other
                                    self.welded_offset = self.p.pos - other.p.pos
                                    self.p.prev = self.p.pos.copy()
                        except Exception:
                            pass

    def draw (self ,surf ):
        center =scaling .to_screen_vec (self .p .pos )
        s =scaling .to_screen_length (self .size )
        rect =pygame .Rect (0 ,0 ,int (s ),int (s ))
        rect .center =(int (center .x ),int (center .y ))
        pygame .draw .rect (surf ,self .outline ,rect )
        inner =rect .inflate (-max (2 ,scaling .to_screen_length (3 )),-max (2 ,scaling .to_screen_length (3 )))
        pygame .draw .rect (surf ,self .color ,inner )


class MakersGun :
    """Attach to mouse cursor, show spawn menu, spawn bricks on left click,
    pick up/move objects on right click.

    Methods:
        handle_event(event, npcs) -> bool: returns True if event consumed
        update(dt, floor=None)
        draw(surf)
    """

    def __init__ (self ):
        self .target =None 
        self .offset =pygame .math .Vector2 (0 ,0 )
        self .dragging =False 

        self .equipped =False 

        self .menu_open =False 

        self .menu_selected =None 

        try :
            self ._prev_cursor_visible =pygame .mouse .get_visible ()
        except Exception :
            self ._prev_cursor_visible =True 
        self .bricks =[]
        self .welding_tool =None 
        self .pistol =None 
        self .thruster_icon =None
        self .axe =None
        self .axe_icon =None

        self .icon =None 
        self .welding_icon =None 
        self .pistol_icon =None 
        try :
            base =os .path .join (os .path .dirname (__file__ ),'assets')

            path =os .path .join (base ,'makergun.png')
            if os .path .exists (path ):
                self .icon =pygame .image .load (path ).convert_alpha ()
            weld_path =os .path .join (base ,'weldingtool.png')
            if os .path .exists (weld_path ):
                self .welding_icon =pygame .image .load (weld_path ).convert_alpha ()
            pistol_path =os .path .join (base ,'pistol.png')
            if os .path .exists (pistol_path ):
                self .pistol_icon =pygame .image .load (pistol_path ).convert_alpha ()
            thruster_path =os .path .join (base ,'thruster.png')
            if os .path .exists (thruster_path ):
                self .thruster_icon =pygame .image .load (thruster_path ).convert_alpha ()
            axe_path =os.path.join(base, 'axe.png')
            if os.path.exists(axe_path):
                self .axe_icon =pygame.image.load(axe_path).convert_alpha()
        except Exception :
            self .icon =None 
            self .welding_icon =None 


        self .menu_w =96 
        self .menu_h =40 
    def pickup_welding_tool (self ):
        if self .welding_tool :
            self .welding_tool ['held']=True 

    def drop_welding_tool (self ):
        if self .welding_tool :
            self .welding_tool ['held']=False 
        return 

    def equip (self ):
        """Equip the makers gun (attach to cursor)."""
        if not self .equipped :
            self .equipped =True 

            try :
                self ._prev_cursor_visible =pygame .mouse .get_visible ()
                pygame .mouse .set_visible (False )
            except Exception :
                pass 

    def drop (self ):
        """Drop / unequip the makers gun and cancel any dragging."""
        if self .equipped :
            self .equipped =False 
            self .dragging =False 
            self .target =None 

            try :
                pygame .mouse .set_visible (self ._prev_cursor_visible )
            except Exception :
                pass 


    def spawn_brick (self ,world_pos ):
        b =Brick (world_pos ,size =40 )
        self .bricks .append (b )
        try:
            mgr = get_world_manager()
            if mgr.current_name:
                mgr.add_brick({"type": "brick", "x": float(world_pos[0]) if isinstance(world_pos, (list, tuple)) else float(world_pos.x), "y": float(world_pos[1]) if isinstance(world_pos, (list, tuple)) else float(world_pos.y), "size": 40})
                mgr.save_now()
        except Exception:
            pass

    def spawn_welding_tool (self ,world_pos ):

        self .welding_tool ={'pos':pygame .math .Vector2 (world_pos ),'held':False }

    def spawn_pistol (self ,world_pos ):
        self .pistol ={'pos':pygame .math .Vector2 (world_pos ),'held':False }

    def spawn_thruster(self, world_pos):
        """Spawn a thruster object into the world (appended to bricks so it
        participates in collisions and can be welded by the welding tool).
        """
        try :
            from src .thruster import Thruster
            t =Thruster (world_pos ,icon =self .thruster_icon )
            # put thrusters into the bricks list so existing collision/welding
            # code will treat them like other spawned objects
            self .bricks .append (t )
            try:
                mgr = get_world_manager()
                if mgr.current_name:
                    mgr.add_brick({"type": "thruster", "x": float(world_pos[0]) if isinstance(world_pos, (list, tuple)) else float(world_pos.x), "y": float(world_pos[1]) if isinstance(world_pos, (list, tuple)) else float(world_pos.y), "size": getattr(t, 'size', 32)})
                    mgr.save_now()
            except Exception:
                pass
        except Exception :
            pass

    def spawn_axe(self, world_pos):
        self.axe = {'pos': pygame.math.Vector2(world_pos), 'held': False}

    def pickup_axe(self):
        if self.axe:
            self.axe['held'] = True

    def drop_axe(self):
        if self.axe:
            self.axe['held'] = False
        return

    def pickup_pistol (self ):
        if self .pistol :
            self .pistol ['held']=True 

    def drop_pistol (self ):
        if self .pistol :
            self .pistol ['held']=False 

    def open_menu (self ):
        """Open the spawn menu (centered). Restores the OS cursor so the
        user can click items. We remember previous cursor visibility to
        restore on close.
        """
        if not self .menu_open :
            try :
                self ._prev_cursor_visible =pygame .mouse .get_visible ()
                pygame .mouse .set_visible (True )
            except Exception :
                pass 


        self .menu_open =True 

    def close_menu (self ):
        """Close the spawn menu and restore previous cursor visibility."""
        if self .menu_open :
            self .menu_open =False 
            try :
                pygame .mouse .set_visible (self ._prev_cursor_visible )
            except Exception :
                pass 

    def clear_selection (self ):
        """Clear any previously selected menu item (stop repeated spawning)."""
        self .menu_selected =None 

    def toggle_menu (self ):
        """Toggle the spawn menu open/closed."""
        if self .menu_open :
            self .close_menu ()
        else :
            self .open_menu ()

    def find_nearest_moveable (self ,world_pos ,npcs ,max_dist =80 ):

        best =None 
        best_d =max_dist 
        v =pygame .math .Vector2 (world_pos )


        for b in self .bricks :
            d =(b .p .pos -v ).length ()
            if d <best_d :
                best_d =d 
                best =('brick',b )


        if best_d >max_dist *0.5 :
            for npc in npcs :
                try :
                    p =npc .particles [2 ].pos 
                except Exception :
                    try :
                        p =npc .particles [0 ].pos 
                    except Exception :
                        continue 
                d =(p -v ).length ()
                if d <best_d :
                    best_d =d 
                    best =('npc',npc )

        return best 

    def handle_event (self ,event ,npcs ):
        """Return True if event consumed (so caller shouldn't forward to Fiddle)."""
        consumed =False 


        if self .menu_open :
            if event .type ==pygame .MOUSEBUTTONDOWN :
                if event .button ==1 :
                    mx ,my =event .pos 

                    try :
                        surf =pygame .display .get_surface ()
                        sw ,sh =surf .get_size ()
                    except Exception :
                        sw ,sh =800 ,600 


                    items =['Brick','Wielding Tool','Pistol','Axe','Thruster','NPC']

                    menu_w =max (300 ,int (sw *0.75 ))
                    menu_h =max (200 ,int (sh *0.6 ))

                    menu_w =min (menu_w ,sw -80 )
                    menu_h =min (menu_h ,sh -120 )
                    menu_x =(sw -menu_w )//2 
                    menu_y =(sh -menu_h )//2 

                    item_h =int ((menu_h -72 )/max (1 ,len (items )))

                    for i ,name in enumerate (items ):
                        r =pygame .Rect (menu_x +24 ,menu_y +40 +i *item_h ,menu_w -48 ,item_h -8 )
                        if r .collidepoint (mx ,my ):


                            if name in ('Wielding Tool','Pistol','Axe','NPC'):
                                try :
                                    world_pos =scaling .to_world ((mx ,my ))
                                    if name =='Wielding Tool':
                                        self .spawn_welding_tool (world_pos )
                                    elif name =='Pistol':
                                        self .spawn_pistol (world_pos )
                                    elif name == 'Axe':
                                        self.spawn_axe(world_pos)
                                    else:
                                        # spawn NPC immediately into the provided list
                                        try:
                                            # to_world returns a tuple (x,y) so unpack it
                                            wx, wy = world_pos
                                            npcs.append(NPC(wx, wy))
                                            try:
                                                mgr = get_world_manager()
                                                if mgr.current_name:
                                                    mgr.add_npc({"x": float(wx), "y": float(wy)})
                                                    # extra explicit flush to disk to be robust
                                                    mgr.save_now()
                                            except Exception:
                                                pass
                                        except Exception:
                                            try:
                                                # fallback if it's a Vector2-like
                                                nx, ny = world_pos.x, world_pos.y
                                                npcs.append(NPC(nx, ny))
                                                try:
                                                    mgr = get_world_manager()
                                                    if mgr.current_name:
                                                        mgr.add_npc({"x": float(nx), "y": float(ny)})
                                                        mgr.save_now()
                                                except Exception:
                                                    pass
                                            except Exception:
                                                pass
                                except Exception :
                                    pass 

                                self .menu_selected =None 
                            else :
                                self .menu_selected =name 
                            self .close_menu ()
                            consumed =True 
                            break 

                elif event .button ==3 :

                    self .close_menu ()
                    consumed =True 

            elif event .type ==pygame .KEYDOWN :
                if event .key in (pygame .K_q ,pygame .K_ESCAPE ):
                    self .close_menu ()
                    consumed =True 

            return consumed 



        if self .menu_selected is not None :
            if event .type ==pygame .MOUSEBUTTONDOWN and event .button ==3 :
                pos =scaling .to_world (event .pos )
                if self .menu_selected =='Brick':
                    self .spawn_brick (pos )
                    consumed =True 
                    return consumed 
                elif self .menu_selected =='Wielding Tool':
                    self .spawn_welding_tool (pos )
                    consumed =True 
                    return consumed 
                elif self .menu_selected =='Pistol':
                    self .spawn_pistol (pos )
                    consumed =True 
                    return consumed 
                elif self .menu_selected == 'Axe':
                    self.spawn_axe(pos)
                    consumed = True
                    return consumed
                elif self .menu_selected =='Thruster':
                    self .spawn_thruster (pos )
                    consumed =True 
                    return consumed 
                elif self .menu_selected == 'NPC':
                    try:
                        px, py = pos
                        npcs.append(NPC(px, py))
                        try:
                            mgr = get_world_manager()
                            if mgr.current_name:
                                mgr.add_npc({"x": float(px), "y": float(py)})
                                mgr.save_now()
                        except Exception:
                            pass
                    except Exception:
                        try:
                            nx, ny = pos.x, pos.y
                            npcs.append(NPC(nx, ny))
                            try:
                                mgr = get_world_manager()
                                if mgr.current_name:
                                    mgr.add_npc({"x": float(nx), "y": float(ny)})
                                    mgr.save_now()
                            except Exception:
                                pass
                        except Exception:
                            pass
                    consumed = True
                    return consumed

            if self .menu_selected =='Wielding Tool'and event .type ==pygame .MOUSEBUTTONDOWN and event .button ==1 :
                if self .welding_tool and not self .welding_tool ['held']:
                    mouse_pos =pygame .math .Vector2 (scaling .to_world (event .pos ))
                    if (mouse_pos -self .welding_tool ['pos']).length ()<48 :
                        self .pickup_welding_tool ()
                        consumed =True 
                        return consumed 
            if self .menu_selected == 'Axe' and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.axe and not self.axe.get('held', False):
                    mouse_pos = pygame.math.Vector2(scaling.to_world(event.pos))
                    try:
                        if (mouse_pos - self.axe['pos']).length() < 48:
                            self.pickup_axe()
                            consumed = True
                            return consumed
                    except Exception:
                        pass


        if event .type ==pygame .MOUSEBUTTONDOWN :

            if event .button ==3 and self .pistol and self .pistol .get ('held',False ):
                try :
                    from src .guns .pistol import Pistol 
                    if not hasattr (self ,'_pistol_obj')or self ._pistol_obj is None :
                        self ._pistol_obj =Pistol (self .pistol ['pos'],icon =self .pistol_icon )

                    self ._pistol_obj .pos =self .pistol ['pos']
                    self ._pistol_obj .held =self .pistol ['held']
                    target =scaling .to_world (event .pos )
                    self ._pistol_obj .shoot (target )
                    consumed =True 
                    return consumed 
                except Exception :
                    pass 
            pos =scaling .to_world (event .pos )

            if event .button ==3 :
                if self .menu_selected =='Wielding Tool':
                    self .spawn_welding_tool (pos )
                elif self .menu_selected =='Pistol':
                    self .spawn_pistol (pos )
                elif self .menu_selected == 'Axe':
                    self.spawn_axe(pos)
                elif self .menu_selected =='Thruster':
                    self .spawn_thruster (pos )
                else :
                    self .spawn_brick (pos )
                consumed =True 
                return consumed 

            elif event .button ==1 :

                if self .welding_tool and not self .welding_tool .get ('held',False ):
                    try :
                        if (pos -self .welding_tool ['pos']).length ()<48 :
                            self .welding_tool ['held']=True 
                            consumed =True 
                            return consumed 
                    except Exception :
                        pass 



                if self .pistol and not self .pistol .get ('held',False ):
                    try :
                        if (pos -self .pistol ['pos']).length ()<96 :
                            self .pistol ['held']=True 
                            consumed =True 
                            return consumed 
                    except Exception :
                        pass 


                if self .axe and not self .axe.get('held', False):
                    try:
                        if (pos - self .axe['pos']).length() < 48:
                            self .axe['held'] = True
                            consumed = True
                            return consumed
                    except Exception:
                        pass


                found =self .find_nearest_moveable (pos ,npcs ,max_dist =80 )
                if found is not None :
                    self .dragging =True 
                    self .target =found 
                    if found [0 ]=='brick':
                        brick =found [1 ]
                        # If the brick is part of a welded group, move the whole
                        # connected group. We compute an offset for the group's
                        # root so the picked brick will track the cursor while
                        # the whole group follows.
                        try:
                            root = brick.get_root()
                        except Exception:
                            root = brick
                        # store both root and the originally selected brick
                        self.target = ('brick_group', (root, brick))
                        # offset so that when root moves, the selected brick
                        # ends up under the cursor: offset = root.pos - selected.pos
                        try:
                            self.offset = root.p.pos - brick.p.pos
                        except Exception:
                            self.offset = pygame.math.Vector2(0, 0)
                        consumed = True
                    else :
                        npc =found [1 ]
                        try :
                            p =npc .particles [2 ]
                            self .offset =p .pos -pygame .math .Vector2 (pos )
                            consumed =True 
                        except Exception :
                            self .dragging =False 
                            self .target =None 
                return consumed 

        elif event .type ==pygame .MOUSEBUTTONUP :
            if event .button ==1 and self .dragging :

                self .dragging =False 
                if self .target and self .target [0 ]=='brick':

                    ttype = self.target[0]
                    if ttype == 'brick':
                        brick = self.target[1]
                        old_pos = brick.p.prev
                        brick.p.prev = brick.p.pos - (brick.p.pos - old_pos) * 0.5
                    elif ttype == 'brick_group':
                        try:
                            root, selected = self.target[1]
                        except Exception:
                            root = self.target[1]
                        old_prev = root.p.prev
                        old_vel = root.p.pos - old_prev
                        # damp the root velocity
                        root.p.prev = root.p.pos - (old_vel * 0.5)
                        # propagate damped velocity to descendants
                        try:
                            damp_vel = root.p.pos - root.p.prev
                            queue = [root]
                            while queue:
                                parent = queue.pop(0)
                                for child in getattr(parent, 'welded_children', []):
                                    child.p.prev = child.p.pos - damp_vel
                                    queue.append(child)
                        except Exception:
                            pass
                self .target =None 
                consumed =True 
                return consumed 


            if self .welding_tool and self .welding_tool .get ('held',False )and event .button ==1 :
                self .welding_tool ['held']=False 
                consumed =True 
                return consumed 

            if self .axe and self .axe.get('held', False) and event.button == 1:
                self .axe['held'] = False
                consumed = True
                return consumed

        return consumed 

    def update (self ,dt ,npcs =None ,floor =None ):

        for b in self .bricks :
            b .update (dt ,floor_y =floor ,other_bricks =self .bricks )

        # Automatic collision: resolve NPC particles against spawned bricks.
        # This keeps NPCs from passing through maker bricks without any
        # extra wiring in the main loop.
        if npcs and self .bricks :
            try :
                for npc in npcs :
                    colison.collide_particles_with_bricks(npc.particles, self.bricks, iterations=2)
            except Exception :
                pass


        if self .welding_tool :
            from src .wield import WeldingTool 
            if not hasattr (self ,'_welding_tool_obj')or self ._welding_tool_obj is None :
                self ._welding_tool_obj =WeldingTool (self .welding_tool ['pos'],icon =self .welding_icon )
            self ._welding_tool_obj .pos =self .welding_tool ['pos']
            self ._welding_tool_obj .held =self .welding_tool ['held']
            self ._welding_tool_obj .update (npcs or [],self .bricks )

            if self .welding_tool ['held']:
                try :
                    self .welding_tool ['pos']=pygame .math .Vector2 (scaling .to_world (pygame .mouse .get_pos ()))
                except Exception :
                    self .welding_tool ['pos']=pygame .math .Vector2 (pygame .mouse .get_pos ())

            # Thruster effects: if any spawned bricks implement an apply_thrust
            # method (i.e. thrusters), call it so welded objects receive forces.
            try :
                if hasattr (self ,'_welding_tool_obj')and self ._welding_tool_obj is not None :
                    for b in list (self .bricks ):
                        try :
                            if hasattr (b ,'apply_thrust'):
                                b .apply_thrust (dt ,welding_tool =self ._welding_tool_obj ,npcs =npcs ,bricks =self .bricks )
                        except Exception :
                            pass
            except Exception :
                pass


        if self .pistol :
            try :
                from src .guns .pistol import Pistol 
                if not hasattr (self ,'_pistol_obj')or self ._pistol_obj is None :
                    self ._pistol_obj =Pistol (self .pistol ['pos'],icon =self .pistol_icon )
                self ._pistol_obj .pos =self .pistol ['pos']
                self ._pistol_obj .held =self .pistol ['held']

                try :
                    self ._pistol_obj .update (dt ,npcs or [],floor )
                except Exception :

                    self ._pistol_obj .update (dt )

                if self .pistol ['held']:
                    try :
                        self .pistol ['pos']=pygame .math .Vector2 (scaling .to_world (pygame .mouse .get_pos ()))
                    except Exception :
                        self .pistol ['pos']=pygame .math .Vector2 (pygame .mouse .get_pos ())
            except Exception :
                pass 


        if self .axe :
            try :
                from src .axe import Axe
                if not hasattr (self ,'_axe_obj')or self ._axe_obj is None :
                    self ._axe_obj =Axe (self .axe ['pos'],icon =self .axe_icon )
                self ._axe_obj .pos =self .axe ['pos']
                self ._axe_obj .held =self .axe ['held']
                try :
                    self ._axe_obj .update (npcs or [],self .bricks ,floor)
                except Exception :
                    try:
                        self ._axe_obj .update (npcs or [],self .bricks ,floor)
                    except Exception:
                        pass

                if self .axe ['held']:
                    try :
                        self .axe ['pos']=pygame .math .Vector2 (scaling .to_world (pygame .mouse .get_pos ()))
                    except Exception :
                        self .axe ['pos']=pygame .math .Vector2 (pygame .mouse .get_pos ())
            except Exception :
                pass 

        if self .dragging and self .target is not None :
            mpos =pygame .math .Vector2 (scaling .to_world (pygame .mouse .get_pos ()))
            desired =mpos +self .offset 
            ttype ,obj =self .target 

            if ttype =='brick':

                old_pos =obj .p .pos .copy ()
                old_vel =obj .p .pos -obj .p .prev 
                obj .p .pos =desired 

                obj .p .prev =obj .p .pos -(old_vel *0.2 )
            elif ttype == 'brick_group':
                # obj is a tuple (root, selected)
                try:
                    root, selected = obj
                except Exception:
                    root = obj
                    selected = obj

                old_pos = root.p.pos.copy()
                old_vel = root.p.pos - root.p.prev
                # move root so the selected brick will be under the cursor
                root.p.pos = desired
                root.p.prev = root.p.pos - (old_vel * 0.2)

                # propagate motion to descendants so the whole group moves
                try:
                    root_vel = root.p.pos - root.p.prev
                    # breadth-first propagate positions using welded_offset
                    queue = [root]
                    while queue:
                        parent = queue.pop(0)
                        for child in getattr(parent, 'welded_children', []):
                            # child's pos is parent.pos + its offset
                            child.p.pos = parent.p.pos + child.welded_offset
                            # give child same velocity as root for cohesiveness
                            child.p.prev = child.p.pos - root_vel
                            queue.append(child)
                except Exception:
                    pass
            else :


                try :
                    idx =2 
                    center =obj .particles [idx ].pos 
                except Exception :
                    idx =0 
                    center =obj .particles [0 ].pos 
                delta =desired -center 
                for p in obj .particles :
                    p .pos +=delta 

    def draw (self ,surf ):

        for b in self .bricks :
            b .draw (surf )

        if self .welding_tool :
            if not hasattr (self ,'_welding_tool_obj')or self ._welding_tool_obj is None :
                from src .wield import WeldingTool 
                self ._welding_tool_obj =WeldingTool (self .welding_tool ['pos'],icon =self .welding_icon )
            self ._welding_tool_obj .pos =self .welding_tool ['pos']
            self ._welding_tool_obj .held =self .welding_tool ['held']
            self ._welding_tool_obj .draw (surf )

        if self .pistol :
            if not hasattr (self ,'_pistol_obj')or self ._pistol_obj is None :
                try :
                    from src .guns .pistol import Pistol 
                    self ._pistol_obj =Pistol (self .pistol ['pos'],icon =self .pistol_icon )
                except Exception :
                    self ._pistol_obj =None 
            if self ._pistol_obj is not None :
                self ._pistol_obj .pos =self .pistol ['pos']
                self ._pistol_obj .held =self .pistol ['held']
                self ._pistol_obj .draw (surf )

        if self .axe :
            if not hasattr (self ,'_axe_obj')or self ._axe_obj is None :
                try :
                    from src .axe import Axe 
                    self ._axe_obj =Axe (self .axe ['pos'],icon =self .axe_icon )
                except Exception :
                    self ._axe_obj =None 
            if self ._axe_obj is not None :
                self ._axe_obj .pos =self .axe ['pos']
                self ._axe_obj .held =self .axe ['held']
                self ._axe_obj .draw (surf )

        m =pygame .mouse .get_pos ()


        if self .menu_open :
            try :
                sw ,sh =surf .get_size ()
            except Exception :
                sw ,sh =800 ,600 

            items =['Brick','Wielding Tool','Pistol','Axe','Thruster','NPC']

            menu_w =max (300 ,int (sw *0.75 ))
            menu_h =max (200 ,int (sh *0.6 ))

            menu_w =min (menu_w ,sw -80 )
            menu_h =min (menu_h ,sh -120 )
            menu_x =(sw -menu_w )//2 
            menu_y =(sh -menu_h )//2 

            menu_rect =pygame .Rect (menu_x ,menu_y ,menu_w ,menu_h )
            pygame .draw .rect (surf ,(20 ,20 ,20 ),menu_rect )
            pygame .draw .rect (surf ,(200 ,200 ,200 ),menu_rect ,2 )


            try :
                font =pygame .font .SysFont ('Arial',max (18 ,scaling .to_screen_length (20 )))
                header =font .render ('Select Item to Spawn',True ,(240 ,240 ,240 ))
                surf .blit (header ,(menu_x +24 ,menu_y +12 ))
            except Exception :
                pass 


            item_h =int ((menu_h -80 )/max (1 ,len (items )))
            for i ,name in enumerate (items ):
                r =pygame .Rect (menu_x +24 ,menu_y +48 +i *item_h ,menu_w -48 ,item_h -8 )
                pygame .draw .rect (surf ,(40 ,40 ,40 ),r )
                pygame .draw .rect (surf ,(120 ,120 ,120 ),r ,1 )


                preview_size =min (120 ,r .height -12 ,int (menu_w *0.25 ))
                preview_rect =pygame .Rect (r .x +12 ,r .y +(r .height -preview_size )//2 ,preview_size ,preview_size )
                if name =='Wielding Tool'and self .welding_icon is not None :
                    surf .blit (pygame .transform .scale (self .welding_icon ,(preview_size ,preview_size )),preview_rect )
                elif name =='Pistol'and self .pistol_icon is not None :
                    surf .blit (pygame .transform .scale (self .pistol_icon ,(preview_size ,preview_size )),preview_rect )
                elif name == 'Axe' and self .axe_icon is not None :
                    surf .blit (pygame .transform .scale (self .axe_icon ,(preview_size ,preview_size )),preview_rect )
                elif name =='Thruster'and self .thruster_icon is not None :
                    surf .blit (pygame .transform .scale (self .thruster_icon ,(preview_size ,preview_size )),preview_rect )
                elif name =='NPC':
                    # draw a simple humanoid preview (head + torso)
                    cx = preview_rect.centerx
                    cy = preview_rect.centery
                    head_r = max(2, int(preview_size * 0.18))
                    torso_w = max(4, int(preview_size * 0.32))
                    torso_h = max(6, int(preview_size * 0.38))
                    head_center = (cx, cy - head_r)
                    torso_rect = pygame.Rect(0,0,torso_w,torso_h)
                    torso_rect.center = (cx, cy + torso_h//6)
                    pygame.draw.circle(surf, (16,40,18), head_center, head_r)
                    pygame.draw.circle(surf, (54,160,60), head_center, max(1, head_r-2))
                    pygame.draw.rect(surf, (16,40,18), torso_rect)
                    inner = torso_rect.inflate(-max(2, scaling.to_screen_length(1)), -max(2, scaling.to_screen_length(1)))
                    pygame.draw.rect(surf, (54,160,60), inner)
                else :
                    pygame .draw .rect (surf ,(30 ,10 ,10 ),preview_rect )
                    inner =preview_rect .inflate (-max (3 ,scaling .to_screen_length (4 )),-max (3 ,scaling .to_screen_length (4 )))
                    pygame .draw .rect (surf ,(180 ,30 ,30 ),inner )


                try :
                    font =pygame .font .SysFont ('Arial',max (18 ,scaling .to_screen_length (18 )))
                    txt =font .render (name ,True ,(230 ,230 ,230 ))
                    surf .blit (txt ,(preview_rect .right +16 ,r .y +(r .height -txt .get_height ())//2 ))
                except Exception :
                    pass 


            try :
                font =pygame .font .SysFont ('Arial',max (12 ,scaling .to_screen_length (14 )))
                hint =font .render ('Left-click to select. After selection: Right-click to spawn repeatedly. Q/Esc to close.',True ,(190 ,190 ,190 ))
                surf .blit (hint ,(menu_x +24 ,menu_y +menu_h -28 ))
            except Exception :
                pass 

            return 


        if not self .equipped :
            for b in self .bricks :
                b .draw (surf )
            return 


        if self .icon is not None :
            w ,h =self .icon .get_size ()
            surf .blit (self .icon ,(m [0 ]-w //2 ,m [1 ]-h //2 ))
        else :
            pygame .draw .circle (surf ,(220 ,200 ,20 ),m ,10 )


        menu_rect =pygame .Rect (m [0 ]+16 ,m [1 ]-self .menu_h //2 ,self .menu_w ,self .menu_h )
        pygame .draw .rect (surf ,(30 ,30 ,30 ),menu_rect )
        pygame .draw .rect (surf ,(200 ,200 ,200 ),menu_rect ,1 )


        icon_rect =pygame .Rect (menu_rect .x +8 ,menu_rect .y +6 ,28 ,28 )
        pygame .draw .rect (surf ,(150 ,40 ,40 ),icon_rect )
        pygame .draw .rect (surf ,(20 ,10 ,10 ),icon_rect ,1 )


        try :
            font =pygame .font .SysFont ('Arial',max (10 ,scaling .to_screen_length (12 )))
            txt =font .render ('Brick',True ,(220 ,220 ,220 ))
            surf .blit (txt ,(icon_rect .right +8 ,menu_rect .y +8 ))
        except Exception :
            pass 



        if self .menu_selected is not None :
            try :

                ps =14 
                pr =pygame .Rect (m [0 ]+16 ,m [1 ]-self .menu_h //2 -ps -8 ,ps ,ps )
                if self .menu_selected =='Pistol'and self .pistol_icon is not None :
                    try :
                        img =pygame .transform .scale (self .pistol_icon ,(ps ,ps ))
                        surf .blit (img ,(pr .x ,pr .y ))
                    except Exception :
                        pygame .draw .rect (surf ,(30 ,10 ,10 ),pr )
                        inner =pr .inflate (-2 ,-2 )
                        pygame .draw .rect (surf ,(180 ,30 ,30 ),inner )
                elif self .menu_selected =='Axe' and self .axe_icon is not None :
                    try :
                        img =pygame .transform .scale (self .axe_icon ,(ps ,ps ))
                        surf .blit (img ,(pr .x ,pr .y ))
                    except Exception :
                        pygame .draw .rect (surf ,(30 ,10 ,10 ),pr )
                        inner =pr .inflate (-2 ,-2 )
                        pygame .draw .rect (surf ,(180 ,30 ,30 ),inner )
                elif self .menu_selected == 'NPC':
                    try:
                        # draw small humanoid icon in the selection box
                        cx = pr.centerx
                        cy = pr.centery
                        head_r = max(2, ps//3)
                        head_center = (cx, cy - head_r//2)
                        pygame.draw.circle(surf, (16,40,18), head_center, head_r)
                        pygame.draw.circle(surf, (54,160,60), head_center, max(1, head_r-1))
                        torso = pr.inflate(-ps//4, -ps//4)
                        torso.centery = cy + head_r//2
                        pygame.draw.rect(surf, (16,40,18), torso)
                        inner = torso.inflate(-1, -1)
                        pygame.draw.rect(surf, (54,160,60), inner)
                    except Exception:
                        pygame .draw .rect (surf ,(30 ,10 ,10 ),pr )
                        inner =pr .inflate (-2 ,-2 )
                        pygame .draw .rect (surf ,(180 ,30 ,30 ),inner )
                elif self .menu_selected == 'Thruster' and self .thruster_icon is not None :
                    try :
                        img =pygame .transform .scale (self .thruster_icon ,(ps ,ps ))
                        surf .blit (img ,(pr .x ,pr .y ))
                    except Exception :
                        pygame .draw .rect (surf ,(30 ,10 ,10 ),pr )
                        inner =pr .inflate (-2 ,-2 )
                        pygame .draw .rect (surf ,(180 ,30 ,30 ),inner )
                else :
                    pygame .draw .rect (surf ,(30 ,10 ,10 ),pr )
                    inner =pr .inflate (-2 ,-2 )
                    pygame .draw .rect (surf ,(180 ,30 ,30 ),inner )
            except Exception :
                pass 
