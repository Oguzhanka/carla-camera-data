import numpy as np
import pandas as pd
import skvideo.io

from PIL import Image
from PIL import ImageDraw


def get_rect(x, y, width, height, angle):
    rect = np.array([(-width/0.6, -height/0.6), (width/0.6, -height/0.6),
                     (width/0.6, height/0.6), (-width/0.6, height/0.6),
                     (-width/0.6, -height/0.6)])
    theta = np.pi/180*angle
    R = np.array([[np.cos(theta), -np.sin(theta)],
                  [np.sin(theta), np.cos(theta)]])
    offset = np.array([x, y])
    transformed_rect = np.dot(rect, R) + offset
    return transformed_rect


def label_video(log_file, video_file, out_file):
    logs = pd.read_csv(log_file)
    video_data = skvideo.io.vread(video_file)
    processed_video = skvideo.io.FFmpegWriter(out_file)

    for t, frame in enumerate(video_data):
        log_time = t
        current_objs = logs[logs["time"] == logs["time"][0] + log_time]
        img = Image.fromarray(frame)

        draw = ImageDraw.Draw(img)
        for x, y, w, h, phi in zip(current_objs["x"], current_objs["y"],
                                   current_objs["width"], current_objs["height"],
                                   current_objs["orient"]):
            rect = get_rect(x=y, y=x, width=w, height=h, angle=-phi)
            draw.line([tuple(p) for p in rect], fill="red", width=3)
        labeled_frame = np.asarray(img)
        processed_video.writeFrame(labeled_frame)

    processed_video.close()
