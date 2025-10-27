import pygame 
from src import scaling 


class WeldingTool :
    def __init__ (self ,pos ,icon =None ):

        self .pos =pygame .math .Vector2 (pos )
        self .held =False 
        self .icon =icon 

        self .radius =36 
        self .welded =[]

        self .joints =[]
        self ._last_weld_target =None 
        self .weld_groups ={}
        self .current_group =None 
        self .max_group_size =100 

    def draw (self ,surf ):

        center =scaling .to_screen_vec (self .pos )
        if self .icon :

            ps =max (24 ,scaling .to_screen_length (36 ))
            try :
                img =pygame .transform .scale (self .icon ,(ps ,ps ))
                surf .blit (img ,(int (center .x -ps //2 ),int (center .y -ps //2 )))
                return 
            except Exception :
                pass 


        r =max (6 ,int (scaling .to_screen_length (self .radius )))
        pygame .draw .circle (surf ,(220 ,220 ,40 ),(int (center .x ),int (center .y )),r )
        pygame .draw .circle (surf ,(80 ,80 ,20 ),(int (center .x ),int (center .y )),r ,2 )

    def update (self ,npcs ,bricks ):

        if self .held :
            try :
                self .pos =pygame .math .Vector2 (scaling .to_world (pygame .mouse .get_pos ()))
            except Exception :

                self .pos =pygame .math .Vector2 (pygame .mouse .get_pos ())


        touched_this_frame =[]


        if self .held :
            for npc in npcs :
                for i ,p in enumerate (getattr (npc ,'particles',[])):
                    try :
                        if (p .pos -self .pos ).length ()<self .radius :


                            entry =(npc ,'npc',i )
                            if entry not in self .welded :
                                self .welded .append (entry )
                                touched_this_frame .append ((npc ,p .pos .copy (),i ))
                    except Exception :
                        continue 
            for b in bricks :
                try :
                    if (b .p .pos -self .pos ).length ()<self .radius :
                        entry =(b ,'brick',None )
                        if entry not in self .welded :
                            self .welded .append (entry )
                            touched_this_frame .append ((b ,b .p .pos .copy (),None ))
                except Exception :
                    continue 


            if len (touched_this_frame )>1 :

                for i in range (len (touched_this_frame )):
                    for j in range (i +1 ,len (touched_this_frame )):
                        obj1 ,pos1 ,idx1 =touched_this_frame [i ]
                        obj2 ,pos2 ,idx2 =touched_this_frame [j ]


                        dist =(pos2 -pos1 ).length ()
                        if dist <self .radius *2 :
                            self .weld_effect (obj1 ,attach_particle =None ,attach_index =idx1 )
                            self ._last_weld_target =(obj1 ,getattr (obj1 ,'__class__',None ),idx1 )
                            self .weld_effect (obj2 ,attach_particle =None ,attach_index =idx2 )

            elif len (touched_this_frame )==1 :
                obj ,_ ,idx =touched_this_frame [0 ]
                self .weld_effect (obj ,attach_particle =None ,attach_index =idx )


        try :
            self .enforce_joints ()
        except Exception :
            pass 

    def weld_effect (self ,target ,attach_particle =None ,attach_index =None ):

        if hasattr (target ,'color'):
            target .color =(255 ,220 ,40 )





        try :
            tool_pos =getattr (self ,'pos',None )
            if tool_pos is None :
                return 


            if hasattr (target ,'p')and hasattr (target .p ,'pos'):
                diff =target .p .pos -tool_pos 
                dist =diff .length ()if diff .length ()!=0 else 0.001 
                norm =diff /dist 

                sep =max (4.0 ,self .radius *0.25 )
                delta =norm *sep 

                target .p .pos +=delta 
                try :
                    target .p .prev +=delta *0.5 
                except Exception :
                    pass 


            elif hasattr (target ,'particles'):

                pts =[getattr (p ,'pos',None )for p in target .particles ]
                pts =[p for p in pts if p is not None ]
                if not pts :
                    return 
                center =sum (pts ,pygame .math .Vector2 (0 ,0 ))/len (pts )
                diff =center -tool_pos 
                dist =diff .length ()if diff .length ()!=0 else 0.001 
                norm =diff /dist 
                sep =max (4.0 ,self .radius *0.25 )
                delta =norm *sep 
                for p in target .particles :
                    try :
                        p .pos +=delta 
                        p .prev +=delta *0.5 
                    except Exception :
                        continue 
        except Exception :

            pass 


        def get_attach_pos (obj ,attach_idx ):
            if attach_idx is None :
                if hasattr (obj ,'p'):
                    return obj .p .pos .copy ()
                elif hasattr (obj ,'particles'):
                    pts =[getattr (p ,'pos',None )for p in obj .particles ]
                    pts =[p for p in pts if p is not None ]
                    if not pts :
                        return None 
                    return sum (pts ,pygame .math .Vector2 (0 ,0 ))/len (pts )
                else :
                    return None 
            else :
                try :
                    return obj .particles [attach_idx ].pos .copy ()
                except Exception :
                    return None 


        try :

            target_group =None 
            for group_id ,objects in self .weld_groups .items ():
                if target in objects :
                    target_group =group_id 
                    break 


            if target_group is None and self ._last_weld_target is not None :
                last =self ._last_weld_target [0 ]
                last_group =None 
                for group_id ,objects in self .weld_groups .items ():
                    if last in objects :
                        last_group =group_id 
                        break 


                pa =get_attach_pos (last ,self ._last_weld_target [2 ]if len (self ._last_weld_target )>2 else None )
                pb =get_attach_pos (target ,attach_index )

                if pa is not None and pb is not None :
                    dist =(pb -pa ).length ()
                    if dist <self .radius *2 :

                        if last_group is not None :

                            if len (self .weld_groups [last_group ])<self .max_group_size :
                                self .weld_groups [last_group ].add (target )
                                target_group =last_group 

                        else :
                            new_group =len (self .weld_groups )
                            self .weld_groups [new_group ]={last ,target }
                            target_group =new_group 


                        exists =False 
                        for j in self .joints :
                            if (j ['a']is last and j ['b']is target )or (j ['a']is target and j ['b']is last ):
                                exists =True 
                                break 
                        if not exists :
                            offset =pb -pa 
                            self .joints .append ({
                            'a':last ,
                            'b':target ,
                            'a_attach':self ._last_weld_target [2 ]if len (self ._last_weld_target )>2 else None ,
                            'b_attach':attach_index ,
                            'offset':offset ,
                            'group':target_group 
                            })


            elif target_group is not None :

                pb =get_attach_pos (target ,attach_index )
                if pb is not None :
                    for other_target ,_ ,other_attach in self .welded :
                        if other_target is target :
                            continue 


                        other_group =None 
                        for group_id ,objects in self .weld_groups .items ():
                            if other_target in objects :
                                other_group =group_id 
                                break 
                        if other_group ==target_group :
                            continue 

                        pa =get_attach_pos (other_target ,other_attach )
                        if pa is not None :
                            dist =(pb -pa ).length ()
                            if dist <self .radius *2 :

                                if other_group is not None :
                                    total_size =len (self .weld_groups [target_group ])+len (self .weld_groups [other_group ])
                                    if total_size <=self .max_group_size :

                                        self .weld_groups [target_group ].update (self .weld_groups [other_group ])
                                        del self .weld_groups [other_group ]

                                        for j in self .joints :
                                            if j ['group']==other_group :
                                                j ['group']=target_group 
                                else :

                                    if len (self .weld_groups [target_group ])<self .max_group_size :
                                        self .weld_groups [target_group ].add (other_target )


                                exists =False 
                                for j in self .joints :
                                    if (j ['a']is target and j ['b']is other_target )or (j ['a']is other_target and j ['b']is target ):
                                        exists =True 
                                        break 
                                if not exists :
                                    offset =pa -pb 
                                    self .joints .append ({
                                    'a':target ,
                                    'b':other_target ,
                                    'a_attach':attach_index ,
                                    'b_attach':other_attach ,
                                    'offset':offset ,
                                    'group':target_group 
                                    })


            self ._last_weld_target =(target ,getattr (target ,'__class__',None ),attach_index )
        except Exception :
            pass 

    def enforce_joints (self ):

        try :
            for j in self .joints :
                a =j ['a']
                b =j ['b']
                offset =j ['offset']

                def get_pos (t ,attach_idx =None ):

                    if attach_idx is not None :
                        try :
                            return t .particles [attach_idx ].pos 
                        except Exception :
                            pass 
                    if hasattr (t ,'p'):
                        return t .p .pos 
                    elif hasattr (t ,'particles'):
                        pts =[getattr (p ,'pos',None )for p in t .particles ]
                        pts =[p for p in pts if p is not None ]
                        if not pts :
                            return None 
                        return sum (pts ,pygame .math .Vector2 (0 ,0 ))/len (pts )
                    else :
                        return None 

                def move_by (t ,delta ):
                    if hasattr (t ,'p'):
                        try :
                            t .p .pos +=delta 
                            t .p .prev +=delta *0.5 
                        except Exception :
                            pass 
                    elif hasattr (t ,'particles'):
                        for p in t .particles :
                            try :
                                p .pos +=delta 
                                p .prev +=delta *0.5 
                            except Exception :
                                continue 

                pa =get_pos (a ,j .get ('a_attach'))
                pb =get_pos (b ,j .get ('b_attach'))
                if pa is None or pb is None :
                    continue 

                desired_pb =pa +offset 
                correction =desired_pb -pb 


                a_is_npc =hasattr (a ,'particles')
                b_is_npc =hasattr (b ,'particles')

                if a_is_npc and not b_is_npc :

                    move_by (b ,correction )
                elif b_is_npc and not a_is_npc :

                    move_by (a ,-correction )
                else :

                    half =correction *0.5 
                    move_by (a ,-half )
                    move_by (b ,half )
        except Exception :
            pass 
