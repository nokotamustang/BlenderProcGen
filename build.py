#!/usr/bin/env python

from os.path import abspath, dirname, join as pjoin
import zipfile
import os

SRC_DIR = dirname(abspath(__file__))

build_dir = f"{SRC_DIR}\\build"

# Create the build directory if it doesn't exist
if not os.path.exists(build_dir):
    os.makedirs(build_dir)

# Remove the existing build zip file if it exists
if os.path.exists(f"{build_dir}\\add_mesh_SpaceshipGenerator.zip"):
    os.remove(f"{build_dir}\\add_mesh_SpaceshipGenerator.zip")

# Create the build zip file
with zipfile.ZipFile('add_mesh_SpaceshipGenerator.zip', 'w', zipfile.ZIP_DEFLATED) as arch:
    for filename in [
            '__init__.py',
            'spaceship_generator.py',
            'textures/hull_normal.png',
            'textures/hull_lights_emit.png',
            'textures/hull_lights_diffuse.png']:
        arch.write(pjoin(SRC_DIR, filename), 'add_mesh_SpaceshipGenerator/'+filename)

# Move the zip file to the build directory
os.rename('add_mesh_SpaceshipGenerator.zip', f"{build_dir}\\add_mesh_SpaceshipGenerator.zip")

print('created file: add_mesh_SpaceshipGenerator.zip')
