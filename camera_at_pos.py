import skvideo.io
import numpy as np
import csv
import glob
import os
import sys


try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla
import queue
from carla import Transform
from carla import Location, Rotation
from carla import ColorConverter as cc


VIDEO_RES = (1440, 2560)
BOUNDARIES = (135, 240)
CENTER = (0, 0)
VELOCITY = (0.0, 0.0)

info_file = "./out/"
video_file = "./out/video.mp4"
vehicle_log_file = "./out/log.csv"
writer = skvideo.io.FFmpegWriter(video_file, outputdict={'-vcodec': 'libx264'})
log_file = csv.writer(open(vehicle_log_file, "w"))


def set_position():
    if cur_pos[1] <= -20:
        cur_velocity[1] = VELOCITY[1]
        cur_velocity[0] = VELOCITY[0]
    if cur_pos[1] >= 20:
        cur_velocity[1] = -VELOCITY[1]
        cur_velocity[0] = -VELOCITY[0]

    cur_pos[0] += cur_velocity[0]
    cur_pos[1] += cur_velocity[1]
    location = camera.get_location()
    location.x = cur_pos[0]
    location.y = cur_pos[1]
    camera.set_location(location)


def process_cars(time):
    for car in cars:
        location = car.get_location()
        if -BOUNDARIES[0]//2 < location.x - cur_pos[0] < BOUNDARIES[0]//2 and\
                -BOUNDARIES[1]//2 < location.y - cur_pos[1] < BOUNDARIES[1]//2:
            orient = car.get_transform().rotation.yaw
            box = car.bounding_box
            height = VIDEO_RES[0]/BOUNDARIES[0]*box.extent.x
            width = VIDEO_RES[0]/BOUNDARIES[0]*box.extent.y

            x_loc = int(-VIDEO_RES[0]/BOUNDARIES[0]*(location.x - cur_pos[0]) + VIDEO_RES[0]//2)
            y_loc = int(VIDEO_RES[1]/BOUNDARIES[1]*(location.y - cur_pos[1]) + VIDEO_RES[1]//2)
            log_file.writerows([[car.id, time, x_loc, y_loc, orient, height, width]])


def process_img(image):
    image.convert(cc.Raw)
    array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
    array = np.reshape(array, (image.height, image.width, 4))
    array = array[:, :, :3]
    array = array[:, :, ::-1]
    writer.writeFrame(array)


client = carla.Client('192.168.2.211', 2000)
log_file.writerows([["id", "time", "x", "y", "orient", "height", "width"]])
client.set_timeout(10.0)

world = client.get_world()
settings = world.get_settings()
settings.synchronous_mode = False
world.apply_settings(settings)

cars = world.get_actors().filter("vehicle.*")
pedestrians = world.get_actors().filter("walker")
spectator = world.get_actors().filter('spectator')[0]

bp_library = world.get_blueprint_library()
camera_bp = bp_library.find('sensor.camera.rgb')
camera_bp.set_attribute('image_size_x', str(VIDEO_RES[1]))
camera_bp.set_attribute('image_size_y', str(VIDEO_RES[0]))

cur_pos = [CENTER[0], CENTER[1]]
cur_velocity = [VELOCITY[0], VELOCITY[1]]
transform = Transform(Location(x=cur_pos[0], y=cur_pos[1], z=120), Rotation(pitch=-90))
camera = world.spawn_actor(camera_bp, transform)
image_queue = queue.Queue()
camera.listen(image_queue.put)


try:
    while True:
        time = world.tick()
        set_position()
        image = image_queue.get()
        process_cars(time)
        process_img(image)
except KeyboardInterrupt:
    camera.destroy()
    writer.close()
    print('Exit')
