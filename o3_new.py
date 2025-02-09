import sys

import cv2
import numpy as np
from PIL import Image, ImageOps
from skimage import measure

# Load the image and ensure it has an alpha channel
image_path = "coffee.png"
try:
    image = Image.open(image_path).convert("RGBA")
except Exception as e:
    sys.exit("Error opening image: " + str(e))

image = ImageOps.expand(image, border=20)

# Composite onto a white background (so transparent regions become white)
white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
pil_image = Image.alpha_composite(white_bg, image)

# Convert PIL image to NumPy array
image_np = np.array(pil_image)

# Convert image to grayscale
image_grayscale = cv2.cvtColor(image_np, cv2.COLOR_RGBA2GRAY)

# Reduce image noise
image_blur = cv2.medianBlur(image_grayscale, 9)

# Extract edges
image_edges = cv2.adaptiveThreshold(
    image_blur,
    255,
    cv2.ADAPTIVE_THRESH_MEAN_C,
    cv2.THRESH_BINARY,
    blockSize=7,
    C=4
    )


def smooth_contour(contour, window_size=5):
    """
    Smooth a contour using a simple moving-average filter.

    Parameters:
      contour (np.array): An array of shape (N,2) representing the contour points.
      window_size (int): The window size for the moving average.

    Returns:
      np.array: The smoothed contour.
    """
    if len(contour) < window_size:
        return contour

    kernel = np.ones(window_size) / window_size
    pad = window_size // 2

    # Pad x and y using the edge values.
    padded_x = np.pad(contour[:, 0], pad_width=pad, mode='edge')
    padded_y = np.pad(contour[:, 1], pad_width=pad, mode='edge')

    # Perform convolution in 'valid' mode to get an output of the original length.
    smoothed_x = np.convolve(padded_x, kernel, mode='valid')
    smoothed_y = np.convolve(padded_y, kernel, mode='valid')

    return np.stack((smoothed_x, smoothed_y), axis=-1)

# Find contours
raw_contours = measure.find_contours(image_edges.astype(float), level=0.999)

# Convert contours to a list of point arrays
point_arrays = []
for contour in raw_contours:

    points = np.fliplr(contour)

    # Remove contours that are too short to be significant.
    if len(points) < 5:
        continue

    # Remove inner contours (clockwise)
    if np.sum((points[1:, 0] - points[:-1, 0]) * (points[1:, 1] + points[:-1, 1])) <= 0:
        continue

    # Smooth the contour line.
    points_smoothed = smooth_contour(points)
    point_arrays.append(points_smoothed)

# Plot the contours with matplotlib
import matplotlib.pyplot as plt

plt.figure(figsize=(8, 8))
for idx, contour in enumerate(point_arrays):
    plt.plot(contour[:, 0], contour[:, 1], label=f"Contour {idx + 1}")
plt.xlabel("X (pixels)")
plt.ylabel("Y (pixels)")
plt.show()