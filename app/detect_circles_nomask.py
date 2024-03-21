import cv2
import numpy as np
import logging
from typing import Tuple, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def radius_of_ellipse(major_axis_length: float, minor_axis_length: float) -> float:
    a = abs(major_axis_length)
    b = abs(minor_axis_length)
    ecc = abs(a - b)
    return ecc

def comparing_areas_of_ellipses(ellipse1: Tuple[float, float], ellipse2: Tuple[float, float]) -> float:
    a1, b1 = ellipse1
    a2, b2 = ellipse2
    area1 = np.pi * a1 * b1
    area2 = np.pi * a2 * b2
    return abs(area1 - area2)

def comparing_radius_of_ellipses(axis1: Tuple[float, float], axis2: Tuple[float, float]) -> float:
    radius1 = radius_of_ellipse(axis1[0], axis1[1])
    radius2 = radius_of_ellipse(axis2[0], axis2[1])
    return abs(radius1 - radius2)

def ellipse_distance(ellipse1: Tuple[Tuple[float, ...]], ellipse2: Tuple[Tuple[float, ...]]) -> Tuple[float, float, float]:
    # Extract parameters
    center1, axes1, angle1 = ellipse1[0][:2], ellipse1[0][2:4], ellipse1[0][-1]
    center2, axes2, angle2 = ellipse2[0][:2], ellipse2[0][2:4], ellipse2[0][-1]

    major1, minor1 = axes1
    major2, minor2 = axes2

    radius_diff = comparing_radius_of_ellipses((major1, minor1), (major2, minor2))
    area_diff = comparing_areas_of_ellipses((major1, minor1), (major2, minor2))

    center_distance = np.sqrt(((center1[0] - center2[0]) ** 2) + ((center1[1] - center2[1]) ** 2))
    return center_distance, area_diff, radius_diff

def filter_duplicate_ellipses(ellipses: List[Tuple], distance_threshold: float) -> List[Tuple]:
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
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.color = (255, 255, 0)
        self.thickness = 7
        logger.info("DetectCircle initialized")

    def process_image(self, source: np.ndarray) -> Tuple[np.ndarray, int, str]:
        self.count_circle = 0
        try:
            self.original = source.copy()
            gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 100, 200)

            self.ed = cv2.ximgproc.createEdgeDrawing()
            self.EDParams = cv2.ximgproc_EdgeDrawing_Params()
            self.ed.setParams(self.EDParams)
            self.ed.detectEdges(edges)

            self.ellipses = self.ed.detectEllipses()

            if self.ellipses is not None:
                size_threshold = 4.5
                filtered_ellipses = filter_duplicate_ellipses(self.ellipses, size_threshold)

                for i, ellipse in enumerate(filtered_ellipses):
                    center, axes, angle = (int(ellipse[0][0]), int(ellipse[0][1])), (int(ellipse[0][2]) + int(ellipse[0][3]), int(ellipse[0][2]) + int(ellipse[0][4])), ellipse[0][5]
                    cv2.ellipse(self.original, center, axes, angle, 0, 360, self.color, 2, cv2.LINE_AA)
                    self.count_circle += 1

                logger.info(f"{self.count_circle} circles detected")
                return self.original, self.count_circle, "Finishing operations"
            else:
                logger.info("No circles found")
                return self.original, 0, "No circles found"

        except Exception as error:
            logger.error(f"Error processing image: {error}")
            return self.original, 0, "Error processing image"