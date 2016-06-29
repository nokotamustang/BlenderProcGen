bl_info = {
    "name": "Spaceship Generator",
    "author": "Michael Davies",
    "version": (1, 0, 0),
    "blender": (2, 76, 0),
    "location": "View3D > Add > Mesh",
    "description": "Procedurally generate 3D spaceships from a random seed.",
    "wiki_url": "https://github.com/a1studmuffin/SpaceshipGenerator/blob/master/README.md",
    "tracker_url": "https://github.com/a1studmuffin/SpaceshipGenerator/issues",
    "category": "Add Mesh"
}

if "bpy" in locals():
    # reload logic (magic)
    import importlib
    importlib.reload(spaceship_generator)
else:
    from add_mesh_SpaceshipGenerator import spaceship_generator

import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty
from bpy.types import Operator

StartCreation = False

class GenerateSpaceship(Operator):
    """Procedurally generate 3D spaceships from a random seed."""
    bl_idname = "mesh.generate_spaceship"
    bl_label = "Spaceship"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    random_seed = StringProperty (default='', name='Seed')
    x_segments  = BoolProperty(default=True, name='Create X Segments')
    y_segments  = BoolProperty(default=False, name='Create Y Segments')
    z_segments  = BoolProperty(default=False, name='Create Z Segments')
    num_hull_segments_min      = IntProperty (default=3, min=0, soft_max=16, name='Min. Hull Segments')
    num_hull_segments_max      = IntProperty (default=6, min=0, soft_max=16, name='Max. Hull Segments')
    create_asymmetry_segments  = BoolProperty(default=True, name='Create Asymmetry Segments')
    num_asymmetry_segments_min = IntProperty (default=1, min=1, soft_max=16, name='Min. Asymmetry Segments')
    num_asymmetry_segments_max = IntProperty (default=5, min=1, soft_max=16, name='Max. Asymmetry Segments')
    create_face_detail         = BoolProperty(default=True,  name='Create Face Detail')
    allow_horizontal_symmetry  = BoolProperty(default=True,  name='Allow Horizontal Symmetry')
    allow_vertical_symmetry    = BoolProperty(default=False, name='Allow Vertical Symmetry')
    apply_bevel_modifier       = BoolProperty(default=True,  name='Apply Bevel Modifier')
    assign_materials           = BoolProperty(default=True,  name='Assign Materials')
    reset_scene                = BoolProperty(default=False,  name='Reset')
    
    CreatedObject = None
    count = 0
    
    class OBJECT_OT_CreateSpaceShipButton(bpy.types.Operator):
        bl_idname = "spaceship.create"
        bl_label = "Create SpaceShip"
        
        def execute(self, context):
            global StartCreation
            StartCreation = True
            return{'FINISHED'}
            
    
    def draw(self, context):
        
        layout = self.layout
        box = layout.box()
        box.prop(self, 'random_seed')
        box.prop(self, 'x_segments')
        box.prop(self, 'y_segments')
        box.prop(self, 'z_segments')
        box.prop(self, 'num_hull_segments_min')
        box.prop(self, 'num_hull_segments_max')
        box.prop(self, 'create_asymmetry_segments')
        box.prop(self, 'num_asymmetry_segments_min')
        box.prop(self, 'num_asymmetry_segments_max')
        box.prop(self, 'create_face_detail')
        box.prop(self, 'allow_horizontal_symmetry')
        box.prop(self, 'allow_vertical_symmetry')
        box.prop(self, 'apply_bevel_modifier')
        box.prop(self, 'assign_materials')
        box.operator("spaceship.create", text='Create SpaceShip', icon='ACTION')
        box.prop(self, "reset_scene",text="Reset", icon='FILE_REFRESH')
    
    def reset_scene1(self, context):
        self.random_seed = ''
        self.x_segments  = True
        self.y_segments  = False
        self.z_segments  = False
        self.num_hull_segments_min      = 3
        self.num_hull_segments_max      = 6
        self.create_asymmetry_segments  = True
        self.num_asymmetry_segments_min = 1
        self.num_asymmetry_segments_max = 5
        self.create_face_detail         = True
        self.allow_horizontal_symmetry  = True
        self.allow_vertical_symmetry    = False
        self.apply_bevel_modifier       = True
        self.assign_materials           = True
        self.reset_scene                = False
        
        self.CreatedObject = spaceship_generator.generate_spaceship(
                self.random_seed,
                self.x_segments,
                self.y_segments,
                self.z_segments,
                self.num_hull_segments_min,
                self.num_hull_segments_max,
                self.create_asymmetry_segments,
                self.num_asymmetry_segments_min,
                self.num_asymmetry_segments_max,
                self.create_face_detail,
                self.allow_horizontal_symmetry,
                self.allow_vertical_symmetry,
                self.apply_bevel_modifier)
            
            
    def execute(self, context):
        global StartCreation
        if self.reset_scene == True:
            self.reset_scene1(context)
            return {'FINISHED'}
            
        if StartCreation:
            self.CreatedObject = spaceship_generator.generate_spaceship(
                self.random_seed,
                self.x_segments,
                self.y_segments,
                self.z_segments,
                self.num_hull_segments_min,
                self.num_hull_segments_max,
                self.create_asymmetry_segments,
                self.num_asymmetry_segments_min,
                self.num_asymmetry_segments_max,
                self.create_face_detail,
                self.allow_horizontal_symmetry,
                self.allow_vertical_symmetry,
                self.apply_bevel_modifier)
            
            StartCreation = False
            return {'FINISHED'}
        
        if self.count == 0:
            self.CreatedObject = spaceship_generator.generate_spaceship(
                self.random_seed,
                self.x_segments,
                self.y_segments,
                self.z_segments,
                self.num_hull_segments_min,
                self.num_hull_segments_max,
                self.create_asymmetry_segments,
                self.num_asymmetry_segments_min,
                self.num_asymmetry_segments_max,
                self.create_face_detail,
                self.allow_horizontal_symmetry,
                self.allow_vertical_symmetry,
                self.apply_bevel_modifier)
            self.count += 1
            return {'FINISHED'}
        else:
            return {'RUNNING_MODAL'}

def menu_func(self, context):
    self.layout.operator(GenerateSpaceship.bl_idname, text="Spaceship")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_mesh_add.append(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_mesh_add.remove(menu_func)

if __name__ == "__main__":
    register()
