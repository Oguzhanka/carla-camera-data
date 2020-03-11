import video_labeler
import recorder
import spawn
import cv2
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
from carla import Transform
from carla import Location, Rotation
from carla import ColorConverter as cc


if __name__ == "__main__":
    info_file = "/home/oguzhan/PycharmProjects/carla/out/info.txt"
    video_file = "/home/oguzhan/PycharmProjects/carla/out/video.mp4"
    log_file = "/home/oguzhan/PycharmProjects/carla/out/log.csv"
    labeled_file = "/home/oguzhan/PycharmProjects/carla/out/labeled.mp4"

    client = carla.Client('192.168.12.211', 2000)
    client.set_timeout(10.0)

    world = client.get_world()
    settings = world.get_settings()

    if not settings.synchronous_mode:
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.03
        world.apply_settings(settings)

    record = recorder.Recorder(world=world,
                               video_file=video_file,
                               log_file=log_file,
                               info_file=info_file)

    spawner = spawn.Spawn(world=world)

    for i in range(10):
        spawner.spawn_actor(actor_type="vehicle")

    try:
        while True:
            time = world.tick()
            record.log_actors(time)
            frame = record.record_img(time)
            cv2.imshow("camera", frame)
            record.move()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        raise KeyboardInterrupt

    except KeyboardInterrupt:
        del record
        del spawner
        video_labeler.label_video(log_file=log_file,
                                  video_file=video_file,
                                  out_file=labeled_file)
        print('Exit')


