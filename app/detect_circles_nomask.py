import os
import time

import cv2
import cv2 as cv
from threading import Thread
from datetime import datetime
import numpy as np
import math
import pandas as pd
# from sklearn.cluster import KMeans
from matplotlib import pyplot as plt


def radius_of_ellipse(major_axis_length, minor_axis_length):
    # rad = math.sqrt((major_axis_length + minor_axis_length) / math.pi)
    a = abs(major_axis_length)
    b = abs(minor_axis_length)
    ecc = abs(a - b)
    # area1 = math.pi * major_axis_length*minor_axis_length

    return ecc


def comparing_areas_of_epplises(ellipse1, ellipse2):
    # https://math.stackexchange.com/questions/432902/how-to-get-the-radius-of-an-ellipse-at-a-specific-angle-by-knowing-its-semi-majo
    a1, b1 = ellipse1
    a2, b2 = ellipse2
    area1 = math.pi * a1 * b1
    area2 = math.pi * a2 * b2

    if area1 > area2:
        # return abs(area1 - area2)  # math.sqrt((area1) ** 2 - (area2) ** 2)
        return abs(abs(area1) - abs(area2))
    else:
        # return abs(area2 - area1)  # math.sqrt((area2) ** 2 - (area1) ** 2)
        return abs(abs(area2) - abs(area1))


def comapring_radius_of_ellipses(axis1, axis2):
    radius1 = radius_of_ellipse(axis1[0], axis1[1])
    radius2 = radius_of_ellipse(axis2[0], axis2[1])

    return abs(abs(radius1) - abs(radius2))


def ellipse_distance(ellipse1, ellipse2):
    center1_1, center1_2, x1, y1, z1, _ = ellipse1[0]
    center2_1, center2_2, x2, y2, z2, _ = ellipse2[0]
    a1 = x1 + y1
    b1 = x1 + z1

    if a1 > b1:
        pass
    else:
        a1, b1 = b1, a1

    a2 = x2 + y2
    b2 = x2 + z2

    if a2 > b2:
        pass
    else:
        a2, b2 = b2, a2

    major1, minor1 = center1_1 + a1, center1_2 - b1
    major2, minor2 = center2_1 + a2, center2_2 - b2

    radius = comapring_radius_of_ellipses((major1, minor1), (major2, minor2))
    area = comparing_areas_of_epplises((major1, minor1), (major2, minor2))
   

   
  

    return (
        np.sqrt(((center1_1 - center2_1) ** 2) + ((center1_2 - center2_2) ** 2)),
        area,
        radius,
    )


def filter_duplicate_ellipses(
    ellipses, distance_threshold
):
    filtered_ellipses = []
    for elpse in ellipses:
        is_duplicate = False
        for existing in filtered_ellipses:
            (centers, area, radius) = ellipse_distance(elpse, existing)
            if centers <= distance_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            filtered_ellipses.append(elpse)

    return filtered_ellipses
   


class DetectCircle:
    def __init__(self):
        self.count_circle = 0
        self.font = cv.FONT_HERSHEY_SIMPLEX
        self.color = (255, 255, 0)
        self.thickness = 7

    def process_image(self, source):
        self.count_circle = 0
        try:
            self.original = source.copy()
            gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)

            # Apply some basic filtering and edge detection as needed
            # Note: You might need to adjust these preprocessing steps based on your specific use case
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 100, 200)

            # Setup for ellipse detection
            self.ed = cv.ximgproc.createEdgeDrawing()
            self.EDParams = cv.ximgproc_EdgeDrawing_Params()
            self.ed.setParams(self.EDParams)
            self.ed.detectEdges(edges)

            self.ellipses = self.ed.detectEllipses()

            if self.ellipses is not None:
                size_threshold = 4.5  # Adjust size threshold as needed
                filtered_ellipses = filter_duplicate_ellipses(self.ellipses, size_threshold)

                for i, ellipse in enumerate(filtered_ellipses):
                    center, axes, angle = (int(ellipse[0][0]), int(ellipse[0][1])), (int(ellipse[0][2]) + int(ellipse[0][3]), int(ellipse[0][2]) + int(ellipse[0][4])), ellipse[0][5]
                    cv.ellipse(self.original, center, axes, angle, 0, 360, self.color, 2, cv.LINE_AA)
                    self.count_circle += 1

                return self.original, self.count_circle, "finishing operations"
            else:
                return self.original, 0, "No circles found"

        except Exception as error:
            print(error)
            return self.original, 0, "Error processing image"
