#app/detect_circles.py

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
    return (a + b) / 2  # Compute the average radius

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
    center1, axes1, _ = ellipse1[0][:2], ellipse1[0][2:4], ellipse1[0][-1]
    center2, axes2, _ = ellipse2[0][:2], ellipse2[0][2:4], ellipse2[0][-1]

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

def get_average_of_extremes(values: List[float], n: int) -> Tuple[float, float]:
    if len(values) < n:
        n = len(values)
    sorted_values = sorted(values)
    return (np.mean(sorted_values[:n]), np.mean(sorted_values[-n:]))

class DetectCircle:
    def __init__(self):
        self.count_circle = 0
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.colors = {
            'small': (255, 0, 0),  # Red for small circles
            'medium': (0, 255, 0),  # Green for medium circles
            'large': (0, 0, 255)  # Blue for large circles
        }
        self.thickness = 7
        logger.info("DetectCircle initialized")


    def process_image(self, source: np.ndarray) -> Tuple[np.ndarray, int, str]:
        self.count_circle = 0
        try:
            self.original = source.copy()
            image_width = self.original.shape[1]
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

                diameters = [2 * radius_of_ellipse(e[0][2], e[0][3]) for e in filtered_ellipses]
                if not diameters:
                    return self.original, 0, "No circles found"

                avg_min, avg_max = get_average_of_extremes(diameters, 3)
                variation_percentage = (avg_max - avg_min) / avg_max * 100

                segregation = variation_percentage > 30
                if segregation:
                    small_threshold = np.percentile(diameters, 33)
                    large_threshold = np.percentile(diameters, 66)

                label_x_position = image_width - 100  # Adjust based on text length and image size
                label_positions = [(label_x_position, 30), (label_x_position, 60), (label_x_position, 90)]
                label_colors = ['small', 'medium', 'large']

                for ellipse in filtered_ellipses:
                    center, axes, angle = (int(ellipse[0][0]), int(ellipse[0][1])), (int(ellipse[0][2]) + int(ellipse[0][3]), int(ellipse[0][2]) + int(ellipse[0][4])), ellipse[0][5]
                    diameter = 2 * radius_of_ellipse(axes[0] / 2, axes[1] / 2)

                    if segregation:
                        if diameter < small_threshold:
                            color = self.colors['small']
                        elif diameter < large_threshold:
                            color = self.colors['medium']
                        else:
                            color = self.colors['large']
                    else:
                        color = (255, 255, 0)  # Yellow for no segregation

                    cv2.ellipse(self.original, center, axes, angle, 0, 360, color, 1, cv2.LINE_AA)
                    self.count_circle += 1

                    # Prepare the text to be displayed
                    count_text = str(self.count_circle)

                    # Calculate text size to position it roughly in the center of the ellipse
                    (text_width, text_height), _ = cv2.getTextSize(count_text, self.font, 1, 2)

                    # Adjust the text position to be at the center of the ellipse
                    text_x = center[0] - text_width // 2
                    text_y = center[1] + text_height // 2

                    # Put the text on the image
                    cv2.putText(self.original, count_text, (text_x, text_y), self.font, 1, (255, 255, 255), 1, cv2.LINE_AA)
                    #commented out for debugging

                # Annotate labels for segregation
                if segregation:
                    for pos, label_color in zip(label_positions, label_colors):
                        cv2.putText(self.original, label_color, pos, self.font, 0.7, self.colors[label_color], 2, cv2.LINE_AA)
                elif not self.count_circle:
                    label_color = 'no segregation'
                    label_position = (label_x_position, 30)
                    cv2.putText(self.original, label_color, label_position, self.font, 0.7, (255, 255, 0), 2, cv2.LINE_AA)

                if self.count_circle:
                    logger.info(f"{self.count_circle} circles detected")
                    return self.original, self.count_circle, "Finishing operations"
                else:
                    logger.info("No circles found")
                    return self.original, 0, "No circles found"

            else:
                logger.info("No ellipses detected")
                return self.original, 0, "No ellipses detected"

        except Exception as error:
            logger.error(f"Error processing image: {error}")
            return self.original, 0, "Error processing image"
