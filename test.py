#!/usr/bin/env python3
import sys
import numpy as np
from PIL import Image, ImageFilter
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from skimage import measure

# ===========================
# Configuration Variables
# ===========================
IMAGE_PATH = "stick.png"  # <-- Update this with the path to your image file
THRESHOLD_VALUE = 64  # Threshold for binary conversion (adjust as needed)


# ===========================
# Edge Extraction Function
# ===========================
def extract_edges_as_point_arrays(image_path, threshold_value):
    """
    Loads an image using Pillow, applies an edge detection filter, thresholds the image,
    and then extracts the edges as point arrays using scikit-image.

    Parameters:
      image_path (str): Path to the input image.
      threshold_value (int): Threshold for converting the edge image to a binary image.

    Returns:
      list: A list of NumPy arrays, each representing a contour as an array of (x, y) points.
    """
    # Load the image
    try:
        image = Image.open(image_path).convert("RGBA")
    except Exception as e:
        sys.exit("Error opening image: " + str(e))

    # Create a new white background image of the same size
    white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))

    # Composite the image over the white background
    image_with_white_bg = Image.alpha_composite(white_bg, image)

    # Convert image to grayscale
    gray_image = image_with_white_bg.convert("L")

    # Apply an edge detection filter provided by Pillow
    edge_image = gray_image.filter(ImageFilter.EDGE_ENHANCE).filter(ImageFilter.FIND_EDGES)

    # Convert the edge image to a NumPy array
    edge_array = np.array(edge_image)#[:, :, 3]

    # Create a binary image using the threshold value
    binary = edge_array > threshold_value

    # Extract contours using scikit-image's find_contours
    # find_contours returns a list of arrays with (row, col) coordinates.
    raw_contours = measure.find_contours(binary.astype(float), level=0.1, fully_connected="high")

    # Convert each contour from (row, col) to (x, y) coordinates
    point_arrays = []
    for contour in raw_contours:
        # Flip columns and rows so that we have (x, y)
        points = np.fliplr(contour)
        point_arrays.append(points)

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
        # Extract x and y coordinates from the contour array
        x_coords = contour[:, 0]
        y_coords = contour[:, 1]
        # Plot the contour as a line
        plt.plot(x_coords, y_coords, label=f"Contour {idx + 1}")
    plt.xlabel("X (pixels)")
    plt.ylabel("Y (pixels)")
    plt.title("Extracted Edge Contours")
    plt.legend()
    plt.gca().invert_yaxis()  # Invert Y-axis so that the origin is at the top-left
    plt.grid(True)
    plt.show()


def chaikins_corner_cutting(coords, refinements=5):
    coords = np.array(coords)

    for _ in range(refinements):
        L = coords.repeat(2, axis=0)
        R = np.empty_like(L)
        R[0] = L[0]
        R[2::2] = L[1:-1:2]
        R[1:-1:2] = L[2::2]
        R[-1] = L[-1]
        coords = L * 0.75 + R * 0.25

    return coords

# ===========================
# Main Script Execution
# ===========================
def main():
    contours = extract_edges_as_point_arrays(IMAGE_PATH, THRESHOLD_VALUE)[1:]

    # Print the extracted edge point arrays
    for idx, contour in enumerate(contours):
        print(f"Contour {idx}:")
        print(contour)
        print("-" * 40)

    new_count = [chaikins_corner_cutting(contour) for contour in contours]

    # Plot the extracted contours
    plot_contours(new_count)


if __name__ == "__main__":
    main()
