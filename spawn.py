"""
Actor spawner class implementation.
"""
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


class Spawn:
    """
    Multiple actor spawner object iss bound to a carla.World object and spawns vehicles or walkers
    inside the world object that it is bound to. Also keeps track of the carla.Actor objects spawned
    by this object. While spawning actors, caller can specify a specific blueprint and a location or,
    spawner object will pick randomly. Upon destruction, destroys all actors spawned by this object.

    Args:
    -----

    :param carla.World world: World object in which the actors will be spawned.

    Attributes:
    -----------

    :ivar world: World object in which the actors will be spawned.
    :vartype world: carla.World

    :ivar spawned_actors: List of actors spawned by this Spawn object.
    :vartype spawned_actors: list

    :ivar filter_dict: Short keywords for filters passed to the Spawn object. Filter type will be
                       used to filter the blueprint population from which the random blueprint will
                       be sampled.
    :vartype filter_dict: Dictionary
    """
    def __init__(self, world):
        self.world = world
        self.spawned_actors = []

        self.filter_dict = {"": "*",
                            "vehicle": "vehicle",
                            "walker": "walker"}

    def spawn_actor(self, location=None, actor_type="", blueprint=None):
        """
        Actor spawning method. If specified, created actor will spawn in the given location. Otherwise,
        a random location will be selected from the available spawn points. If specified, an actor with
        the specified blueprint will be spawned. Otherwise, a random will be selected from the available
        blueprint library.

        :param carla.Transform location: Location of the actor that will be spawned. If not specified,
                                         a random location will be sampled from the available spawn
                                         points.
        :param str actor_type: Type of the actor to be generated. Can be ["walker", "vehicle"].
        :param carla.Blueprint blueprint: Blueprint for the actor to be spawned. If not specified, a
                                          random blueprint will be picked from the library.
        :return: None
        """
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
        """
        Destructor for the spawner object. When called, destroys all the actors spawned by this object.
        :return: None
        """
        for actor in self.spawned_actors:
            actor.destroy()
