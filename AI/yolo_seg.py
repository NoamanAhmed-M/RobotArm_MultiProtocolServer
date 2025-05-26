import pyrealsense2 as rs
import numpy as np
import cv2
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

TRT_LOGGER = trt.Logger(trt.Logger.INFO)

def load_engine(path):
    with open(path, "rb") as f, trt.Runtime(TRT_LOGGER) as runtime:
        return runtime.deserialize_cuda_engine(f.read())

def allocate_buffers(engine):
    inputs, outputs, bindings = [], [], []
    stream = cuda.Stream()
    for binding in engine:
        shape = engine.get_binding_shape(binding)
        size = trt.volume(shape)
        dtype = trt.nptype(engine.get_binding_dtype(binding))
        host_mem = cuda.pagelocked_empty(size, dtype)
        device_mem = cuda.mem_alloc(host_mem.nbytes)
        bindings.append(int(device_mem))
        if engine.binding_is_input(binding):
            inputs.append((host_mem, device_mem))
        else:
            outputs.append((host_mem, device_mem))
    return inputs, outputs, bindings, stream

def do_inference(context, bindings, inputs, outputs, stream):
    [cuda.memcpy_htod_async(inp[1], inp[0], stream) for inp in inputs]
    context.execute_async_v2(bindings=bindings, stream_handle=stream.handle)
    [cuda.memcpy_dtoh_async(out[0], out[1], stream) for out in outputs]
    stream.synchronize()
    return [out[0] for out in outputs]

def preprocess(frame, size=(640, 640)):
    img_resized = cv2.resize(frame, size)
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img = img_rgb.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))
    img = np.expand_dims(img, axis=0)
    return frame, np.ascontiguousarray(img)

def postprocess(detections, img_shape, conf_thresh=0.4):
    boxes, scores, classes, masks = [], [], [], []
    for det in detections:
        if det[4] < conf_thresh:
            continue
        x1, y1, x2, y2 = det[0:4]
        x1 = int(x1 / 640 * img_shape[1])
        y1 = int(y1 / 640 * img_shape[0])
        x2 = int(x2 / 640 * img_shape[1])
        y2 = int(y2 / 640 * img_shape[0])
        score = det[4]
        cls = int(det[5])
        mask_coef = det[6:38]  # 32 coefficients
        boxes.append([x1, y1, x2, y2])
        scores.append(score)
        classes.append(cls)
        masks.append(mask_coef)
    return boxes, scores, classes, masks

def apply_mask(proto, mask_coef, box, img_shape, threshold=0.5):
    mask = np.tensordot(mask_coef, proto, axes=([0], [0]))  # (160,160)
    mask = 1 / (1 + np.exp(-mask))  # sigmoid
    mask = cv2.resize(mask, (img_shape[1], img_shape[0]))
    x1, y1, x2, y2 = box
    mask_cropped = (mask > threshold).astype(np.uint8) * 255
    return mask_cropped

def visualize(image, masks, boxes, classes, scores):
    overlay = image.copy()
    for i, mask in enumerate(masks):
        color_mask = np.zeros_like(image)
        color_mask[:, :, 1] = mask
        overlay = cv2.addWeighted(overlay, 1.0, color_mask, 0.5, 0)
        x1, y1, x2, y2 = boxes[i]
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"Obj {classes[i]}: {scores[i]:.2f}"
        cv2.putText(overlay, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return overlay

if __name__ == "__main__":
    engine = load_engine("best_nan_sego.engine")
    context = engine.create_execution_context()
    inputs, outputs, bindings, stream = allocate_buffers(engine)

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline.start(config)

    try:
        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            color_image = np.asanyarray(color_frame.get_data())
            img, input_tensor = preprocess(color_image)
            np.copyto(inputs[0][0], input_tensor.ravel())

            trt_outputs = do_inference(context, bindings, inputs, outputs, stream)
            proto = trt_outputs[0].reshape((32, 160, 160))
            detections = trt_outputs[1].reshape((25200, 39))

            boxes, scores, classes, masks = postprocess(detections, color_image.shape, conf_thresh=0.4)

            all_masks = []
            for box, coef in zip(boxes, masks):
                m = apply_mask(proto, coef, box, color_image.shape)
                all_masks.append(m)

            result = visualize(color_image, all_masks, boxes, classes, scores)

            cv2.imshow("YOLOv5-Segmentation TensorRT", result)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()

#4
trtexec --onnx=best_nan_sego.onnx --saveEngine=best_nan_sego.engine --fp32
python export.py --weights best_nan_sego.pt --img 640 --include onnx --opset 12 --dynamic
pip install onnxruntime
sudo find / -name trtexec 2>/dev/null
/usr/src/tensorrt/bin/trtexec
sudo apt update
sudo apt install tensorrt
sudo apt install tensorrt python3-libnvinfer-dev
/usr/src/tensorrt/bin/trtexec --version
echo 'export PATH=$PATH:/usr/src/tensorrt/bin' >> ~/.bashrc
source ~/.bashrc
trtexec --onnx=best_nan_sego.onnx --saveEngine="best_nan_sego.engine" --fp32
trtexec --onnx=best_nan_sego.onnx --saveEngine=best_nan_sego.engine --fp32
--saveEngine=/home/its/Desktop/best_nan_sego_fp32.engine
trtexec --onnx=/home/its/Desktop/yolov5/best_nan_sego.onnx --saveEngine=/home/its/Desktop/yolov5/best_nan_sego_fp32.engine --fp32 --verbose
---------
trtexec --onnx=/home/its/Desktop/nano_best.onnx --saveEngine=/home/its/Desktop/nano_best.engine --fp32


