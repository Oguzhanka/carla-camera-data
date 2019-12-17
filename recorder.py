"""
Recorder class implementation.
"""
import skvideo.io
import numpy as np
import datetime
import math
import glob
import sys
import csv
import os


__all__ = ["Recorder"]

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import queue
from carla import Transform
from carla import Location, Rotation
from carla import ColorConverter as cc


VIDEO_RES = (960, 1280)


class Recorder:
    """
    A recorder object is an RGB camera located in a specified location (or in a random location
    if not specified). Object records observed frames into a video file and logs the visible
    actors in sight into a csv file. Also, video record date and server time for the first
    frame is logged to an info file.

    Args:
    -----

    :param carla.World world: World object. Server world object passed by reference. Recorder object is placed

    :param file video_file: Name or file descriptor for the video recording output.
    :param file log_file: Name or file descriptor for the visible actors log file.
    :param file info_file: Name or file descriptor for the recording information file.

    Attributes:
    -----------

    :ivar writer: Video frame writer object. Uses FFmpegWriter class of skvideo.io
    :vartype writer: skvideo.io.FFmpegWriter

    :ivar logger: Logger object which logs the observed actors' pixel locations on
                  the recorded frames.
    :vartype logger: csv.writer

    :ivar info_file: Information file logger object which records the date of recording
                     and the server tick time of the first frame.
    :vartype info_file: file

    :ivar cur_pos: Current position vector of the Recorder object. Has 3 elements specifying the real-world
                   coordinates for the Recorder object. Vector elements are [x, y, z].
    :vartype cur_pos: list

    :ivar cur_velocity: Current velocity vector of the Recorder object. Has 2 elements specifying the real-
                        world velocity of the object in x and y dimensions. Vector elements are [V_x, V_y].
    :vartype cur_velocity: list
    """
    def __init__(self, world, video_file, log_file, info_file):
        self.writer = skvideo.io.FFmpegWriter(video_file,
                                              outputdict={'-vcodec': 'libx264'})
        self.logger = csv.writer(open(log_file, "w"))
        self.logger.writerows([["id", "type", "time", "x", "y", "orient", "height", "width"]])

        self.info_file = open(info_file, "w")
        print("Record date: {}".format(datetime.datetime.today()),
              file=self.info_file,
              flush=True)

        self.cur_pos = [0, 0, 120]
        self.cur_velocity = [0, 0]
        self.cur_angle = [90, -90]

        self.aspect_ratio = VIDEO_RES[1] / VIDEO_RES[0]
        self.boundaries = [2 * self.cur_pos[2] * math.tan(math.pi/4)]
        self.boundaries.append(self.boundaries[0]/self.aspect_ratio)
        self.boundaries.reverse()

        bp_library = world.get_blueprint_library()
        camera_bp = bp_library.find('sensor.camera.rgb')
        camera_bp.set_attribute('image_size_x', str(VIDEO_RES[1]))
        camera_bp.set_attribute('image_size_y', str(VIDEO_RES[0]))

        transform = Transform(Location(x=self.cur_pos[0],
                                       y=self.cur_pos[1],
                                       z=self.cur_pos[2]),
                              Rotation(yaw=self.cur_angle[0], pitch=self.cur_angle[1]))
        self.camera = world.spawn_actor(camera_bp, transform)

        self.image_queue = queue.Queue()
        self.camera.listen(self.image_queue.put)

        self.video_start_time = -1

    def log_actors(self, time, actors):
        """
        Actor logging function. Main loop provides the server time which is to be logged into the
        actor log file along with the pixel locations of the actor centers, bounding box size in
        pixel coordinates and the orientations of the bounding boxes on pixel plane. Also, actor
        type and the ID is recorded.

        :param int time: Server time.
        :param list actors: List of carla.Actor objects.
        :return: None
        """
        for actor in actors:
            location = actor.get_location()
            actor_type = actor.type_id.split(".")[0]

            conversion_rate = VIDEO_RES[0] / self.boundaries[0] * self.cur_pos[2] / (self.cur_pos[2] - location.z)
            x_bounds = self.boundaries[0]*conversion_rate // 2
            y_bounds = self.boundaries[1]*conversion_rate // 2

            del_x = location.x - self.cur_pos[0]
            del_y = location.y - self.cur_pos[1]

            rot_x, rot_y = np.matmul(self.rotation, np.array([[del_x], [del_y]]))
            if -x_bounds < rot_x < x_bounds and \
                    -y_bounds < rot_y < y_bounds:
                orient = actor.get_transform().rotation.yaw - self.cur_angle[0]
                box = actor.bounding_box
                height = box.extent.x * conversion_rate
                width = box.extent.y * conversion_rate

                x_loc = int(-conversion_rate * rot_x + VIDEO_RES[0] // 2)
                y_loc = int(conversion_rate * rot_y + VIDEO_RES[1] // 2)

                self.logger.writerows([[actor.id, actor_type, time, x_loc, y_loc, orient, height, width]])

    def record_img(self, time):
        """
        Records a frame obtained from the RGB camera sensor. Image frame is converted to a numpy.ndarray
        which is then fed to the FFmpeg writer. Image array is returned the caller for visualizing. Also,
        after capturing the first video frame, server time is recorded which will be logged to the info file.

        :param int time: Server time.
        :return: Captured image frame.
        :rtype: numpy.ndarray
        """
        if self.video_start_time == -1:
            self.video_start_time = time

        image = self.image_queue.get()
        image.convert(cc.Raw)
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        self.writer.writeFrame(array)
        return array

    @property
    def rotation(self):
        """
        Rotation matrix for the yaw angle.

        :return: Rotation matrix.
        :rtype: numpy.ndarray
        """
        angle = -self.cur_angle[0]*np.pi/180
        rotation_matrix = np.array([[np.cos(angle), -np.sin(angle)],
                                    [np.sin(angle), np.cos(angle)]])
        return rotation_matrix

    def __del__(self):
        """
        Destructor method for the recorder object. All log file descriptors are destroyed and video writer
        object is destructed.

        :return: None
        """
        print("Video start timestamp: {}".format(str(self.video_start_time)), file=self.info_file, flush=True)
        self.camera.destroy()
        self.writer.close()
        self.info_file.close()
