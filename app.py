import base64
from typing import Type
from urllib import response
from flask_cors import CORS, cross_origin
from flask import Flask, request, jsonify, send_file
import os
import time

from io import BytesIO

from tensorflow.keras.models import load_model
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing import image

from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import mahotas as mh
import tensorflow as tf
import cv2
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from skimage.feature import graycomatrix, graycoprops

dir = ""

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

model = load_model(dir + 'model/stroke_classification_model.h5')

@app.route('/')
@cross_origin()
def home():
    return "home"

@app.route('/prediction', methods=['POST'])
@cross_origin()
def prediction():

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    file_data = file.read()

    file_object = BytesIO(file_data)
    image = Image.open(file_object)

    img_width, img_height = 224, 224

    target_size = (img_width, img_height)
    img = image.resize(target_size)

    gray_image = image_to_grayscale(img)

    blur_image = image_to_blur(gray_image)

    threshold_image = image_to_threshold(blur_image)

    morphological_image = image_to_morphological(threshold_image)

    img = Image.fromarray(morphological_image)
    img.save(dir + 'temp/1.jpg')

    feature = calculate_glcm_features(dir + "temp/1.jpg")

    feature_standart_array = standarization(feature)

    res_predict = model.predict(feature_standart_array)

    res_max_index = np.argmax(res_predict)

    res_class = ""

    if (res_max_index == 0):
        res_class = "normal"
    elif (res_max_index == 1):
        res_class = "hemorrhagic"
    elif (res_max_index == 2):
        res_class = "ischemic"
    else:
        res_class = "undefined"

    return jsonify(res_class)

def load_image_from_base64(base64_string, target_size):
    encoded_data = base64_string.split(',')[1]
    image_bytes = base64.b64decode(encoded_data)

    img = image.load_img(BytesIO(image_bytes), target_size=target_size)

    return img

def image_to_grayscale(img):
    gray_image = img.convert("L")
    return gray_image

def image_to_blur(img, kernel_size=(5, 5), sigma=0):
    image = np.array(img)
    blurred_image = cv2.GaussianBlur(image, kernel_size, sigma)
    return blurred_image

def image_to_threshold(img, block_size=11):
    image = np.array(img)
    _, thresholded_image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresholded_image

def image_to_morphological(img, kernel_size=3):
    image = np.array(img)
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    opened_image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
    return opened_image

def calculate_glcm_features(image_path):
    image = Image.open(image_path)
    gray_image = image.convert("L")
    gray_array = np.array(gray_image)

    # Hitung GLCM
    distances = [1]  # Jarak antara piksel
    angles = [0]     # Sudut
    glcm = graycomatrix(gray_array, distances=distances, angles=angles, symmetric=True, normed=True)

    # Ekstraksi fitur dari GLCM
    contrast = graycoprops(glcm, 'contrast')[0, 0]
    dissimilarity = graycoprops(glcm, 'dissimilarity')[0, 0]
    homogeneity = graycoprops(glcm, 'homogeneity')[0, 0]
    correlation = graycoprops(glcm, 'correlation')[0, 0]
    angular = graycoprops(glcm, 'ASM')[0, 0]
    energy = graycoprops(glcm, 'energy')[0, 0]

    return [contrast, dissimilarity, homogeneity, correlation, angular, energy]

def standarization(feature):
    features = np.load(dir + "feature/1.1 features.npy")
    features = np.append(features, [feature], axis=0)

    df = pd.DataFrame(features)

    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df)
    scaled_df = pd.DataFrame(scaled_data, columns=df.columns)

    feature_standart = scaled_df.iloc[-1]
    feature_standart_flatten = feature_standart.values.flatten()

    feature_standart_array = np.array([feature_standart_flatten])

    return feature_standart_array

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')