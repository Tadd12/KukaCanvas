#!/usr/bin/env python3
"""
This script takes multiple point arrays (contours) and generates a KRL
source file for a 6-axis KUKA robot to draw the outlines with a pencil.
Contours are first smoothed by re-interpolating them with a parametric spline,
ensuring smooth drawn curves. The generated KRL file uses standard KUKA
guidelines with proper header lines and instructions.
"""

import numpy as np
from scipy.interpolate import splprep, splev

# ===========================================================
# Configuration Parameters (adjust as needed)
# ===========================================================
# Pencil and robot motion parameters (in mm)
TRAVEL_Z = 10.0  # Z height when pencil is up (travel mode)
DRAW_Z = 0.0  # Z height when pencil is down (drawing mode)
HOME_X = 0.0  # Home X coordinate
HOME_Y = 0.0  # Home Y coordinate

# Paper dimensions (in mm)
LENGTH_X = 210.0  # Length of the paper (e.g., A4 width)
HEIGHT_Y = 297.0  # Height of the paper (e.g., A4 height)

SCALING_METHOD = "keep_ratio" # "keep_ratio", "scale_to_paper"

BORDER_WIDTH_X = 5.0
BORDER_WIDTH_Y = 5.0

# Spline smoothing parameters
SMOOTHING_FACTOR = 0.5  # Increase to smooth more (0 forces interpolation through all points)
POINT_DISTANCE = 5  # Point Distance in mm


# ===========================================================
# Spline Interpolation Function
# ===========================================================
def smooth_contour(contour, smoothing=SMOOTHING_FACTOR, distance=POINT_DISTANCE):
    """
    Smooth a 2D contour using parametric spline interpolation.

    Parameters:
      contour (np.array): An (N, 2) array of (x, y) points.
      smoothing (float): Smoothing factor for splprep. Use 0 to force interpolation
                         through every point.

    Returns:
      np.array: An (num_points, 2) array of smoothed (x, y) points.
    """
    # Extract x and y coordinates.
    x = contour[:, 0]
    y = contour[:, 1]

    # Compute cumulative arc length to parameterize the contour.
    distances = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2)
    t = np.concatenate(([0], np.cumsum(distances)))
    if t[-1] == 0:
        return contour  # If degenerate, return original
    t /= t[-1]  # Normalize t to [0, 1]

    # Fit a parametric spline to the points.
    tck, _ = splprep([x, y], s=smoothing, u=t)

    # Generate new, uniformly spaced parameter values.
    mean = np.mean(np.sqrt(np.square(contour[:-1, 0] - contour[1:, 0]) + np.square(contour[:-1, 1] - contour[1:, 1])))
    num_points = int((len(contour) * mean) / distance)
    u_fine = np.linspace(0, 1, num_points)

    # Evaluate the spline to obtain smoothed coordinates.
    x_smooth, y_smooth = splev(u_fine, tck)
    smoothed_contour = np.vstack((x_smooth, y_smooth)).T
    return smoothed_contour


# ===========================================================
# KRL Generation Function
# ===========================================================
def generate_krl_script(contours, save=True, filename="draw.krl"):
    """
    Generates a KUKA KRL source file that instructs a 6-axis robot to draw
    the lines defined by the given (smoothed) contours.

    Each contour is drawn as follows:
      - A PTP move (pencil up) to the contour's start.
      - A LIN move to lower the pencil to DRAW_Z and set the pencil output.
      - A series of LIN moves to draw the contour.
      - A LIN move to lift the pencil (return to TRAVEL_Z) and turn off the pencil output.

    Parameters:
      contours (list of np.array): Each element is an (N,2) array containing
                                   points [X, Y] in the robot coordinate system.
      save (bool): Whether to save the KRL source code to a file.
      filename (str): Name of the output KRL source file.
    """
    krl_lines = []
    # KUKA header and program definition
    krl_lines.append("&ACCESS RVP")
    krl_lines.append("&REL 1")
    krl_lines.append("DEF DRAW_PICTURE()")
    krl_lines.append("; Define home position (pencil up)")
    krl_lines.append("POS p_home")
    krl_lines.append(
        f"p_home = {{X {HOME_X:.2f}, Y {HOME_Y:.2f}, Z {TRAVEL_Z:.2f}, A 0, B 0, C 0}}"
    )
    krl_lines.append("")
    krl_lines.append("")
    krl_lines.append("BAS(#initmov, 0)")
    krl_lines.append("BAS(#tool, 3)")
    krl_lines.append("BAS(#base, 3)")
    krl_lines.append("")
    krl_lines.append("PTP $axis_act")
    krl_lines.append("PTP p_home")
    krl_lines.append("")

    # Determine the maximum dimensions across all contours
    max_x = np.max([np.max(cont[:, 0]) for cont in contours])
    max_y = np.max([np.max(cont[:, 1]) for cont in contours])

    min_x = np.min([np.min(cont[:, 0]) for cont in contours])
    min_y = np.min([np.min(cont[:, 1]) for cont in contours])

    height_without_border = HEIGHT_Y - 2*BORDER_WIDTH_Y
    width_without_border = LENGTH_X - 2*BORDER_WIDTH_X

    # Calculate the scaling factor to maintain aspect ratio
    scale_x = (LENGTH_X - 2 * BORDER_WIDTH_X) / (max_x - min_x)
    scale_y = (HEIGHT_Y - 2 * BORDER_WIDTH_Y) / (max_y - min_y)
    scale = min(scale_x, scale_y)

    # scale Points
    match SCALING_METHOD:
        case "keep_ratio":
            for cont in contours:
                #cont[:] -= [min_x, min_y]
                pass


        case "scale_to_paper":
            pass
        case _:
            print("WARNING: Unknown SCALING_METHOD {}".format(SCALING_METHOD))


    # Process each contour
    for i, contour in enumerate(contours):
        if contour.size == 0:
            continue

        # Smooth (interpolate) the contour
        smooth_pts = smooth_contour(contour)
        print(f"Writing Contour {i+1} with {len(smooth_pts)} points")

        krl_lines.append(f"; ----- Contour {i + 1} -----")

        # Scale points to fit on the paper
        smooth_pts[:, 0] = smooth_pts[:, 0] * scale + BORDER_WIDTH_X
        smooth_pts[:, 1] = smooth_pts[:, 1] * scale + BORDER_WIDTH_Y

        # Move with pencil up (PTP) to starting point.
        start_x, start_y = smooth_pts[0]
        krl_lines.append(
            f"PTP {{X {start_x:.2f}, Y {start_y:.2f}, Z {TRAVEL_Z:.2f}, A 0, B 0, C 0}}"
        )
        # Lower the pencil using a LIN move.
        krl_lines.append(
            f"LIN {{X {start_x:.2f}, Y {start_y:.2f}, Z {DRAW_Z:.2f}, A 0, B 0, C 0}}"
        )
        krl_lines.append(
            "WAIT SEC 0.1"
        )
        # Draw the contour with LIN moves.
        for pt in smooth_pts[1:]:
            x, y = pt
            krl_lines.append(
                f"LIN {{X {x:.2f}, Y {y:.2f}, Z {DRAW_Z:.2f}, A 0, B 0, C 0}} C_DIS"
            )
        # End the contour by lifting the pencil.
        last_x, last_y = smooth_pts[-1]
        krl_lines.append(
            f"LIN {{X {last_x:.2f}, Y {last_y:.2f}, Z {TRAVEL_Z:.2f}, A 0, B 0, C 0}}"
        )
        krl_lines.append("")

    # Return to home position at the end.
    krl_lines.append("PTP p_home")
    krl_lines.append("END")


    if save:
        # Write the KRL source code to the output file.
        with open(filename, "w") as f:
            for line in krl_lines:
                f.write(line + "\n")
        print(f"KRL script saved to '{filename}'")

    return krl_lines

# ===========================================================
# Main Script Execution
# ===========================================================
def main():
    # Example: define two sample contours (as point arrays in robot coordinates)
    # In a real application, these would come from your image/edge processing routines.
    contour1 = np.array([
        [100, 100],
        [150, 120],
        [200, 110],
        [250, 130],
        [300, 125]
    ])
    contour2 = np.array([
        [300, 200],
        [320, 220],
        [340, 210],
        [360, 230],
        [380, 220],
        [400, 215]
    ])

    # Collect contours into a list.
    contours = [contour1, contour2]

    # Generate the KRL source file.
    generate_krl_script(contours, filename="draw.src")


if __name__ == "__main__":
    main()
