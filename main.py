import svgpathtools
import numpy as np
import matplotlib.pyplot as plt

# === CONFIGURATION ===
SVG_FILE = "Mediamodifier-Design.svg"  # Input SVG file
OUTPUT_KRL = "robot_drawing.src"  # Output KUKA KRL file (must end in .src for the controller)

# Robot workspace limits (adjust to suit your robot’s actual table/work area)
X_MIN, X_MAX = 50, 300  # X-axis range in mm
Y_MIN, Y_MAX = 50, 200  # Y-axis range in mm
Z_SAFE = 50  # Pen-up height
Z_DRAW = 0  # Pen-down height

# Scaling factors (adjust based on your SVG dimensions)
SVG_WIDTH, SVG_HEIGHT = 500, 500  # Change based on your SVG file's canvas size
X_SCALE = (X_MAX - X_MIN) / SVG_WIDTH
Y_SCALE = (Y_MAX - Y_MIN) / SVG_HEIGHT

# Number of points to approximate arcs/circles
ARC_POINTS = 30


def interpolate_curve(segment, num_points=ARC_POINTS):
    """
    Break arcs and Bezier curves into discrete linear segments.
    This helps convert complex curves into multiple small lines
    which the robot can follow with LIN movements.
    """
    points = [segment.point(t) for t in np.linspace(0, 1, num_points)]
    return [(p.real, p.imag) for p in points]


def svg_to_krl(svg_file, output_krl):
    """
    Converts SVG paths to KUKA KRL format, handling arcs and curves by
    discretizing them into multiple linear segments.
    """
    paths, attributes = svgpathtools.svg2paths(svg_file)

    # -- KRL HEADER BLOCK --
    # The following lines are valid KRL “expert” header directives.
    # &ACCESS / &REL / &PARAM lines help with file access and versioning inside the KUKA HMI.
    krl_commands = [
        "&ACCESS RVP",
        "&REL 1",
        "&PARAM TEMPLATE = CIRC",
        "&PARAM EDITMASK = *",
        "DEF DRAWING()",  # Program definition
        "$BASE = {FRAME: X 0, Y 0, Z 0, A 0, B 0, C 0}",  # Define or override BASE
        "$TOOL = {FRAME: X 0, Y 0, Z 100, A 0, B 0, C 0}",  # Define or override TOOL
        # Adjust velocity/acceleration as needed; these are in mm/sec (and mm/sec^2) for cartesian motions.
        "$VEL.CP = 0.1",
        "$ACC.CP = 0.2",
    ]

    # If your robot requires initializing motion defaults, you can also include:
    # krl_commands.append("BAS(#INITMOV,0)")
    # krl_commands.append("BAS(#CP_PARAMS,0)")
    #
    # However, not all configurations require BAS(#INITMOV,0).
    # It depends on how your KRC is set up.

    all_points = []  # Collect points for plotting/visualization

    for path in paths:
        first_point = True  # We'll use this to do a "pen-down" only at the start of each path

        for segment in path:
            # 1) Handle lines
            if isinstance(segment, svgpathtools.Line):
                points = [
                    (segment.start.real, segment.start.imag),
                    (segment.end.real, segment.end.imag),
                ]

            # 2) Handle arcs
            elif isinstance(segment, svgpathtools.Arc):
                points = interpolate_curve(segment, ARC_POINTS)

            # 3) Handle bezier curves
            elif isinstance(segment, (svgpathtools.CubicBezier, svgpathtools.QuadraticBezier)):
                points = interpolate_curve(segment, ARC_POINTS)

            else:
                # Ignore other elements like Move commands, empty segments, etc.
                continue

            # Now convert these 2D points to robot coordinates
            for i, (x, y) in enumerate(points):
                # Basic scaling and Y flip if desired
                x_robot = X_MIN + x * X_SCALE
                y_robot = Y_MIN + (SVG_HEIGHT - y) * Y_SCALE  # Flip Y-axis
                # If your robot’s Y-axis is not “flipped,” remove the (SVG_HEIGHT - y).

                if first_point:
                    # Move robot in PTP mode above the first point (pen up).
                    all_points.append((x_robot, y_robot, 1))  # '1' indicates pen-lift in the visual
                    krl_commands.append(f"PTP {{X {x_robot:.3f}, Y {y_robot:.3f}, Z {Z_SAFE:.3f}, A 0, B 0, C 0}}")
                    krl_commands.append("WAIT SEC 0.5")  # Just a small pause (optional)

                    # Lower the pen with a linear move to pen-down height
                    krl_commands.append(f"LIN {{X {x_robot:.3f}, Y {y_robot:.3f}, Z {Z_DRAW:.3f}, A 0, B 0, C 0}}")
                    first_point = False

                else:
                    # Continue drawing with a linear move.
                    # "C_DIS" for continuous path; remove if your controller doesn’t support it or you want exact stops.
                    all_points.append((x_robot, y_robot, 0))
                    krl_commands.append(
                        f"LIN {{X {x_robot:.3f}, Y {y_robot:.3f}, Z {Z_DRAW:.3f}, A 0, B 0, C 0}} C_DIS"
                    )

        # When this path is done, lift the pen up before moving to the next path
        # x_robot / y_robot will be the last position from the loop
        krl_commands.append(f"LIN {{X {x_robot:.3f}, Y {y_robot:.3f}, Z {Z_SAFE:.3f}, A 0, B 0, C 0}}")
        krl_commands.append("WAIT SEC 0.5")  # Optional pause before the next shape

    # After all paths, move safely to home or some parked position
    krl_commands.append("PTP {X 0, Y 0, Z 200, A 0, B 0, C 0}")
    krl_commands.append("END")  # End of the KUKA program

    # Write everything out to the .src file
    with open(output_krl, "w") as f:
        f.write("\n".join(krl_commands))
        f.write("\n")  # End with newline for cleanliness

    print(f"KRL script saved as {output_krl}")
    return all_points  # Return for optional plotting or debugging


# === RUN THE CONVERSION ===
all_points = svg_to_krl(SVG_FILE, OUTPUT_KRL)

# === PLOT THE PATH ===
plt.figure(figsize=(6, 6))
paths = []

# Separate each path based on the pen-up marker (point[2] == 1)
for point in all_points:
    if point[2] == 1:
        # Start a new path
        paths.append([])
    paths[-1].append(point[:2])  # (x, y)

# Plot each path in a loop
for path in paths:
    plt.plot(*zip(*path), 'o-', markersize=3, linewidth=1)

plt.xlabel("X (mm)")
plt.ylabel("Y (mm)")
plt.title("Robot Path Visualization from SVG")
plt.grid(True)
plt.axis('equal')
plt.show()
