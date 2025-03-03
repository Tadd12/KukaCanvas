import cv2
import numpy as np
from PIL import ImageOps
from PIL import Image
from skimage import measure


def smooth_contour(contour, window_size=5):
    if len(contour) < window_size:
        return contour

    kernel = np.ones(window_size) / window_size
    pad = window_size // 2

    padded_x = np.pad(contour[:, 0], pad_width=pad, mode='edge')
    padded_y = np.pad(contour[:, 1], pad_width=pad, mode='edge')

    smoothed_x = np.convolve(padded_x, kernel, mode='valid')
    smoothed_y = np.convolve(padded_y, kernel, mode='valid')

    return np.stack((smoothed_x, smoothed_y), axis=-1)

def process_image(image_path, blur, blockSize, C):
    image = Image.open(image_path).convert("RGBA")
    image = ImageOps.expand(image, border=20)

    white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
    pil_image = Image.alpha_composite(white_bg, image)

    image_np = np.array(pil_image)
    image_grayscale = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    image_blur = cv2.medianBlur(image_grayscale, blur)
    image_edges = cv2.adaptiveThreshold(
        image_blur,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=blockSize,
        C=C
    )

    raw_contours = measure.find_contours(image_edges.astype(float), level=0.9)
    point_arrays = []
    for contour in raw_contours:
        points = np.fliplr(contour)
        if len(points) < 20:
            continue
        if np.sum((points[1:, 0] - points[:-1, 0]) * (points[1:, 1] + points[:-1, 1])) >= 0:
            continue
        points_smoothed = smooth_contour(points)
        point_arrays.append(points_smoothed)

    # Interpolate the last point to the first point
    for i, arr in enumerate(point_arrays):
        print(f"Processing contour {i+1} with length", len(point_arrays[i]))
        first_point = arr[0]
        print(first_point)
        last_point = arr[-1]
        print(last_point)
        # Calculate the distance between the first and last point

        distance = np.sqrt((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)
        print(distance)
        # If the distance is greater than 0.5, interpolate a new point
        if distance > 0.5:
            # Calculate points along the line between the first and last point with step size 10 % of distance
            new_points = np.linspace(first_point, last_point, int(distance / 0.1))
            # Insert the new points after the last point
            point_arrays[i] = np.insert(arr, -1, new_points[1:], axis=0)
            # Add first point again to close the contour
            point_arrays[i] = np.insert(point_arrays[i], -1, first_point, axis=0)

        print(f"Done adding points to contour {i+1}, now has length", len(point_arrays[i]))



    return point_arrays
