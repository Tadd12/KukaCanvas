#!/usr/bin/env python3
import sys
import numpy as np
from PIL import Image, ImageFilter, ImageOps
import matplotlib.pyplot as plt
from skimage import measure, morphology

import website.kuka.converter

# ===========================
# Configuration Variables
# ===========================
IMAGE_PATH = "shibu.png"  # <-- Update with the path to your image file
THRESHOLD_VALUE = 32  # Threshold for binary conversion (adjust as needed)
BORDER_MARGIN = 5  # Margin (in pixels) around the image to discard contours touching the border
SMOOTHING_WINDOW = 5  # Window size for smoothing the contour lines
MIN_CONTOUR_LENGTH = 50  # Minimum number of points for a contour to be considered


# ===========================
# Smoothing Function
# ===========================
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


# ===========================
# Edge Extraction Function
# ===========================
def extract_edges_as_point_arrays(image_path, threshold_value):
    """
    Loads an image using Pillow, composites it onto a white background,
    converts it to grayscale, applies edge detection, and then performs
    morphological cleaning to reduce noise and spurious edges. Finally,
    it extracts and smooths the contours.

    Parameters:
      image_path (str): Path to the input image.
      threshold_value (int): Threshold for converting the edge image to binary.

    Returns:
      list: A list of NumPy arrays, each representing a (smoothed) contour as an array of (x, y) points.
    """
    # Load the image and ensure it has an alpha channel
    try:
        image = Image.open(image_path).convert("RGBA")
    except Exception as e:
        sys.exit("Error opening image: " + str(e))

    image = ImageOps.expand(image, border=20)

    # Composite onto a white background (so transparent regions become white)
    white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
    image = Image.alpha_composite(white_bg, image)

    # Get image dimensions (Pillow uses (width, height))
    width, height = image.size

    # Convert to grayscale
    gray = image.convert("L")

    # Apply edge enhancement and edge detection filters
    edge = gray.filter(ImageFilter.EDGE_ENHANCE).filter(ImageFilter.FIND_EDGES)

    # Convert the edge image to a NumPy array
    edge_array = np.array(edge)

    # Create a binary image using the threshold value
    binary = edge_array > threshold_value

    # --- Morphological Processing ---
    # Use a disk-shaped structuring element to close small gaps in the edges.
    binary_clean = morphology.closing(binary, morphology.disk(3))

    # Remove small objects (noise) that are unlikely to be part of a significant edge.
    binary_clean = morphology.remove_small_objects(binary_clean, min_size=10)

    # Optionally, fill small holes (if needed)
    binary_clean = morphology.remove_small_holes(binary_clean, area_threshold=20)

    # --- Contour Extraction ---
    # Adjust the level (e.g., 0.8) to extract the most relevant contours.
    raw_contours = measure.find_contours(binary_clean.astype(float), level=0.999)

    point_arrays = []
    for contour in raw_contours:
        # The contours are returned as (row, col) coordinates.
        # Flip to get (x, y) coordinates.
        points = np.fliplr(contour)

        # Remove contours that touch the image border.
        if (np.min(points[:, 0]) < BORDER_MARGIN or
                np.max(points[:, 0]) > (width - BORDER_MARGIN) or
                np.min(points[:, 1]) < BORDER_MARGIN or
                np.max(points[:, 1]) > (height - BORDER_MARGIN)):
            continue

        # Remove contours that are too short to be significant.
        if len(points) < MIN_CONTOUR_LENGTH:
            continue

        # Remove inner contours (clockwise)
        if np.sum((points[1:, 0] - points[:-1, 0]) * (points[1:, 1] + points[:-1, 1])) <= 0:
            continue

        # Smooth the contour line.
        points_smoothed = smooth_contour(points, window_size=SMOOTHING_WINDOW)

        point_arrays.append(points_smoothed)

    return point_arrays


# ===========================
# Plotting Function
# ===========================
def plot_contours(contours):
    """
    Plots a list of contours (each contour is an array of (x,y) points) using Matplotlib.
    """
    plt.figure(figsize=(8, 8))
    for idx, contour in enumerate(contours):
        plt.plot(contour[:, 0], contour[:, 1], label=f"Contour {idx + 1}")
    plt.xlabel("X (pixels)")
    plt.ylabel("Y (pixels)")
    plt.title("Filtered & Smoothed Contours")
    plt.gca().invert_yaxis()  # Invert Y-axis so that the origin is at the top-left
    plt.grid(True)
    plt.show()


# ===========================
# Main Script Execution
# ===========================
def main():
    contours = extract_edges_as_point_arrays(IMAGE_PATH, THRESHOLD_VALUE)

    # Print the extracted contours (for debugging)
    for idx, contour in enumerate(contours):
        print(f"Contour {idx}: {len(contour)} points")
        print("-" * 40)

    # Plot the extracted contours
    plot_contours(contours)

    website.kuka.converter.generate_krl_script(contours, filename="draw.src")


if __name__ == "__main__":
    main()
