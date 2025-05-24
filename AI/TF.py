import cv2
import numpy as np
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

TRT_LOGGER = trt.Logger()

# Load TensorRT engine
def load_engine(path):
    with open(path, 'rb') as f, trt.Runtime(TRT_LOGGER) as runtime:
        return runtime.deserialize_cuda_engine(f.read())

engine = load_engine("yolov5n.trt")
context = engine.create_execution_context()

# Get binding info
input_idx = engine.get_binding_index("images")  # Change if needed
output_idx = engine.get_binding_index("output")  # Change if needed

input_shape = engine.get_binding_shape(input_idx)
output_shape = engine.get_binding_shape(output_idx)

w, h = input_shape[2], input_shape[1]
input_size = (w, h)

# Allocate memory
d_input = cuda.mem_alloc(trt.volume(input_shape) * 4)
d_output = cuda.mem_alloc(trt.volume(output_shape) * 4)
bindings = [int(d_input), int(d_output)]

# Video capture
cap = cv2.VideoCapture(0)

def preprocess(img):
    img = cv2.resize(img, input_size)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = np.transpose(img, (2, 0, 1)).astype(np.float32) / 255.0
    return np.expand_dims(img, axis=0)

def postprocess(output, conf=0.4):
    output = output.reshape(-1, 6)
    result = []
    for det in output:
        x1, y1, x2, y2, conf_score, cls = det
        if conf_score >= conf:
            result.append((int(x1), int(y1), int(x2), int(y2), float(conf_score), int(cls)))
    return result

while True:
    ret, frame = cap.read()
    if not ret:
        break

    inp = preprocess(frame)
    cuda.memcpy_htod(d_input, inp)
    context.execute_v2(bindings)
    out = np.empty(output_shape, dtype=np.float32)
    cuda.memcpy_dtoh(out, d_output)

    for (x1, y1, x2, y2, conf, cls) in postprocess(out):
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{cls} {conf:.2f}", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("YOLOv5 TensorRT Camera", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
