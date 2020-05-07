import video_labeler
import recorder
import spawn
import cv2
import glob
import time
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
from carla import Transform
from carla import Location, Rotation
from carla import ColorConverter as cc


if __name__ == "__main__":
    order = sys.argv[-1]
    info_file = "/home/oguzhan/PycharmProjects/carla/out/info_{}.txt".format(order)
    video_file = "/home/oguzhan/PycharmProjects/carla/out/video_{}.mp4".format(order)
    log_file = "/home/oguzhan/PycharmProjects/carla/out/log_{}.csv".format(order)
    labeled_file = "/home/oguzhan/PycharmProjects/carla/out/labeled_{}.mp4".format(order)

    client = carla.Client('192.168.12.211', 2000)
    client.set_timeout(10.0)

    world = client.get_world()
    settings = world.get_settings()

    if not settings.synchronous_mode:
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.033
        world.apply_settings(settings)

    record = recorder.Recorder(world=world,
                               video_file=video_file,
                               log_file=log_file,
                               info_file=info_file,
                               order=order)

    spawner = spawn.Spawn(world=world)
    start_time = 0.0

    for i in range(10):
        spawner.spawn_actor(actor_type="vehicle")

    try:
        k = 0
        while True:
            k += 1
            server_time = world.tick()
            cur_time = world.get_snapshot().platform_timestamp
            if start_time == 0.0:
                start_time = cur_time
            print("\rELAPSED TIME: {}".format(k * 0.033), end="", flush=True)
            record.log_actors(server_time)
            frame = record.record_img(server_time)
            record.move_2((cur_time - start_time) / 1000)

            if k > 15000:
                break

        raise KeyboardInterrupt

    except KeyboardInterrupt:
        del record
        del spawner
        video_labeler.label_video(log_file=log_file,
                                  video_file=video_file,
                                  out_file=labeled_file)
        print('Exit')


