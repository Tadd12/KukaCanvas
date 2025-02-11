import os

import cv2
import numpy as np
from PIL import Image, ImageOps


image = Image.open("shibu.png")
os.chdir("shibu")

image = ImageOps.expand(image, border=20)

# Composite onto a white background (so transparent regions become white)
white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
pil_image = Image.alpha_composite(white_bg, image)

img = np.array(pil_image)

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

edges = cv2.Canny(gray, 50, 150)
#_, edges = cv2.threshold(edges, 128, 255, cv2.THRESH_BINARY_INV)


#kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
#edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)


contours = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
contours = contours[0] if len(contours) == 2 else contours[1]

# filter contours to keep only large ones
result = img.copy()
i = 1
for c in contours:
    perimeter = cv2.arcLength(c, True)
    if perimeter > 100:
        cv2.drawContours(result, c, -1, (0,0,255), 1)
        contour_img = np.zeros_like(img, dtype=np.uint8)
        cv2.drawContours(contour_img, c, -1, (0,0,255), 1)
        cv2.imwrite("short_title_contour_{0}.jpg".format(i),contour_img)
        i = i + 1

def show(nums):
    con_img = np.zeros_like(img, dtype=np.uint8)
    for num in nums:
        cv2.drawContours(con_img, contours[num], -1, (0,0,255), 1)
    cv2.imwrite("con_img.jpg", con_img)

# save results
cv2.imwrite("short_title_gray.jpg", gray)
cv2.imwrite("short_title_edges.jpg", edges)
cv2.imwrite("short_title_contours.jpg", result)