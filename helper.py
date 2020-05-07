import numpy as np


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
