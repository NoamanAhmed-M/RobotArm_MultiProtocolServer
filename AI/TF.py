import cv2
import numpy as np
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
import time

# Load the TensorRT engine
TRT_LOGGER = trt.Logger(trt.Logger.INFO)

def load_engine(engine_path):
    with open(engine_path, 'rb') as f, trt.Runtime(TRT_LOGGER) as runtime:
        return runtime.deserialize_cuda_engine(f.read())

engine = load_engine("yolov5n.trt")  # Replace with your .engine file
context = engine.create_execution_context()

# Get input and output details
input_index = engine.get_binding_index('images')  # usually 'images' for YOLOv5
output_index = engine.get_binding_index('output')  # usually 'output'

input_shape = engine.get_binding_shape(input_index)
output_shape = engine.get_binding_shape(output_index)

input_size = (input_shape[2], input_shape[1])  # width, height

# Allocate device memory
d_input = cuda.mem_alloc(trt.volume(input_shape) * np.float32().nbytes)
d_output = cuda.mem_alloc(trt.volume(output_shape) * np.float32().nbytes)
bindings = [int(d_input), int(d_output)]

# Helper to preprocess frames
def preprocess(img):
    img_resized = cv2.resize(img, input_size)
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_transposed = np.transpose(img_rgb, (2, 0, 1)).astype(np.float32) / 255.0
    return np.expand_dims(img_transposed, axis=0)

# Postprocessing helper
def postprocess(output, conf_thres=0.4):
    output = output.reshape(-1, 6)
    boxes = []
    for det in output:
        conf = det[4]
        if conf > conf_thres:
            x1, y1, x2, y2 = map(int, det[:4])
            cls = int(det[5])
            boxes.append((x1, y1, x2, y2, conf, cls))
    return boxes

# Open camera
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    img = preprocess(frame)
    img = np.ascontiguousarray(img)

    # Transfer to device
    cuda.memcpy_htod(d_input, img)
    context.execute_v2(bindings)

    # Retrieve results
    output = np.empty(output_shape, dtype=np.float32)
    cuda.memcpy_dtoh(output, d_output)

    # Draw results
    for (x1, y1, x2, y2, conf, cls) in postprocess(output):
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{int(cls)}: {conf:.2f}"
        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("YOLOv5 TensorRT", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
