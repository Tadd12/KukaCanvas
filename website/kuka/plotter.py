import numpy as np
import plotly.graph_objects as go
from numpy import ndarray


def str_to_point(line: str) -> list:
    point = line[:-1].split("{")[1].split("}")[0]
    point = [float(p.split(" ")[1]) for p in point.split(", ")]
    return point

def extract(lines: list) -> list[np.ndarray]:
    points = []

    for line in lines:
        if line.startswith("; ----- Contour"):
            points.append([])
        elif not "{" in line:
            continue
        elif line.startswith('PTP') or line.startswith('LIN'):
            points[-1].append(str_to_point(line))
    points = [np.array(p) for p in points]
    return points

def extract_file(filename: str) -> list[np.ndarray]:

    with open(filename, 'r') as f:
        return extract(f.readlines())

def plot_cont(points: list|ndarray, fig: go.Figure = None, show: bool = True) -> None:

    if fig is None:
        fig = go.Figure()

    # Add a trace for each contour
    for idx, contour in enumerate(points):
        contour = np.asarray(contour)
        fig.add_trace(go.Scatter(
            x=contour[:, 0],
            y=contour[:, 1],
            mode='lines',
            name=f"Contour {idx + 1}"
        ))

    # Update layout with title, axis labels, and grid lines
    fig.update_layout(
        title="Filtered & Smoothed Contours",
        xaxis_title="X (pixels)",
        yaxis_title="Y (pixels)",
        width=800,
        height=800
    )
    # Invert the y-axis so that the origin is at the top-left
    fig.update_yaxes(autorange='reversed', showgrid=True)
    fig.update_xaxes(showgrid=True)

    if show:
        fig.show()

def plot_path(points: list|ndarray, fig: go.Figure = None, show: bool = True) -> None:

    if fig is None:
        fig = go.Figure()
    last_point = None

    # Lists to store non-move and move traces separately.
    non_move_traces = []
    move_traces = []

    # Flags to ensure each legend entry is added only once.
    start_added = False
    contour_added = False
    end_added = False
    move_added = False

    for contour in points:
        contour = np.asarray(contour)
        # If there is a previous contour, record the dashed "Move" trace.
        if last_point is not None:
            move_trace = go.Scatter(
                x=[last_point[0], contour[0, 0]],
                y=[last_point[1], contour[0, 1]],
                mode='lines',
                line=dict(dash='dash'),
                name="Move",
                showlegend=not move_added
            )
            move_traces.append(move_trace)
            move_added = True

        # Plot the starting point (green marker)
        start_trace = go.Scatter(
            x=[contour[0, 0]],
            y=[contour[0, 1]],
            mode='markers',
            marker=dict(color='green', size=10),
            name="Start",
            showlegend=not start_added
        )
        non_move_traces.append(start_trace)
        start_added = True

        # Plot the contour path (line with markers), if available.
        if contour.shape[0] > 1:
            contour_trace = go.Scatter(
                x=contour[1:, 0],
                y=contour[1:, 1],
                mode='lines+markers',
                marker=dict(size=2),
                name="Contour",
                showlegend=not contour_added
            )
            non_move_traces.append(contour_trace)
            contour_added = True

        # Plot the ending point (red marker)
        end_trace = go.Scatter(
            x=[contour[-1, 0]],
            y=[contour[-1, 1]],
            mode='markers',
            marker=dict(color='red', size=10),
            name="End",
            showlegend=not end_added
        )
        non_move_traces.append(end_trace)
        end_added = True

        last_point = contour[-1]

    # Add non-move traces first...
    for trace in non_move_traces:
        fig.add_trace(trace)
    # ...then add move traces so they are drawn on top.
    for trace in move_traces:
        fig.add_trace(trace)

    fig.update_layout(
        title="Robot Path",
        xaxis_title="X (mm)",
        yaxis_title="Y (mm)",
        width=800,
        height=800
    )
    # Invert the y-axis so that the origin is at the top-left
    fig.update_yaxes(autorange='reversed', showgrid=True)
    fig.update_xaxes(showgrid=True)

    if show:
        fig.show()

if __name__ == '__main__':
    points = extract_file("../../kuka files/draw.src")
    plot_cont(points)
    plot_path(points)