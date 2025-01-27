import svgpathtools
import numpy as np
import matplotlib.pyplot as plt

# === CONFIGURATION ===
SVG_FILE = "smile.svg" # Input SVG file
OUTPUT_KRL = "robot_drawing.src"  # Output KUKA KRL file

# Robot workspace limits (adjust as needed)
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
    """ Breaks arcs and Bezier curves into discrete linear segments """
    points = [segment.point(t) for t in np.linspace(0, 1, num_points)]
    return [(p.real, p.imag) for p in points]


def svg_to_krl(svg_file, output_krl):
    """ Converts SVG paths to KUKA KRL format, handling arcs and curves """

    paths, attributes = svgpathtools.svg2paths(svg_file)
    krl_commands = [
        "&ACCESS RVP",
        "&REL 1",
        "&PARAM TEMPLATE = CIRC",
        "&PARAM EDITMASK = *",
        "DEF DRAWING()",
        "$BASE = {FRAME: X 0, Y 0, Z 0, A 0, B 0, C 0}",  # Set base
        "$TOOL = {FRAME: X 0, Y 0, Z 100, A 0, B 0, C 0}",  # Define tool
        "$VEL.CP = 0.1",  # Set speed
        "$ACC.CP = 0.2",  # Set acceleration
    ]

    all_points = []  # Store points for visualization

    for path in paths:
        first_point = True  # Used to lift/lower pen correctly

        for segment in path:
            if isinstance(segment, svgpathtools.Line):
                points = [(segment.start.real, segment.start.imag), (segment.end.real, segment.end.imag)]
            elif isinstance(segment, svgpathtools.Arc):
                points = interpolate_curve(segment, ARC_POINTS)
            elif isinstance(segment, (svgpathtools.CubicBezier, svgpathtools.QuadraticBezier)):
                points = interpolate_curve(segment, ARC_POINTS)
            else:
                continue  # Ignore other elements

            for i, (x, y) in enumerate(points):
                x_robot = X_MIN + x * X_SCALE
                y_robot = Y_MIN + (SVG_HEIGHT - y) * Y_SCALE  # Flip Y-axis


                if first_point:
                    all_points.append((x_robot, y_robot, 1))
                    krl_commands.append(f"PTP {{X {x_robot}, Y {y_robot}, Z {Z_SAFE}, A 0, B 0, C 0}}")
                    krl_commands.append("WAIT SEC 0.5")  # Short delay
                    krl_commands.append(f"LIN {{X {x_robot}, Y {y_robot}, Z {Z_DRAW}, A 0, B 0, C 0}}")  # Lower pen
                    first_point = False
                else:
                    all_points.append((x_robot, y_robot, 0))
                    krl_commands.append(f"LIN {{X {x_robot}, Y {y_robot}, Z {Z_DRAW}, A 0, B 0, C 0}} C_DIS")

        krl_commands.append(f"LIN {{X {x_robot}, Y {y_robot}, Z {Z_SAFE}, A 0, B 0, C 0}}")
        krl_commands.append("WAIT SEC 0.5")  # Short delay before next path

    krl_commands.append("PTP {X 0, Y 0, Z 200, A 0, B 0, C 0}")
    krl_commands.append("END")

    with open(output_krl, "w") as f:
        f.write("\n".join(krl_commands))

    print(f"KRL script saved as {output_krl}")
    return all_points  # Return points for visualization


# === RUN THE CONVERSION ===
all_points = svg_to_krl(SVG_FILE, OUTPUT_KRL)

# === PLOT THE PATH ===
plt.figure(figsize=(6, 6))
paths = []
for point in all_points:
    if point[2]:
        paths.append([])
        pass
    paths[-1].append(point[:2])
for path in paths:
    plt.plot(*zip(*path), 'o-', markersize=3, linewidth=1)
plt.xlabel("X (mm)")
plt.ylabel("Y (mm)")
plt.title("Robot Path Visualization from SVG")
plt.grid(True)
plt.show()
