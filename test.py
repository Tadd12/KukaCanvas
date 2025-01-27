# Redefining the correct smiley face path

# Circle face (approximate with discrete points)
face_circle = [(100 + 90 * np.cos(theta), 100 + 90 * np.sin(theta), 0) for theta in np.linspace(0, 2 * np.pi, 100)]

# Left eye
left_eye = [(70 + 10 * np.cos(theta), 130 + 10 * np.sin(theta), 0) for theta in np.linspace(0, 2 * np.pi, 30)]

# Right eye
right_eye = [(130 + 10 * np.cos(theta), 130 + 10 * np.sin(theta), 0) for theta in np.linspace(0, 2 * np.pi, 30)]

# Smile curve (Bezier-like arc)
smile = [(60 + t * 80, 70 + 30 * np.sin(t * np.pi), 0) for t in np.linspace(0, 1, 50)]

# Combining all paths in proper drawing order
smiley_path = face_circle + left_eye + right_eye + smile + [(60, 70, 50)]  # Lift pen at end

# Extract coordinates for plotting
x_coords = [p[0] for p in smiley_path]
y_coords = [p[1] for p in smiley_path]
z_coords = [p[2] for p in smiley_path]

# Set up figure for animation
fig, ax = plt.subplots(figsize=(6, 6))
ax.set_xlim(0, 200)
ax.set_ylim(0, 200)
ax.set_xticks([])
ax.set_yticks([])
ax.set_title("KUKA Robot Drawing Smiley Face")

# Plot elements
line, = ax.plot([], [], 'k-', lw=2)  # Path line
robot_tip, = ax.plot([], [], 'ro', markersize=8)  # Robot tool marker
pen_state = ax.text(10, 190, "Pen: Down", fontsize=12, color="green")

# Initialization function
def init():
    line.set_data([], [])
    robot_tip.set_data([], [])
    pen_state.set_text("Pen: Down")
    return line, robot_tip, pen_state

# Update function for animation
def update(frame):
    x_data = x_coords[:frame]
    y_data = y_coords[:frame]
    line.set_data(x_data, y_data)

    # Update robot tip position
    robot_tip.set_data(x_coords[frame-1], y_coords[frame-1])

    # Check if pen is lifted
    if z_coords[frame-1] > 0:
        pen_state.set_text("Pen: Up")
        pen_state.set_color("red")
    else:
        pen_state.set_text("Pen: Down")
        pen_state.set_color("green")

    return line, robot_tip, pen_state

# Create animation
ani = animation.FuncAnimation(fig, update, frames=len(smiley_path), init_func=init, blit=True, interval=50)

# Save the animation as a video file
video_filename = "/mnt/data/kuka_smiley_drawing.mp4"
ani.save(video_filename, writer="ffmpeg", fps=20)

# Display the video file
video_filename

