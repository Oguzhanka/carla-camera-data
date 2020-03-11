"""
Recorder class implementation.
"""
import skvideo.io
import numpy as np
import datetime
import config
import helper
import math
import json
import glob
import sys
import csv
import cv2
import os


__all__ = ["Recorder"]

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla
from carla import Transform
from carla import Location, Rotation
from carla import ColorConverter as cc

import queue


VIDEO_RES = (1440, 2560)


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
        self.logger.writerows([["type", "time", "x", "y", "orient", "width", "height"]])

        self.info_file = open(info_file, "w")

        self.video_start_time = -1
        print("Record date: {}".format(datetime.datetime.today()),
              file=self.info_file,
              flush=True)

        self.cur_pos = [0, 0, 120]
        self.cur_velocity = [2, 0, 1, 1]
        self.cur_angle = [90, -80]

        self.aspect_ratio = VIDEO_RES[1] / VIDEO_RES[0]
        self.boundaries = [2 * self.cur_pos[2] * math.tan(math.pi/4)]
        self.boundaries.append(self.boundaries[0]/self.aspect_ratio)
        self.boundaries.reverse()

        bp_library = world.get_blueprint_library()
        camera_bp = bp_library.find('sensor.camera.rgb')
        camera_bp.set_attribute('image_size_x', str(VIDEO_RES[1]))
        camera_bp.set_attribute('image_size_y', str(VIDEO_RES[0]))

        segmentation_camera = bp_library.find('sensor.camera.semantic_segmentation')
        segmentation_camera.set_attribute('image_size_x', str(VIDEO_RES[1]))
        segmentation_camera.set_attribute('image_size_y', str(VIDEO_RES[0]))

        transform = Transform(Location(x=self.cur_pos[0],
                                       y=self.cur_pos[1],
                                       z=self.cur_pos[2]),
                              Rotation(yaw=self.cur_angle[0], pitch=self.cur_angle[1]))
        self.camera = world.spawn_actor(camera_bp, transform)
        self.segmentation_goggles = world.spawn_actor(segmentation_camera, transform)

        self.image_queue = queue.Queue()
        self.segmentation_queue = queue.Queue()
        self.camera.listen(self.image_queue.put)
        self.segmentation_goggles.listen(self.segmentation_queue.put)

        self.rotated_bounding = False
        self.json_dict = {"video_filename": video_file,
                          "frames": [],
                          "categories": self.object_categories}
        self.init_time = world.tick()
        self.init_ms = world.get_snapshot().platform_timestamp
        self.world = world

    def move(self):
        self.cur_pos[0] += self.cur_velocity[0]
        self.cur_pos[1] += self.cur_velocity[1]
        self.cur_angle[0] += self.cur_velocity[2]
        self.cur_angle[1] += self.cur_velocity[3]

        transform = Transform(Location(x=self.cur_pos[0],
                                       y=self.cur_pos[1],
                                       z=self.cur_pos[2]),
                              Rotation(yaw=self.cur_angle[0], pitch=self.cur_angle[1]))

        self.camera.set_transform(transform)
        self.segmentation_goggles.set_transform(transform)

    def log_actors(self, time):
        """
        Actor logging function. Main loop provides the server time which is to be logged into the
        actor log file along with the pixel locations of the actor centers, bounding box size in
        pixel coordinates and the orientations of the bounding boxes on pixel plane. Also, actor
        type and the ID is recorded.

        :param int time: Server time.
        :return: None
        """
        detected_actors = self.detect_actors(time)
        ms = self.world.get_snapshot().platform_timestamp
        ms_diff = int((ms - self.init_ms) * 1000 % 1000)
        h_diff = int((ms - self.init_ms) // 3600)
        m_diff = int((ms - self.init_ms) // 600 - h_diff * 60)
        s_diff = int((ms - self.init_ms) - h_diff * 3600 - m_diff * 60)
        cur_frame = {"frame": time-self.init_time,
                     "miliseconds": "{}:{}:{}:{}".format(h_diff, m_diff, s_diff, ms_diff),
                     "bboxes": []}

        for object_type in config.classes.keys():
            if object_type not in ["Vehicles", "Pedestrians"]:
                continue
            self.logger.writerows(detected_actors[object_type])

            for actor in detected_actors[object_type]:
                rect_points = helper.get_rect(actor[2], actor[3], actor[5], actor[6], actor[4])
                actor_data = {"x": rect_points[0][0],
                              "y": rect_points[0][1],
                              "w": actor[5],
                              "h": actor[6],
                              "c": self.object_categories[actor[0]]}
                cur_frame["bboxes"].append(actor_data)
        self.json_dict["frames"].append(cur_frame)

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

    def detect_actors(self, time):
        image = self.segmentation_queue.get()
        image.convert(cc.Raw)
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]

        detected_actors = {}

        for object_type in config.classes.keys():
            if object_type not in ["Vehicles", "Pedestrians"]:
                continue

            detected_actors[object_type] = []
            object_value = config.classes[object_type]
            threshold = ([val for val in object_value], [val for val in object_value])
            mask = cv2.inRange(array, np.array(threshold[0]), np.array(threshold[1]))

            contours, hierarchy = cv2.findContours(mask.copy(),
                                                   cv2.RETR_EXTERNAL,
                                                   cv2.CHAIN_APPROX_NONE)

            for contour in contours:
                if self.rotated_bounding:
                    rect = cv2.minAreaRect(contour)
                    detected_actors[object_type].append([object_type, time, int(rect[0][0]), int(rect[0][1]),
                                                         int(rect[2]), int(rect[1][0]), int(rect[1][1])])
                else:
                    rect = cv2.boundingRect(contour)
                    detected_actors[object_type].append([object_type, time, int(rect[0]) + int(rect[2]) // 2,
                                                         int(rect[1]) + int(rect[3] // 2), int(0), int(rect[2]),
                                                         int(rect[3])])

        return detected_actors

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

    @property
    def object_categories(self):
        category = {"Vehicles": 0,
                    "Pedestrian": 1}
        return category

    def __del__(self):
        """
        Destructor method for the recorder object. All log file descriptors are destroyed and video writer
        object is destructed.

        :return: None
        """
        print("Video start timestamp: {}".format(str(self.video_start_time)), file=self.info_file, flush=True)
        with open('./out/result.json', 'w') as fp:
            json.dump(self.json_dict, fp)
        self.camera.destroy()
        self.writer.close()
        self.info_file.close()
