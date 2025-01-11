# Import the necessary packages
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
from imutils.video import VideoStream
import numpy as np
import imutils
import time
import cv2
import os

def detect_and_predict_mask(frame, faceNet, maskNet):
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))


    faceNet.setInput(blob)
    detections = faceNet.forward()

    # Initialize our lists
    faces = []
    locs = []
    preds = []

   
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]

        # Filter weak detections
        if confidence > 0.5:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # Ensure bounding boxes fall within the frame
            (startX, startY) = (max(0, startX), max(0, startY))
            (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

            # Preprocess the face ROI
            face = frame[startY:endY, startX:endX]
            if face.size == 0:
                continue
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = cv2.resize(face, (224, 224))
            face = img_to_array(face)
            face = preprocess_input(face)

            # Append the face and bounding box
            faces.append(face)
            locs.append((startX, startY, endX, endY))

    # Predict mask or no mask if at least one face is detected
    if len(faces) > 0:
        faces = np.array(faces, dtype="float32")
        preds = maskNet.predict(faces, batch_size=32)

    return (locs, preds)


prototxtPath = r"face_detector\deploy.prototxt"
weightsPath = r"face_detector\res10_300x300_ssd_iter_140000.caffemodel"


if not os.path.exists(prototxtPath) or not os.path.exists(weightsPath):
    raise FileNotFoundError("Face detection model files not found. Check paths.")

faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)

# Load the trained face mask detection model
if not os.path.exists("Face_mask_detector.h5"):
    raise FileNotFoundError("Face mask detection model file not found.")
maskNet = load_model("Face_mask_detector.h5")

# Start the video stream
print("[INFO] Starting video stream")
vs = VideoStream(src=0).start()
time.sleep(2.0)

try:
    # Loop over frames from the video stream
    while True:
        frame = vs.read()
        if frame is None:
            print("[ERROR] Frame not captured. Retrying...")
            continue
        frame = imutils.resize(frame, width=400)

        # Detect faces and predict mask or no mask
        (locs, preds) = detect_and_predict_mask(frame, faceNet, maskNet)

        # Loop over the detected face locations and their corresponding predictions
        for (box, pred) in zip(locs, preds):
            (startX, startY, endX, endY) = box
            (mask, withoutMask) = pred

            # Determine label and bounding box color
            label = "Mask" if mask < withoutMask else "No Mask"
            color = (0, 255, 0) if label == "Mask" else (0, 0, 255)

            # Include the probability in the label
            label = f"{label}: {max(mask, withoutMask) * 100:.2f}%"

            # Display the label and bounding box rectangle
            cv2.putText(frame, label, (startX, startY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)

      
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF

        # Break from loop if `q` key is pressed
        if key == ord("q"):
            break
finally:
    # Cleanup
    print("[INFO] Cleaning up...")
    cv2.destroyAllWindows()
    vs.stop()
