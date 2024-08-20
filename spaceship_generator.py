# This is a Blender script that uses procedural generation to create
# textured 3D spaceship models. Tested with Blender 4.2.
# by Nokota Mustang
# https://github.com/nokotamustang/BlenderProcGen
# Forked from SpaceshipGenerator by Michael Davies

import os
import os.path
import bpy
import bmesh
from math import sqrt, radians
from mathutils import Vector, Matrix
from random import random, seed, uniform, randint, randrange
from enum import IntEnum
from colorsys import hls_to_rgb

DIR = os.path.dirname(os.path.abspath(__file__))


def resource_path(*path_components):
    return os.path.join(DIR, *path_components)


def reset_scene():
    '''Delete all existing spaceships and unused materials from the scene
    '''
    for item in bpy.data.objects:
        item.select = item.name.startswith('Spaceship')
    bpy.ops.object.delete()
    for material in bpy.data.materials:
        if not material.users:
            bpy.data.materials.remove(material)
    for texture in bpy.data.textures:
        if not texture.users:
            bpy.data.textures.remove(texture)


def extrude_face(bm, face, translate_forwards=0.0, extruded_face_list=None):
    '''Extrude a face along its normal by translate_forwards units.
    Args: 
        bm: bmesh object.
        face: face to extrude.
        translate_forwards: distance to extrude.
        extruded_face_list: list to append extruded faces to.
    Returns:
        new_face: the new face created by extrusion.
    '''
    new_faces = bmesh.ops.extrude_discrete_faces(bm, faces=[face])['faces']
    if extruded_face_list != None:
        extruded_face_list += new_faces[:]
    new_face = new_faces[0]
    bmesh.ops.translate(bm,
                        vec=new_face.normal * translate_forwards,
                        verts=new_face.verts)
    return new_face


def ribbed_extrude_face(bm, face, translate_forwards, num_ribs=3, rib_scale=0.9):
    '''Extrude a face along its normal by translate_forwards units, creating ribs.
    Args: 
        bm: bmesh object.
        face: face to extrude.
        translate_forwards: distance to extrude.
        num_ribs: number of ribs to create.
        rib_scale: scale of the ribs.
    Returns:
        new_face: the new face created by extrusion.
    '''
    translate_forwards_per_rib = translate_forwards / float(num_ribs)
    new_face = face
    for i in range(num_ribs):
        new_face = extrude_face(bm, new_face, translate_forwards_per_rib * 0.25)
        new_face = extrude_face(bm, new_face, 0.0)
        scale_face(bm, new_face, rib_scale, rib_scale, rib_scale)
        new_face = extrude_face(bm, new_face, translate_forwards_per_rib * 0.5)
        new_face = extrude_face(bm, new_face, 0.0)
        scale_face(bm, new_face, 1 / rib_scale, 1 / rib_scale, 1 / rib_scale)
        new_face = extrude_face(bm, new_face, translate_forwards_per_rib * 0.25)
    return new_face


def scale_face(bm, face, scale_x, scale_y, scale_z):
    '''Scale a face in local face space.'''
    face_space = get_face_matrix(face)
    face_space.invert()
    bmesh.ops.scale(bm,
                    vec=Vector((scale_x, scale_y, scale_z)),
                    space=face_space,
                    verts=face.verts)


def get_face_matrix(face, pos=None):
    '''Get a 4x4 matrix representing the orientation of a face.
    Args:
        face: face to get matrix for.
        pos: optional position override.
    Returns:
        mat: 4x4 matrix.
    '''
    x_axis = (face.verts[1].co - face.verts[0].co).normalized()
    z_axis = -face.normal
    y_axis = z_axis.cross(x_axis)
    if not pos:
        pos = face.calc_center_bounds()

    # Construct a 4x4 matrix from axes + position:
    # http://i.stack.imgur.com/3TnQP.png
    mat = Matrix()
    mat[0][0] = x_axis.x
    mat[1][0] = x_axis.y
    mat[2][0] = x_axis.z
    mat[3][0] = 0
    mat[0][1] = y_axis.x
    mat[1][1] = y_axis.y
    mat[2][1] = y_axis.z
    mat[3][1] = 0
    mat[0][2] = z_axis.x
    mat[1][2] = z_axis.y
    mat[2][2] = z_axis.z
    mat[3][2] = 0
    mat[0][3] = pos.x
    mat[1][3] = pos.y
    mat[2][3] = pos.z
    mat[3][3] = 1
    return mat


def get_face_width_and_height(face):
    '''Get the rough width and height of a quad face.
    Args:
        face: face to measure.
    Returns:
        width: width of the face.
        height: height of the face.
    '''
    if not face.is_valid or len(face.verts[:]) < 4:
        return -1, -1
    width = (face.verts[0].co - face.verts[1].co).length
    height = (face.verts[2].co - face.verts[1].co).length
    return width, height


def get_aspect_ratio(face):
    '''Get the aspect ratio of a face.'''
    if not face.is_valid:
        return 1.0
    face_aspect_ratio = max(0.01, face.edges[0].calc_length() / face.edges[1].calc_length())
    if face_aspect_ratio < 1.0:
        face_aspect_ratio = 1.0 / face_aspect_ratio
    return face_aspect_ratio


def is_rear_face(face):
    '''Returns true if this face is pointing behind the ship.
    Args:
        face: face to check.
    '''
    return face.normal.x < -0.95


def add_exhaust_to_face(bm, face):
    '''Add an exhaust shape to a face.
    Args:
        bm: bmesh object.
        face: face to add exhaust to.
    '''
    if not face.is_valid:
        return

    # The more square the face is, the more grid divisions it might have
    num_cuts = randint(1, int(4 - get_aspect_ratio(face)))
    result = bmesh.ops.subdivide_edges(bm,
                                       edges=face.edges[:],
                                       cuts=num_cuts,
                                       fractal=0.02,
                                       use_grid_fill=True)

    exhaust_length = uniform(0.1, 0.2)
    scale_outer = 1 / uniform(1.3, 1.6)
    scale_inner = 1 / uniform(1.05, 1.1)
    for face in result['geom']:
        if isinstance(face, bmesh.types.BMFace):
            if is_rear_face(face):
                face.material_index = Material.hull_dark
                face = extrude_face(bm, face, exhaust_length)
                scale_face(bm, face, scale_outer, scale_outer, scale_outer)
                extruded_face_list = []
                face = extrude_face(bm, face, -exhaust_length * 0.9, extruded_face_list)
                for extruded_face in extruded_face_list:
                    extruded_face.material_index = Material.exhaust_burn
                scale_face(bm, face, scale_inner, scale_inner, scale_inner)


def add_grid_to_face(bm, face):
    '''Add a grid pattern to a face.
    Args:    
        bm: bmesh object.
        face: face to add grid to.
    '''
    if not face.is_valid:
        return
    result = bmesh.ops.subdivide_edges(bm,
                                       edges=face.edges[:],
                                       cuts=randint(2, 4),
                                       fractal=0.02,
                                       use_grid_fill=True,
                                       use_single_edge=False)
    grid_length = uniform(0.025, 0.15)
    scale = 0.8
    for face in result['geom']:
        if isinstance(face, bmesh.types.BMFace):
            material_index = Material.hull_lights if random() > 0.5 else Material.hull
            extruded_face_list = []
            face = extrude_face(bm, face, grid_length, extruded_face_list)
            for extruded_face in extruded_face_list:
                if abs(face.normal.z) < 0.707:  # side face
                    extruded_face.material_index = material_index
            scale_face(bm, face, scale, scale, scale)


def add_cylinders_to_face(bm, face):
    '''Add cylinders to a face in a grid pattern.
    Args:
        bm: bmesh object.
        face: face to add cylinders to.
    '''
    if not face.is_valid or len(face.verts[:]) < 4:
        return
    horizontal_step = randint(1, 3)
    vertical_step = randint(1, 3)
    num_segments = randint(6, 12)
    face_width, face_height = get_face_width_and_height(face)
    cylinder_depth = 1.3 * min(face_width / (horizontal_step + 2),
                               face_height / (vertical_step + 2))
    cylinder_size = cylinder_depth * 0.5
    for h in range(horizontal_step):
        top = face.verts[0].co.lerp(
            face.verts[1].co, (h + 1) / float(horizontal_step + 1))
        bottom = face.verts[3].co.lerp(
            face.verts[2].co, (h + 1) / float(horizontal_step + 1))
        for v in range(vertical_step):
            pos = top.lerp(bottom, (v + 1) / float(vertical_step + 1))
            cylinder_matrix = get_face_matrix(face, pos) * \
                Matrix.Rotation(radians(90), 3, 'X').to_4x4()
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=num_segments,
                                  radius1=cylinder_size,
                                  radius2=cylinder_size,
                                  depth=cylinder_depth,
                                  matrix=cylinder_matrix)


def add_weapons_to_face(bm, face):
    '''Add weapon turrets to a face in a grid pattern.
    Args:
        bm: bmesh object.
        face: face to add weapons to.
    '''
    if not face.is_valid or len(face.verts[:]) < 4:
        return
    horizontal_step = randint(1, 2)
    vertical_step = randint(1, 2)
    num_segments = 16
    face_width, face_height = get_face_width_and_height(face)
    weapon_size = 0.5 * min(face_width / (horizontal_step + 2),
                            face_height / (vertical_step + 2))
    weapon_depth = weapon_size * 0.2
    for h in range(horizontal_step):
        top = face.verts[0].co.lerp(
            face.verts[1].co, (h + 1) / float(horizontal_step + 1))
        bottom = face.verts[3].co.lerp(
            face.verts[2].co, (h + 1) / float(horizontal_step + 1))
        for v in range(vertical_step):
            pos = top.lerp(bottom, (v + 1) / float(vertical_step + 1))
            face_matrix = get_face_matrix(face, pos + face.normal * weapon_depth * 0.5) * \
                Matrix.Rotation(radians(uniform(0, 90)), 3, 'Z').to_4x4()

            # Turret foundation
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=num_segments,
                                  radius1=weapon_size * 0.9,
                                  radius2=weapon_size,
                                  depth=weapon_depth,
                                  matrix=face_matrix)

            # Turret left guard
            left_guard_mat = face_matrix * \
                Matrix.Rotation(radians(90), 3, 'Y').to_4x4() * \
                Matrix.Translation(Vector((0, 0, weapon_size * 0.6))).to_4x4()
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=num_segments,
                                  radius1=weapon_size * 0.6,
                                  radius2=weapon_size * 0.5,
                                  depth=weapon_depth * 2,
                                  matrix=left_guard_mat)

            # Turret right guard
            right_guard_mat = face_matrix * \
                Matrix.Rotation(radians(90), 3, 'Y').to_4x4() * \
                Matrix.Translation(Vector((0, 0, weapon_size * -0.6))).to_4x4()
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=num_segments,
                                  radius1=weapon_size * 0.5,
                                  radius2=weapon_size * 0.6,
                                  depth=weapon_depth * 2,
                                  matrix=right_guard_mat)

            # Turret housing
            upward_angle = uniform(0, 45)
            turret_house_mat = face_matrix * \
                Matrix.Rotation(radians(upward_angle), 3, 'X').to_4x4() * \
                Matrix.Translation(Vector((0, weapon_size * -0.4, 0))).to_4x4()
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=8,
                                  radius1=weapon_size * 0.4,
                                  radius2=weapon_size * 0.4,
                                  depth=weapon_depth * 5,
                                  matrix=turret_house_mat)

            # Turret barrels L + R
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=8,
                                  radius1=weapon_size * 0.1,
                                  radius2=weapon_size * 0.1,
                                  depth=weapon_depth * 6,
                                  matrix=turret_house_mat *
                                  Matrix.Translation(Vector((weapon_size * 0.2, 0, -weapon_size))).to_4x4())
            bmesh.ops.create_cone(bm,
                                  cap_ends=True,
                                  cap_tris=False,
                                  segments=8,
                                  radius1=weapon_size * 0.1,
                                  radius2=weapon_size * 0.1,
                                  depth=weapon_depth * 6,
                                  matrix=turret_house_mat *
                                  Matrix.Translation(Vector((weapon_size * -0.2, 0, -weapon_size))).to_4x4())


def add_sphere_to_face(bm, face):
    '''Add a sphere to a face.
    Args:
        bm: bmesh object.
        face: face to add sphere to.
    '''
    if not face.is_valid:
        return
    face_width, face_height = get_face_width_and_height(face)
    sphere_size = uniform(0.4, 1.0) * min(face_width, face_height)
    sphere_matrix = get_face_matrix(face,
                                    face.calc_center_bounds() - face.normal *
                                    uniform(0, sphere_size * 0.5))
    result = bmesh.ops.create_icosphere(bm,
                                        subdivisions=3,
                                        radius=sphere_size,
                                        matrix=sphere_matrix)
    for vert in result['verts']:
        for face in vert.link_faces:
            face.material_index = Material.hull


def add_surface_antenna_to_face(bm, face):
    '''Add surface antennas to a face.
    Args:
        bm: bmesh object.
        face: face to add antennas to.
    '''
    if not face.is_valid or len(face.verts[:]) < 4:
        return
    horizontal_step = randint(4, 10)
    vertical_step = randint(4, 10)
    for h in range(horizontal_step):
        top = face.verts[0].co.lerp(
            face.verts[1].co, (h + 1) / float(horizontal_step + 1))
        bottom = face.verts[3].co.lerp(
            face.verts[2].co, (h + 1) / float(horizontal_step + 1))
        for v in range(vertical_step):
            if random() > 0.9:
                pos = top.lerp(bottom, (v + 1) / float(vertical_step + 1))
                face_size = sqrt(face.calc_area())
                depth = uniform(0.1, 1.5) * face_size
                depth_short = depth * uniform(0.02, 0.15)
                base_diameter = uniform(0.005, 0.05)

                material_index = Material.hull if random() > 0.5 else Material.hull_dark
                num_segments = int(uniform(3, 6))

                # Spire
                result = bmesh.ops.create_cone(bm,
                                               cap_ends=False,
                                               cap_tris=False,
                                               segments=num_segments,
                                               radius1=0,
                                               radius2=base_diameter,
                                               depth=depth,
                                               matrix=get_face_matrix(face, pos + face.normal * depth * 0.5))
                for vert in result['verts']:
                    for vert_face in vert.link_faces:
                        vert_face.material_index = material_index

                # Base
                result = bmesh.ops.create_cone(bm,
                                               cap_ends=True,
                                               cap_tris=False,
                                               segments=num_segments,
                                               radius1=base_diameter * uniform(1, 1.5),
                                               radius2=base_diameter * uniform(1.5, 2),
                                               depth=depth_short,
                                               matrix=get_face_matrix(face, pos + face.normal * depth_short * 0.45))
                for vert in result['verts']:
                    for vert_face in vert.link_faces:
                        vert_face.material_index = material_index


def add_disc_to_face(bm, face):
    '''Add a glowing disc to a face.
    Args:
        bm: bmesh object.
        face: face to add disc
    '''
    if not face.is_valid:
        return
    face_width, face_height = get_face_width_and_height(face)
    depth = 0.125 * min(face_width, face_height)
    bmesh.ops.create_cone(bm,
                          cap_ends=True,
                          cap_tris=False,
                          segments=32,
                          radius1=depth * 3,
                          radius2=depth * 4,
                          depth=depth,
                          matrix=get_face_matrix(face, face.calc_center_bounds() + face.normal * depth * 0.5))
    result = bmesh.ops.create_cone(bm,
                                   cap_ends=False,
                                   cap_tris=False,
                                   segments=32,
                                   radius1=depth * 1.25,
                                   radius2=depth * 2.25,
                                   depth=0.0,
                                   matrix=get_face_matrix(face, face.calc_center_bounds() + face.normal * depth * 1.05))
    for vert in result['verts']:
        for face in vert.link_faces:
            face.material_index = Material.glow_disc


class Material(IntEnum):
    hull = 0            # Plain spaceship hull
    hull_lights = 1     # Spaceship hull with emissive windows
    hull_dark = 2       # Plain Spaceship hull, darkened
    exhaust_burn = 3    # Emissive engine burn material
    glow_disc = 4       # Emissive landing pad disc material


img_cache = {}


def create_texture(name: str, tex_type: str, filename: str, use_alpha: bool = True):
    '''Create a texture from an image file.
    Args:
        name (str): name of the texture.
        tex_type (str): type of the texture.
        filename (str): path to the image file.
        use_alpha (bool): whether to use the alpha channel.
    Returns:
        tex: the created texture.
    '''
    if filename in img_cache:
        # Image has been cached already, so just use that.
        img = img_cache[(filename, use_alpha)]
    else:
        # We haven't cached this asset yet, so load it from disk.
        try:
            img = bpy.data.images.load(filename)
        except:
            raise IOError("Cannot load image: %s" % filename)
        # Set the alpha channel usage
        # img.alpha_mode = use_alpha
        img.pack()
        # Cache the asset
        img_cache[(filename, use_alpha)] = img

    # Create and return a new texture using img
    tex = bpy.data.textures.new(name, tex_type)
    tex.image = img
    return tex


def add_hull_normal_map(mat, hull_normal_colortex):
    '''Add a hull normal map texture slot to a material.
    Args:
        mat: material to add the texture slot to.
        hull_normal_colortex: the normal map texture.
    '''
    material_output = mat.node_tree.nodes.get('Material Output')
    principled_BSDF = mat.node_tree.nodes.get('Principled BSDF')
    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex_node.image = hull_normal_colortex.image
    # tex_node.texture_coords = 'GLOBAL'  # global UVs, yolo
    # tex_node.mapping = 'CUBE'
    # tex_node.use_map_color_diffuse = False
    # tex_node.use_map_normal = True
    # tex_node.normal_factor = 1
    # tex_node.bump_method = 'BUMP_BEST_QUALITY'


def set_hull_mat_basics(mat, color, hull_normal_colortex):
    '''Set some basic properties for a hull material.
    Args:
        mat: material to set properties for.
        color: base color of the hull.
        hull_normal_colortex: normal map texture.
    '''
    mat.specular_intensity = 0.1
    mat.diffuse_color = color
    add_hull_normal_map(mat, hull_normal_colortex)


def create_materials():
    '''Create all spaceship materials.
    Returns:
        ret: list of materials
'''
    ret = []
    for material in Material:
        new_mat = bpy.data.materials.new(material.name)
        new_mat.use_nodes = True
        ret.append(new_mat)

    # Choose a base color for the spaceship hull
    hull_base_color = hls_to_rgb(random(), uniform(0.05, 0.5), uniform(0, 0.25))
    hull_base_color = (hull_base_color[0], hull_base_color[1], hull_base_color[2], 1.0)

    # Load up the hull normal map
    hull_normal_colortex = create_texture('ColorTex', 'IMAGE', resource_path('textures', 'hull_normal.png'))
    hull_normal_colortex.use_normal_map = True

    # Build the hull texture
    mat = ret[Material.hull]
    set_hull_mat_basics(mat, hull_base_color, hull_normal_colortex)

    # Build the hull_lights texture
    mat = ret[Material.hull_lights]
    set_hull_mat_basics(mat, hull_base_color, hull_normal_colortex)

    # Add a diffuse layer that sets the window color
    material_output = mat.node_tree.nodes.get('Material Output')
    principled_BSDF = mat.node_tree.nodes.get('Principled BSDF')
    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    texture = create_texture('ColorTex', 'IMAGE', resource_path('textures', 'hull_lights_diffuse.png'))
    tex_node.image = texture.image
    # mtex = mat.texture_slots.add()
    # mtex.texture = create_texture('ColorTex', 'IMAGE', resource_path('textures', 'hull_lights_diffuse.png'))
    # mtex.texture_coords = 'GLOBAL'
    # mtex.mapping = 'CUBE'
    # mtex.blend_type = 'ADD'
    # mtex.use_map_color_diffuse = True
    # mtex.use_rgb_to_intensity = True
    # mtex.color = hls_to_rgb(random(), uniform(0.5, 1), uniform(0, 0.5))

    # Add an emissive layer that lights up the windows
    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    texture = create_texture('ColorTex', 'IMAGE', resource_path('textures', 'hull_lights_emit.png'), False)
    tex_node.image = texture.image
    # mtex = mat.texture_slots.add()
    # mtex.texture = create_texture('ColorTex', 'IMAGE', resource_path('textures', 'hull_lights_emit.png'), False)
    # mtex.texture_coords = 'GLOBAL'
    # mtex.mapping = 'CUBE'
    # mtex.use_map_emit = True
    # mtex.emit_factor = 2.0
    # mtex.blend_type = 'ADD'
    # mtex.use_map_color_diffuse = False

    # Build the hull_dark texture
    mat = ret[Material.hull_dark]
    hull_base_color = [0.3 * x for x in hull_base_color]
    hull_base_color = (hull_base_color[0], hull_base_color[1], hull_base_color[2], 1.0)
    set_hull_mat_basics(mat, hull_base_color, hull_normal_colortex)

    # Choose a glow color for the exhaust + glow discs
    glow_color = hls_to_rgb(random(), uniform(0.5, 1), 1)
    glow_color = (glow_color[0], glow_color[1], glow_color[2], 1.0)

    # Build the exhaust_burn texture
    mat = ret[Material.exhaust_burn]
    mat.diffuse_color = glow_color
    # mat.node_tree.nodes.new('ShaderNodeEmission')
    # mat.node_tree.nodes["ShaderNodeEmission"].inputs[1].default_value = 1.0

    # Build the glow_disc texture
    mat = ret[Material.glow_disc]
    mat.diffuse_color = glow_color
    # mat.node_tree.nodes.new('ShaderNodeEmission')
    # mat.node_tree.nodes["ShaderNodeEmission"].inputs[1].default_value = 1.0

    return ret


def generate_spaceship(random_seed: str = "",
                       x_segments: bool = True,
                       y_segments: bool = False,
                       z_segments: bool = False,
                       num_hull_segments_min: int = 3,
                       num_hull_segments_max: int = 6,
                       create_asymmetry_segments: bool = True,
                       num_asymmetry_segments_min: int = 1,
                       num_asymmetry_segments_max: int = 5,
                       create_face_detail: bool = True,
                       allow_horizontal_symmetry: bool = True,
                       allow_vertical_symmetry: bool = False,
                       apply_bevel_modifier: bool = True,
                       assign_materials: bool = True):
    '''Generate a spaceship mesh.
    Args:
        random_seed (str): random seed for the generator.
        x_segments (bool): whether to segment the hull along the X axis.
        y_segments (bool): whether to segment the hull along the Y axis.
        z_segments (bool): whether to segment the hull along the Z axis.
        num_hull_segments_min (int): minimum number of hull segments.
        num_hull_segments_max (int): maximum number of hull segments.
        create_asymmetry_segments (bool): whether to add asymmetrical hull segments.
        num_asymmetry_segments_min (int): minimum number of asymmetry segments.
        num_asymmetry_segments_max (int): maximum number of asymmetry segments.
        create_face_detail (bool): whether to add detail to the hull faces.
        allow_horizontal_symmetry (bool): whether to allow horizontal symmetry.
        allow_vertical_symmetry (bool): whether to allow vertical symmetry.
        apply_bevel_modifier (bool): whether to apply a bevel modifier.
        assign_materials (bool): whether to assign materials to the spaceship.
    '''
    if random_seed is not None:
        if type(random_seed) == str:
            if random_seed != "":
                seed(random_seed)
        elif type(random_seed) == int:
            seed(random_seed)
    else:
        seed()

    # Print each input parameter
    print("random_seed: " + str(random_seed))
    print("x_segments: " + str(x_segments))
    print("y_segments: " + str(y_segments))
    print("z_segments: " + str(z_segments))
    print("num_hull_segments_min: " + str(num_hull_segments_min))
    print("num_hull_segments_max: " + str(num_hull_segments_max))
    print("create_asymmetry_segments: " + str(create_asymmetry_segments))
    print("num_asymmetry_segments_min: " + str(num_asymmetry_segments_min))
    print("num_asymmetry_segments_max: " + str(num_asymmetry_segments_max))
    print("create_face_detail: " + str(create_face_detail))
    print("allow_horizontal_symmetry: " + str(allow_horizontal_symmetry))
    print("allow_vertical_symmetry: " + str(allow_vertical_symmetry))
    print("apply_bevel_modifier: " + str(apply_bevel_modifier))
    print("assign_materials: " + str(assign_materials))

    if num_hull_segments_min is None or type(num_hull_segments_min) != int:
        num_hull_segments_min = 3

    if num_hull_segments_max is None or type(num_hull_segments_max) != int:
        num_hull_segments_max = 6

    wm = bpy.context.window_manager

    wm.progress_begin(0, 100)
    # Let's start with a unit BMesh cube scaled randomly
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    scale_vector = Vector(
        (uniform(0.75, 2.0), uniform(0.75, 2.0), uniform(0.75, 2.0)))
    bmesh.ops.scale(bm, vec=scale_vector, verts=bm.verts)

    wm.progress_update(5)
    # Extrude out the hull along the X axis, adding some semi-random perturbations
    for face in bm.faces[:]:
        isX = x_segments and abs(face.normal.x) > 0.5
        isY = y_segments and abs(face.normal.y) > 0.5
        isZ = z_segments and abs(face.normal.z) > 0.5
        if isX or isY or isZ:
            hull_segment_length = uniform(0.3, 1)
            num_hull_segments = randrange(num_hull_segments_min, num_hull_segments_max)
            hull_segment_range = range(num_hull_segments)
            for i in hull_segment_range:
                # if i > 2:
                #   break
                if (isY or isZ) and i > 5:
                    break
                is_last_hull_segment = i == hull_segment_range[-1]
                if (isY or isZ) and i == 5:
                    is_last_hull_segment = True

                val = random()
                if val > 0.1:
                    # Most of the time, extrude out the face with some random deviations
                    face = extrude_face(bm, face, hull_segment_length)
                    if random() > 0.75:
                        face = extrude_face(
                            bm, face, hull_segment_length * 0.25)

                    # Maybe apply some scaling
                    if random() > 0.5:
                        # sx = uniform(1.2, 1.5)
                        sy = uniform(1.2, 1.5)
                        sz = uniform(1.2, 1.5)
                        if is_last_hull_segment or random() > 0.5:
                            # sx = 1 / sx
                            sy = 1 / sy
                            sz = 1 / sz
                        scale_face(bm, face, 1, sy, sz)

                    # Maybe apply some sideways translation
                    if random() > 0.5:
                        sideways_translation = Vector(
                            (0, 0, uniform(0.1, 0.4) * scale_vector.z * hull_segment_length))
                        if random() > 0.5:
                            sideways_translation = -sideways_translation
                        bmesh.ops.translate(bm,
                                            vec=sideways_translation,
                                            verts=face.verts)

                    # Maybe add some rotation around Y axis
                    if x_segments and random() > 0.5:
                        angle = 5
                        if random() > 0.5:
                            angle = -angle
                        bmesh.ops.rotate(bm,
                                         verts=face.verts,
                                         cent=(0, 0, 0),
                                         matrix=Matrix.Rotation(radians(angle), 3, 'Y'))
                else:
                    # Rarely, create a ribbed section of the hull
                    rib_scale = uniform(0.75, 0.95)
                    face = ribbed_extrude_face(
                        bm, face, hull_segment_length, randint(2, 4), rib_scale)

    wm.progress_update(25)
    # Add some large asymmetrical sections of the hull that stick out
    if create_asymmetry_segments:
        for face in bm.faces[:]:
            # Skip any long thin faces as it'll probably look stupid
            if get_aspect_ratio(face) > 4:
                continue
            if random() > 0.85:
                hull_piece_length = uniform(0.1, 0.4)
                hull_segments = randrange(num_asymmetry_segments_min, num_asymmetry_segments_max)
                for i in range(hull_segments):
                    face = extrude_face(bm, face, hull_piece_length)

                    # Maybe apply some scaling
                    if random() > 0.25:
                        s = 1 / uniform(1.1, 1.5)
                        scale_face(bm, face, s, s, s)

    wm.progress_update(35)
    # Now the basic hull shape is built, let's categorize + add detail to all the faces
    if create_face_detail:
        engine_faces = []
        grid_faces = []
        antenna_faces = []
        weapon_faces = []
        sphere_faces = []
        disc_faces = []
        cylinder_faces = []
        for face in bm.faces[:]:
            # Skip any long thin faces as it'll probably look stupid
            if get_aspect_ratio(face) > 3:
                continue

            # Spin the wheel! Let's categorize + assign some materials
            val = random()
            if is_rear_face(face):  # rear face
                if not engine_faces or val > 0.75:
                    engine_faces.append(face)
                elif val > 0.5:
                    cylinder_faces.append(face)
                elif val > 0.25:
                    grid_faces.append(face)
                else:
                    face.material_index = Material.hull_lights
            elif face.normal.x > 0.9:  # front face
                if face.normal.dot(face.calc_center_bounds()) > 0 and val > 0.7:
                    antenna_faces.append(face)  # front facing antenna
                    face.material_index = Material.hull_lights
                elif val > 0.4:
                    grid_faces.append(face)
                else:
                    face.material_index = Material.hull_lights
            elif face.normal.z > 0.9:  # top face
                if face.normal.dot(face.calc_center_bounds()) > 0 and val > 0.7:
                    antenna_faces.append(face)  # top facing antenna
                elif val > 0.6:
                    grid_faces.append(face)
                elif val > 0.3:
                    cylinder_faces.append(face)
            elif face.normal.z < -0.9:  # bottom face
                if val > 0.75:
                    disc_faces.append(face)
                elif val > 0.5:
                    grid_faces.append(face)
                elif val > 0.25:
                    weapon_faces.append(face)
            elif abs(face.normal.y) > 0.9:  # side face
                if not weapon_faces or val > 0.75:
                    weapon_faces.append(face)
                elif val > 0.6:
                    grid_faces.append(face)
                elif val > 0.4:
                    sphere_faces.append(face)
                else:
                    face.material_index = Material.hull_lights

        wm.progress_update(40)
        # Now we've categorized, let's actually add the detail
        for face in engine_faces:
            add_exhaust_to_face(bm, face)
        wm.progress_update(42)
        for face in grid_faces:
            add_grid_to_face(bm, face)
        wm.progress_update(47)
        for face in antenna_faces:
            add_surface_antenna_to_face(bm, face)
        wm.progress_update(52)
        for face in weapon_faces:
            add_weapons_to_face(bm, face)
        wm.progress_update(57)
        for face in sphere_faces:
            add_sphere_to_face(bm, face)
        wm.progress_update(62)
        for face in disc_faces:
            add_disc_to_face(bm, face)
        wm.progress_update(67)
        for face in cylinder_faces:
            add_cylinders_to_face(bm, face)

    wm.progress_update(70)

    # Apply horizontal symmetry sometimes
    if allow_horizontal_symmetry and random() > 0.5:
        bmesh.ops.symmetrize(bm, input=bm.verts[:] + bm.edges[:] + bm.faces[:], direction="-X")  # 1

    wm.progress_update(75)

    # Apply vertical symmetry sometimes - this can cause spaceship "islands", so disabled by default
    if allow_vertical_symmetry and random() > 0.5:
        bmesh.ops.symmetrize(bm, input=bm.verts[:] + bm.edges[:] + bm.faces[:], direction="-Y")  # 2

    wm.progress_update(80)

    # Finish up, write the bmesh into a new mesh
    me = bpy.data.meshes.new('Mesh')
    bm.to_mesh(me)
    bm.free()

    # Add the mesh to the scene
    scene = bpy.context.scene
    obj = bpy.data.objects.new('Spaceship', me)
    bpy.context.collection.objects.link(obj)

    # Select and make active
    current_state = bpy.data.objects["Spaceship"].select_get()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Recenter the object to its center of mass
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
    ob = bpy.context.object
    ob.location = (0, 0, 0)

    # Add a fairly broad bevel modifier to angularize shape
    if apply_bevel_modifier:
        bevel_modifier = ob.modifiers.new('Bevel', 'BEVEL')
        bevel_modifier.width = uniform(5, 20)
        bevel_modifier.offset_type = 'PERCENT'
        bevel_modifier.segments = 2
        bevel_modifier.profile = 0.25
        bevel_modifier.limit_method = 'NONE'

    wm.progress_update(90)

    # Add materials to the spaceship
    me = ob.data
    materials = create_materials()
    for mat in materials:
        if assign_materials:
            me.materials.append(mat)
        else:
            me.materials.append(bpy.data.materials.new(name="Material"))

    wm.progress_update(100)
    wm.progress_end()
    return obj
