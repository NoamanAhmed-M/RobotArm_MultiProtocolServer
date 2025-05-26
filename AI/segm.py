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

def visualize_segmentation(original, proto_output, mask_coeff, threshold=0.5):
    # proto_output: (32, 160, 160)
    # mask_coeff: (32,)
    mask = np.tensordot(mask_coeff, proto_output, axes=([0], [0]))  # (160, 160)
    mask = 1 / (1 + np.exp(-mask))  # Sigmoid
    mask = cv2.resize(mask, (original.shape[1], original.shape[0]))
    mask_bin = (mask > threshold).astype(np.uint8) * 255

    color_mask = np.zeros_like(original)
    color_mask[:, :, 1] = mask_bin  # Green channel
    return cv2.addWeighted(original, 0.7, color_mask, 0.3, 0)

if __name__ == "__main__":
    engine = load_engine("best_nan_sego.engine")
    context = engine.create_execution_context()
    inputs, outputs, bindings, stream = allocate_buffers(engine)

    # Setup RealSense camera stream
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

            output = do_inference(context, bindings, inputs, outputs, stream)[0]
            print("Output shape:", output.shape, "size:", output.size)

            # ✅ Fix: reshape to (32, 160, 160)
            proto = output.reshape((32, 160, 160))

            # TEMP: random mask coeffs (replace later with real detection)
            mask_coeff = np.random.rand(32).astype(np.float32)

            result = visualize_segmentation(img, proto, mask_coeff)

            cv2.imshow("YOLOv5 Segmentation", result)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()
