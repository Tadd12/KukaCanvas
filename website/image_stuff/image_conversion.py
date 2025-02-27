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
    image = image.rotate(180)

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
        point_arrays.append(points_smoothed.tolist())  # Convert to list

    all_x = np.concatenate([arr[:, 0] for arr in point_arrays])
    A = np.min(all_x)
    B = np.max(all_x)
    
    fac = A + B
    
    for arr in point_arrays:
      arr[:, 0] = fac - arr[:, 0]
    
    return point_arrays
