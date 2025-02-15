import os
import cv2
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
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
preprocessing_options = {
    'blur_intensity': 9,
    'threshold_block_size': 7,
    'threshold_C': 4
}

history = []
redo_stack = []

@app.route('/')
def index():
    global krl_script, contours, preprocessing_options
    return render_template('index.html', krl_script=krl_script, preprocessing_options=preprocessing_options)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and file.filename.endswith('.png'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        process_image(file_path)
        return redirect(url_for('index'))
    return 'Invalid file format. Please upload a PNG file.'

@app.route('/update_preprocessing', methods=['POST'])
def update_preprocessing():
    global preprocessing_options
    preprocessing_options['blur_intensity'] = int(request.form.get('blur_intensity'))
    preprocessing_options['threshold_block_size'] = int(request.form.get('threshold_block_size'))
    preprocessing_options['threshold_C'] = int(request.form.get('threshold_C'))
    print(preprocessing_options, "Hello2")
    return redirect(url_for('index'))

def smooth_contour(contour, window_size=5):
    if len(contour) < window_size:
        return contour

    kernel = np.ones(window_size) / window_size
    pad = window_size // 2

    padded_x = np.pad(contour[:, 0], pad_width=pad, mode='edge')
    padded_y = np.pad(contour[:, 1], pad_width=pad, mode='edge')

    smoothed_x = np.convolve(padded_x, kernel, mode='valid')
    smoothed_y = np.convolve(padded_y, kernel, mode='valid')

    return np.stack((smoothed_x, smoothed_y), axis=-1)

def process_image(image_path):
    global contours, preprocessing_options, history, redo_stack
    image = Image.open(image_path).convert("RGBA")
    image = ImageOps.expand(image, border=20)
    image = image.rotate(180)

    white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
    pil_image = Image.alpha_composite(white_bg, image)

    image_np = np.array(pil_image)
    image_grayscale = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    image_blur = cv2.medianBlur(image_grayscale, preprocessing_options['blur_intensity'])
    image_edges = cv2.adaptiveThreshold(
        image_blur,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=preprocessing_options['threshold_block_size'],
        C=preprocessing_options['threshold_C']
    )

    raw_contours = measure.find_contours(image_edges.astype(float), level=0.9)
    point_arrays = []
    for contour in raw_contours:
        points = np.fliplr(contour)
        if len(points) < 20:
            continue
        if np.sum((points[1:, 0] - points[:-1, 0]) * (points[1:, 1] + points[:-1, 1])) >= 0:
            continue
        points_smoothed = smooth_contour(points)
        point_arrays.append(points_smoothed)

    contours = point_arrays
    history.append((contours.copy(), preprocessing_options.copy()))
    print(history, "Hello")
    redo_stack.clear()

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
    global contours, history, redo_stack
    idx = int(request.form.get('contour_index')) - 1
    if 0 <= idx < len(contours):
        contours.pop(idx)
        history.append((contours.copy(), preprocessing_options.copy()))
        redo_stack.clear()
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

@app.route('/undo', methods=['POST'])
def undo():
    global contours, history, redo_stack, krl_script, preprocessing_options
    if history:
        redo_stack.append((contours.copy(), preprocessing_options.copy()))
        contours, preprocessing_options = history.pop()
        print(contours, "lol")
        #krl_script = kuka.converter.generate_krl_script(contours, save=False)
        #krl_script = "\n".join(krl_script)
    return redirect(url_for('index'))

@app.route('/redo', methods=['POST'])
def redo():
    global contours, history, redo_stack, preprocessing_options
    if redo_stack:
        history.append((contours.copy(), preprocessing_options.copy()))
        contours, preprocessing_options = redo_stack.pop()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)