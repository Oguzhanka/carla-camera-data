import random
import glob
import sys
import os


try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

from carla import Transform
from carla import Location, Rotation
from carla import ColorConverter as cc


class Spawn:
    def __init__(self, world):
        self.world = world
        self.spawned_actors = []

        self.filter_dict = {"": "*",
                            "vehicle": "vehicle",
                            "walker": "walker"}

    def spawn_actor(self, location=None, actor_type="", blueprint=None):
        if location is not None:
            transform = Transform(Location(**location))
        else:
            spawn_points = self.world.get_map().get_spawn_points()
            transform = random.sample(spawn_points, 1)[0]

        if blueprint is None:
            blueprints = [bp for bp in self.world.get_blueprint_library().filter(self.filter_dict[actor_type])]
            blueprint = random.sample(blueprints, 1)[0]

        actor = self.world.try_spawn_actor(blueprint, transform)
        if actor is not None:
            actor.set_autopilot(True)
            self.spawned_actors.append(actor)

    def __del__(self):
        for actor in self.spawned_actors:
            actor.destroy()
