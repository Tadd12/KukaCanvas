# KUKACanvas

KUKACanvas is a Python-based tool that converts images into movement instructions for KUKA robots, enabling automated drawing or sketching. It provides an interface for image processing, contour detection, and the generation of robot code compatible with KUKA six-axis robots.

## Features

- Converts images to robot movement commands (e.g., KRL `.src` files)
- Image preprocessing: grayscale conversion, blurring, adaptive thresholding
- Plotting of contours and robot pathing
- Contour removing by clicking on the contour plot
- Contour detection and smoothing
- Contour interpolation and closure for continuous drawing paths
- Self-hosted web interface for image upload and conversion to KRL code

## Requirements

Install dependencies:
```
pip install opencv-python numpy pillow scikit-image flask flask_session plotly pandas
```

## Usage

### With web interface
1. Run the Flask web server:
   ```bash
   python app.py
   ```
2. Open your web browser and navigate to `https://{set-url}/kuka`
3. Use KUKACanvas

### Without web interface
Look at `main.py` for the main function. You can set `ìmage_path` and `output_path` to your desired input image and output file name. Also image processing parameters can be set in `main.py`:

```bash
   python main.py
```

## KRL Code Generation
Every contour is represented as a series of points. The code generation function takes these points and formats them into KUKA Robot Language (KRL) commands. The generated code includes:
- Initialization of the robot's base and tool
- Setting the robot's position to a home position
- Movement commands for each contour, including linear and circular movements
- Wait commands to control the speed of the drawing process
- Closing the contours to ensure continuous drawing
- Returning to the home position after completing the drawing
- Comments to indicate the start and end of each contour


A generated KUKA `.src` file will contain lines like with `{base_id}` and `{tool_id}` replaced with actual values:
```
&ACCESS RVP 
&REL 1 

DEF DRAW() 

POS p_home 
p_home = {X 0.00, Y 0.00, Z 10.00, A 0, B 0, C 0} 

BAS(#initmov, 0) 
BAS(#tool, {tool_id}) 
BAS(#base, {base_id}) 

PTP $axis_act 

PTP p_home

; ----- Contour 1 -----
PTP {X 112.68, Y 204.61, Z 10.00, A 0, B 0, C 0}
LIN {X 112.68, Y 204.61, Z 0.00, A 0, B 0, C 0}
WAIT SEC 0.1

LIN {X 114.64, Y 204.61, Z 0.00, A 0, B 0, C 0} C_DIS
LIN {X 116.60, Y 204.61, Z 0.00, A 0, B 0, C 0} C_DIS
.
.
.
LIN {X 112.37, Y 204.77, Z 10.00, A 0, B 0, C 0}
; ----- Contour 2 -----
.
.
.
PTP p_home
END
```

## Web Interface
![Web Interface Screenshot](webapp.png)
