import pyrealsense2 as rs

ctx = rs.context()
devices = ctx.query_devices()
if len(devices) == 0:
    print("❌ No RealSense devices found")
else:
    print("✅ RealSense connected:", devices[0].get_info(rs.camera_info.name))
