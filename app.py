import sys 
import pygame 
from src .background import Background 
from src .baseplate import Baseplate 
from src .npc import NPC 
from src .fiddle import Fiddle 
from src import scaling 
from src .makersgun import MakersGun, Brick
from src.thruster import Thruster
from src.menu import Menu
from src.worldman import get_world_manager
import rpc


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
    # Main menu shown on startup
    menu =Menu (DESIGN_W ,DESIGN_H )
    fiddle =Fiddle ()
    makersgun =MakersGun ()


    # Start with a single NPC by default (will be replaced if a world is loaded)
    npcs =[NPC (300 ,360 )]
    world_applied = False
    # track last presence state to avoid spamming updates
    presence_state = None

    running =True 
    paused =False 

    # Start Discord RPC (safe no-op if dependency missing)
    try:
        rpc.start()
    except Exception:
        pass

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


            # If the main menu is active, let it handle input first.
            if menu .active :
                consumed =menu .handle_event (event )
                if consumed :
                    continue

            # Default ordering: let MakersGun handle the event first (spawn/menu
            # logic and object dragging). If it doesn't consume the event, allow
            # the Fiddle (direct NPC particle dragging) to handle it.
            consumed =makersgun .handle_event (event ,npcs )
            if not consumed :
                fiddle .handle_event (event ,npcs )

        if menu .active :
            menu .update (dt )
        else :
            # If the menu requested start (world loaded), initialize runtime NPCs
            if menu.start_requested and not world_applied:
                try:
                    mgr = get_world_manager()
                    if getattr(mgr, 'current_data', None) and isinstance(mgr.current_data, dict):
                        raw = mgr.current_data.get('npcs', None)
                        if isinstance(raw, list):
                            new_npcs = []
                            for ent in raw:
                                try:
                                    if isinstance(ent, dict) and 'x' in ent and 'y' in ent:
                                        new_npcs.append(NPC(float(ent['x']), float(ent['y'])))
                                    elif isinstance(ent, (list, tuple)) and len(ent) >= 2:
                                        new_npcs.append(NPC(float(ent[0]), float(ent[1])))
                                except Exception:
                                    continue
                            # use world NPCs even if empty list explicitly provided
                            npcs = new_npcs
                        # Load saved bricks into the makersgun so the world visually restores
                        try:
                            raw_bricks = mgr.current_data.get('bricks', None)
                            if isinstance(raw_bricks, list):
                                # clear existing runtime bricks and recreate from saved data
                                makersgun.bricks.clear()
                                for ent in raw_bricks:
                                    try:
                                        if not isinstance(ent, dict):
                                            continue
                                        t = ent.get('type', 'brick')
                                        x = float(ent.get('x', 0))
                                        y = float(ent.get('y', 0))
                                        size = int(ent.get('size', 40))
                                        if t == 'thruster':
                                            try:
                                                thr = Thruster((x, y), icon=makersgun.thruster_icon)
                                                makersgun.bricks.append(thr)
                                            except Exception:
                                                # fallback: create simple Brick if Thruster fails
                                                makersgun.bricks.append(Brick((x, y), size=size))
                                        elif t == 'bike':
                                            try:
                                                from src.vehicles.bike import Bike
                                                b = Bike((x, y), size=size)
                                                makersgun.bricks.append(b)
                                            except Exception:
                                                makersgun.bricks.append(Brick((x, y), size=size))
                                        elif t == 'car':
                                            try:
                                                from src.vehicles.car import Car
                                                c = Car((x, y), size=size)
                                                makersgun.bricks.append(c)
                                            except Exception:
                                                makersgun.bricks.append(Brick((x, y), size=size))
                                        else:
                                            makersgun.bricks.append(Brick((x, y), size=size))
                                    except Exception:
                                        continue
                        except Exception:
                            pass
                except Exception:
                    pass
                world_applied = True
            if not paused :
                bg .update (dt )
                for npc in npcs :

                    npc .update (dt ,floor_y =base )
                fiddle .update (dt )
                makersgun .update (dt ,npcs =npcs ,floor =base )

                # Global drive input: if a possessed NPC is mounted on a bike,
                # route A/D input to that bike so the player can drive it.
                try:
                    keys = pygame.key.get_pressed()
                    vx = 0.0
                    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                        vx -= 220.0
                    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                        vx += 220.0

                    if vx != 0.0:
                        # Collect bikes that currently have riders mounted
                        mounted_bikes = [b for b in makersgun.bricks if getattr(b, 'rider', None) is not None]

                        # Prefer bikes whose rider has been explicitly possessed
                        controlled = [n for n in npcs if getattr(n, 'possessed_controlled', False)]
                        targets = []
                        if controlled:
                            targets = [b for b in mounted_bikes if b.rider in controlled]

                        # If no possessed-controlled rider, and there's exactly one
                        # mounted bike, drive that one (common single-player case).
                        if not targets:
                            if len(mounted_bikes) == 1:
                                targets = mounted_bikes
                            else:
                                # Fallback: if there is exactly one NPC and it's mounted,
                                # drive that NPC's bike.
                                if len(npcs) == 1:
                                    r = npcs[0]
                                    mb = getattr(r, 'mounted_bike', None)
                                    if mb is not None:
                                        targets = [mb]

                        for b in targets:
                            try:
                                if hasattr(b, 'drive'):
                                    b.drive(vx, dt)
                                else:
                                    b.p.prev.x = b.p.pos.x - vx * dt
                            except Exception:
                                pass
                except Exception:
                    pass


        # Update presence on transitions (menu <-> game). We only change the
        # RPC state when the logical state changes to avoid spamming updates.
        try:
            if menu .active :
                if presence_state != 'menu':
                    rpc.set_menu()
                    presence_state = 'menu'
            else :
                if presence_state != 'game':
                    # Game mode unknown in this codepath; assume singleplayer
                    rpc.set_game('singleplayer')
                    presence_state = 'game'
        except Exception:
            # presence errors are non-fatal
            pass

        # If menu active, draw it (it includes a background). Otherwise draw
        # the normal game scene.
        if menu .active :
            menu .draw (screen )
        else :
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

    # Before quitting, persist runtime NPCs back into the loaded world (if any)
    try:
        mgr = get_world_manager()
        if getattr(mgr, 'current_name', None) and getattr(mgr, 'current_data', None) is not None:
            # Serialize NPCs as simple {'x':..., 'y':...} entries using torso center (particle 2)
            serialized = []
            for npc in npcs:
                try:
                    center = npc.particles[2].pos
                    serialized.append({"x": float(center.x), "y": float(center.y)})
                except Exception:
                    try:
                        # fallback: use particle 0
                        center = npc.particles[0].pos
                        serialized.append({"x": float(center.x), "y": float(center.y)})
                    except Exception:
                        continue
            mgr.set_field('npcs', serialized)
            mgr.save_now()
    except Exception:
        pass

    # Shutdown rpc cleanly if available
    try:
        rpc.shutdown()
    except Exception:
        pass

    pygame .quit ()


if __name__ =='__main__':
    try :
        main ()
    except Exception :
        pygame .quit ()
        raise
import sys 
import pygame 
from src .background import Background 
from src .baseplate import Baseplate 
from src .npc import NPC 
from src .fiddle import Fiddle 
from src import scaling 
from src .makersgun import MakersGun, Brick
from src.thruster import Thruster
from src.menu import Menu
from src.worldman import get_world_manager


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
    # Main menu shown on startup
    menu =Menu (DESIGN_W ,DESIGN_H )
    fiddle =Fiddle ()
    makersgun =MakersGun ()


    # Start with a single NPC by default (will be replaced if a world is loaded)
    npcs =[NPC (300 ,360 )]
    world_applied = False

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


            # If the main menu is active, let it handle input first.
            if menu .active :
                consumed =menu .handle_event (event )
                if consumed :
                    continue

            # Default ordering: let MakersGun handle the event first (spawn/menu
            # logic and object dragging). If it doesn't consume the event, allow
            # the Fiddle (direct NPC particle dragging) to handle it.
            consumed =makersgun .handle_event (event ,npcs )
            if not consumed :
                fiddle .handle_event (event ,npcs )

        if menu .active :
            menu .update (dt )
        else :
            # If the menu requested start (world loaded), initialize runtime NPCs
            if menu.start_requested and not world_applied:
                try:
                    mgr = get_world_manager()
                    if getattr(mgr, 'current_data', None) and isinstance(mgr.current_data, dict):
                        raw = mgr.current_data.get('npcs', None)
                        if isinstance(raw, list):
                            new_npcs = []
                            for ent in raw:
                                try:
                                    if isinstance(ent, dict) and 'x' in ent and 'y' in ent:
                                        new_npcs.append(NPC(float(ent['x']), float(ent['y'])))
                                    elif isinstance(ent, (list, tuple)) and len(ent) >= 2:
                                        new_npcs.append(NPC(float(ent[0]), float(ent[1])))
                                except Exception:
                                    continue
                            # use world NPCs even if empty list explicitly provided
                            npcs = new_npcs
                        # Load saved bricks into the makersgun so the world visually restores
                        try:
                            raw_bricks = mgr.current_data.get('bricks', None)
                            if isinstance(raw_bricks, list):
                                # clear existing runtime bricks and recreate from saved data
                                makersgun.bricks.clear()
                                for ent in raw_bricks:
                                    try:
                                        if not isinstance(ent, dict):
                                            continue
                                        t = ent.get('type', 'brick')
                                        x = float(ent.get('x', 0))
                                        y = float(ent.get('y', 0))
                                        size = int(ent.get('size', 40))
                                        if t == 'thruster':
                                            try:
                                                thr = Thruster((x, y), icon=makersgun.thruster_icon)
                                                makersgun.bricks.append(thr)
                                            except Exception:
                                                # fallback: create simple Brick if Thruster fails
                                                makersgun.bricks.append(Brick((x, y), size=size))
                                        elif t == 'bike':
                                            try:
                                                from src.vehicles.bike import Bike
                                                b = Bike((x, y), size=size)
                                                makersgun.bricks.append(b)
                                            except Exception:
                                                makersgun.bricks.append(Brick((x, y), size=size))
                                        else:
                                            makersgun.bricks.append(Brick((x, y), size=size))
                                    except Exception:
                                        continue
                        except Exception:
                            pass
                except Exception:
                    pass
                world_applied = True
            if not paused :
                bg .update (dt )
                for npc in npcs :

                    npc .update (dt ,floor_y =base )
                fiddle .update (dt )
                makersgun .update (dt ,npcs =npcs ,floor =base )


        # If menu active, draw it (it includes a background). Otherwise draw
        # the normal game scene.
        if menu .active :
            menu .draw (screen )
        else :
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

    # Before quitting, persist runtime NPCs back into the loaded world (if any)
    try:
        mgr = get_world_manager()
        if getattr(mgr, 'current_name', None) and getattr(mgr, 'current_data', None) is not None:
            # Serialize NPCs as simple {'x':..., 'y':...} entries using torso center (particle 2)
            serialized = []
            for npc in npcs:
                try:
                    center = npc.particles[2].pos
                    serialized.append({"x": float(center.x), "y": float(center.y)})
                except Exception:
                    try:
                        # fallback: use particle 0
                        center = npc.particles[0].pos
                        serialized.append({"x": float(center.x), "y": float(center.y)})
                    except Exception:
                        continue
            mgr.set_field('npcs', serialized)
            mgr.save_now()
    except Exception:
        pass

    pygame .quit ()


if __name__ =='__main__':
    try :
        main ()
    except Exception :
        pygame .quit ()
        raise 