import time

import cv2
import cv2 as cv
from datetime import datetime
from utils.data_preprocessing import Preprocess
import numpy as np
import math
# from sklearn.cluster import KMeans


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
        self.now = time.strftime("%H:%M:%S")
        self.font = cv.FONT_HERSHEY_SIMPLEX
        self.org = (10, 100)
        self.fontScale = 2
        self.color = (255, 255, 0)
        self.thickness = 7
        self.date = datetime.now()

       

        self.counting_images = 0

    def process_image(self, source):
        # Initialize self.original at the beginning of the method
        self.original = source.copy()
        try:
            pre = Preprocess(source)
            # Proceed with the existing logic to modify self.original as needed
            self.output_path, _, _ = pre.checkFolder()
            self.upscale = pre.SuperResolution()

            filtered_image = cv2.ximgproc.anisotropicDiffusion(
                self.upscale, alpha=0.0001, K=50, niters=200
            )

            self.gray = cv2.cvtColor(filtered_image, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2, tileGridSize=(3, 3))
            self.gray = clahe.apply(self.gray)

            # It seems self.original is redefined here, which is okay as it has been defined earlier
            self.original = cv.resize(source, (self.upscale.shape[1], self.upscale.shape[0]))

            self.esrc = source.copy()
            self.ed = cv.ximgproc.createEdgeDrawing()
            self.EDParams = cv.ximgproc_EdgeDrawing_Params()
            self.EDParams.MinPathLength = 50
            self.EDParams.PFmode = False
            self.EDParams.MinLineLength = 10
            self.EDParams.NFAValidation = True

            self.ed.setParams(self.EDParams)
            self.ed.detectEdges(self.gray)
            self.ellipses = self.ed.detectEllipses()

            self.count_circle = 0
            if self.ellipses is not None:
                size_threshold = 4.5
                filtered_ellipses = filter_duplicate_ellipses(self.ellipses, size_threshold)

                for i, ellipse in enumerate(filtered_ellipses):
                    center, axes, angle = (int(ellipse[0][0]), int(ellipse[0][1])), (int(ellipse[0][2]) + int(ellipse[0][3]), int(ellipse[0][2]) + int(ellipse[0][4])), ellipse[0][5]
                    cv.ellipse(self.original, center, axes, angle, 0, 360, self.color, 2, cv.LINE_AA)
                    self.count_circle += 1
                    
            return self.original, self.count_circle, "finishing operations"
        except Exception as error:
            print(error)
            # self.original is already defined, so we can safely return it
            return self.original, 0, "No Trucks found"