import numpy as np
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
    
    for i, out in enumerate(outputs):
        print(f"[Output {i}] shape: {out[0].shape}, dtype: {out[0].dtype}, size: {out[0].size}")
    
    return [out[0] for out in outputs]

def dummy_input(shape=(1, 3, 640, 640)):
    # Generate a black image for testing
    return np.zeros(shape, dtype=np.float32)

if __name__ == "__main__":
    engine_path = "best_nan_sego.engine"  # Change if needed
    engine = load_engine(engine_path)
    context = engine.create_execution_context()
    inputs, outputs, bindings, stream = allocate_buffers(engine)

    # Dummy image (black input)
    input_tensor = dummy_input()

    # Fill input buffer
    np.copyto(inputs[0][0], input_tensor.ravel())

    # Run inference and print output shapes
    trt_outputs = do_inference(context, bindings, inputs, outputs, stream)

#3
