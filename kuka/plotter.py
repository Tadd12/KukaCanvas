from typing import Any

import numpy as np
from matplotlib import pyplot as plt


def str_to_point(input: str) -> list:
    point = input[:-1].split("{")[1].split("}")[0]
    point = [float(p.split(":")[1]) for p in point.split(",")]
    return point


def extract(filename: str) -> np.ndarray:
    points = []

    with open(filename, 'r') as f:
        for line in f.readlines():
            if line.startswith("; ----- Contour"):
                points.append([])
            elif not "{" in line:
                continue
            elif line.startswith('PTP') or line.startswith('LIN'):
                points[-1].append(str_to_point(line))
        points = [np.array(p) for p in points]
    return points

def plot_cont(filename: str) -> None:
    points = extract(filename)

    plt.figure(figsize=(8, 8))
    for idx, contour in enumerate(points):
        plt.plot(contour[:, 0], contour[:, 1], label=f"Contour {idx + 1}")
    plt.xlabel("X (pixels)")
    plt.ylabel("Y (pixels)")
    plt.title("Filtered & Smoothed Contours")
    plt.legend()
    plt.gca().invert_yaxis()  # Invert Y-axis so that the origin is at the top-left
    plt.grid(True)
    plt.show()

def plot_path(filename: str) -> None:
    points = extract(filename)

    plt.figure(figsize=(8, 8))
    last_point: np.ndarray = None
    for contour in points:
        if last_point is not None:
            plt.plot([last_point[0], contour[0, 0]], [last_point[1], contour[0, 1]], "--", label="Move")
        plt.plot(contour[0, 0], contour[0, 1], "o", color="green")
        plt.plot(contour[1:, 0], contour[1:, 1], "o-")
        plt.plot(contour[-1, 0], contour[-1, 1], "o", color="red")
        last_point = contour[-1]

    plt.xlabel("X (mm)")
    plt.ylabel("Y (mm)")
    plt.title("Robot Path")
    plt.legend()
    plt.gca().invert_yaxis()  # Invert Y-axis so that the origin is at the top-left
    plt.grid(True)
    plt.show()

if __name__ == '__main__':
    plot_cont("../draw.src")
    plot_path("../draw.src")