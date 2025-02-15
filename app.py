import os
import cv2
from flask import Flask, render_template, request, redirect, url_for, send_file
import plotly.express as px
import plotly.io as pio
import numpy as np
from PIL import Image, ImageOps
from skimage import measure

import kuka.converter

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

contours = []
krl_script = ""

@app.route('/')
def index():
    global krl_script
    return render_template('index.html', krl_script=krl_script)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and file.filename.endswith('.png'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        process_image(file_path)
        return redirect(url_for('index'))
    return 'Invalid file format. Please upload a PNG file.'

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

def process_image(image_path):
    global contours
    image = Image.open(image_path).convert("RGBA")
    image = ImageOps.expand(image, border=20)
    image = image.rotate(180)

    # Composite onto a white background (so transparent regions become white)
    white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
    pil_image = Image.alpha_composite(white_bg, image)

    # Convert PIL image to NumPy array
    image_np = np.array(pil_image)

    # Convert image to grayscale
    image_grayscale = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    # Reduce image noise
    image_blur = cv2.medianBlur(image_grayscale, 7)
    # Extract edges
    image_edges = cv2.adaptiveThreshold(
        image_blur,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=3,
        C=1
    )

    # Find contours
    raw_contours = measure.find_contours(image_edges.astype(float), level=0.9)

    # Convert contours to a list of point arrays
    point_arrays = []
    for contour in raw_contours:

        points = np.fliplr(contour)

        # Remove contours that are too short to be significant.
        if len(points) < 20:
            continue

        # Remove outer contours (clockwise)
        if np.sum((points[1:, 0] - points[:-1, 0]) * (points[1:, 1] + points[:-1, 1])) >= 0:
            continue

        # Smooth the contour line.
        points_smoothed = smooth_contour(points)
        point_arrays.append(points_smoothed)

    contours = point_arrays

@app.route('/plot', methods=['GET'])
def plot():
    global contours
    fig = px.line()
    for idx, contour in enumerate(contours):
        fig.add_scatter(x=contour[:, 0], y=contour[:, 1], mode='lines', name=f"Contour {idx + 1}")
    plot_html = pio.to_html(fig, full_html=False)
    return plot_html

@app.route('/remove_contour', methods=['POST'])
def remove_contour():
    global contours
    index = int(request.form.get('contour_index'))-1
    if 0 <= index < len(contours):
        contours.pop(index)
    return redirect(url_for('index'))

@app.route('/convert', methods=['POST'])
def convert():
    global contours, krl_script
    krl_script = kuka.converter.generate_krl_script(contours, save=False)
    krl_script = "\n".join(krl_script)
    return redirect(url_for('index'))

@app.route('/update_krl', methods=['POST'])
def update_krl():
    global krl_script
    krl_script = request.form['krl_script']
    return '', 204

@app.route('/download_krl')
def download_krl():
    from io import BytesIO
    import flask

    output = BytesIO()
    output.write(krl_script.encode('utf-8'))
    output.seek(0)

    return flask.send_file(output, as_attachment=True, download_name="draw.src", mimetype="text/plain")

if __name__ == '__main__':
    app.run(debug=True)