# Spaceship Generator

A Blender script to procedurally generate 3D spaceships from a random seed. `Nokota Mustang` has forked this, from Michael Davies, to update it to work with Blender 4.2.

It's working but I had to butcher some of the texture on the materials -- will update as soon as I can figure out how to update the code.

I will add new features when I get the hang of it.

![Spaceship screenshots](https://raw.githubusercontent.com/a1studmuffin/SpaceshipGenerator/master/screenshots/spaceships_grid.jpg)

## Usage

- Install Blender 4.2: <http://blender.org/download/>
- Download newest **add_mesh_SpaceshipGenerator.zip** from the Releases.
- Under `Edit > Preferences > Add-ons > Install` From Disk then pick the release zip file.
- Add a spaceship in the 3D View under `Add > Mesh > Spaceship`

## How it works

![Step-by-step animation](https://raw.githubusercontent.com/a1studmuffin/SpaceshipGenerator/master/screenshots/step-by-step-animation.gif)

Watch on YouTube: <https://www.youtube.com/watch?v=xJZyXqJ6nog>

- Start with a box.
- Build the hull: Extrude the front/rear faces several times, adding random translation/scaling/rotation along the way.
- Add asymmetry to the hull: Pick random faces and extrude them out in a similar manner, reducing in scale each time.
- Add detail to the hull: Categorize each face by its orientation and generate details on it such as engines, antenna, weapon turrets, lights etc.
- Sometimes apply horizontal symmetry.
- Add a Bevel modifier to angularize the shape.
- Apply materials to the final result.
- Take over the universe with your new infinite fleet of spaceships.

## Extreme examples

The following screenshots were created using extreme values for the number of hull segments and asymmetry segments to show how the algorithm works.

![Extreme spaceship screenshots](https://raw.githubusercontent.com/a1studmuffin/SpaceshipGenerator/master/screenshots/extreme_examples.jpg)

## Tips

- By default the script will delete all objects starting with `Spaceship` before generating a new spaceship. To disable this feature, remove or comment out the call to `reset_scene()` around line 735 in the main function.
- You can provide a seed to the `generate_spaceship()` function to always generate the same spaceship. For example, `generate_spaceship('michael')`.
- The `generate_spaceship()` function takes many more parameters that affect the generation process. Try playing with them!
