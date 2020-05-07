"""
Video labeling util functions. Called after the data is collected. Bounding boxes are drawn
on the video frames.
"""
import numpy as np
import pandas as pd
import skvideo.io

from PIL import Image
from PIL import ImageDraw


def get_rect(x, y, width, height, angle):
    """
    Generates the vertices of a rectangle with the specified center coordinates, width, height
    and orientation angle. All units are in pixel coordinates.

    :param int x: Center x location.
    :param int y: Center y location.
    :param int width: Width of the bounding box.
    :param int height: Height of the bounding box.
    :param int angle: (in degrees) Orientation angle of the bounding box.
    :return: Vertex coordinates.
    :rtype: list
    """
    rect = np.array([(-width // 2, -height // 2), (width // 2, -height // 2),
                     (width // 2, height // 2), (-width // 2, height // 2),
                     (-width // 2, -height // 2)])
    theta = np.pi/180*angle
    R = np.array([[np.cos(theta), -np.sin(theta)],
                  [np.sin(theta), np.cos(theta)]])
    offset = np.array([x, y])
    transformed_rect = np.dot(rect, R) + offset
    return transformed_rect


def label_video(log_file, video_file, out_file):
    """
    Video labeling function. Called at the end of the data collection loop. Takes the video
    and draws the bounding boxes at the actor locations on the frames.

    :param str log_file: Actor log file with bounding box locations of the visible actors.
    :param str video_file: Video file containing the captured frames.
    :param str out_file: Output video file with bounding boxes.
    :return: None
    """
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
            rect = get_rect(x=x, y=y, width=w, height=h, angle=-phi)
            draw.line([tuple(p) for p in rect], fill="red", width=3)
        labeled_frame = np.asarray(img)
        processed_video.writeFrame(labeled_frame)

    processed_video.close()
