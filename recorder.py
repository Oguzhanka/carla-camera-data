import skvideo.io
import numpy as np
import datetime
import math
import glob
import sys
import csv
import os


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
    def __init__(self, world, video_file, log_file, info_file):
        self.writer = skvideo.io.FFmpegWriter(video_file,
                                              outputdict={'-vcodec': 'libx264'})
        self.logger = csv.writer(open(log_file, "w"))
        self.logger.writerows([["id", "type", "time", "x", "y", "orient", "height", "width"]])

        self.info_file = open(info_file, "w")
        print("Record date: {}".format(datetime.datetime.today()), file=self.info_file, flush=True)

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
        angle = -self.cur_angle[0]*np.pi/180
        rotation_matrix = np.array([[np.cos(angle), -np.sin(angle)],
                                    [np.sin(angle), np.cos(angle)]])
        return rotation_matrix

    def __del__(self):
        print("Video start timestamp: {}".format(str(self.video_start_time)), file=self.info_file, flush=True)
        self.camera.destroy()
        self.writer.close()
        self.info_file.close()
