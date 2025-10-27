from typing import Tuple 
try :
    import pygame 
    Vector2 =pygame .math .Vector2 
except Exception :

    Vector2 =tuple 


DESIGN_W =960 
DESIGN_H =640 


_scale =1.0 
_offset_x =0.0 
_offset_y =0.0 
_design_w =DESIGN_W 
_design_h =DESIGN_H 

def init (actual_w :int ,actual_h :int ,design_w :int =DESIGN_W ,design_h :int =DESIGN_H ):
    global _scale ,_offset_x ,_offset_y ,_design_w ,_design_h 
    _design_w =design_w 
    _design_h =design_h 
    sx =actual_w /float (design_w )
    sy =actual_h /float (design_h )

    _scale =min (sx ,sy )
    scaled_w =design_w *_scale 
    scaled_h =design_h *_scale 
    _offset_x =(actual_w -scaled_w )/2.0 
    _offset_y =(actual_h -scaled_h )/2.0 

def get_scale ()->float :
    return _scale 

def get_offset ()->Tuple [float ,float ]:
    return (_offset_x ,_offset_y )

def to_screen (pos )->Tuple [int ,int ]:
    x ,y =pos 
    sx =int (round (x *_scale +_offset_x ))
    sy =int (round (y *_scale +_offset_y ))
    return (sx ,sy )

def to_screen_vec (vec ):
    if Vector2 is tuple :
        return to_screen ((vec [0 ],vec [1 ]))
    v =Vector2 (vec )
    sx =v .x *_scale +_offset_x 
    sy =v .y *_scale +_offset_y 
    return Vector2 (sx ,sy )

def to_screen_length (length :float )->int :
    return int (round (length *_scale ))

def to_world (screen_pos )->Tuple [float ,float ]:
    sx ,sy =screen_pos 
    x =(sx -_offset_x )/_scale 
    y =(sy -_offset_y )/_scale 
    return (x ,y )

def to_world_vec (vec ):
    if Vector2 is tuple :
        return to_world ((vec [0 ],vec [1 ]))
    v =Vector2 (vec )
    x =(v .x -_offset_x )/_scale 
    y =(v .y -_offset_y )/_scale 
    return Vector2 (x ,y )
