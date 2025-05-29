Repo for converting yolo pt model to TRT model competable with jetson nano - > https://github.com/mailrocketsystems/JetsonYolov5
-------------------------------------
pyrealsense2 for depth camera (jetson nano) installation :
git clone https://github.com/JetsonHacksNano/installLibrealsense
cd installLibrealsense
sudo apt-get update && sudo apt-get install -y \
    git libssl-dev libusb-1.0-0-dev pkg-config libgtk-3-dev \
    libglfw3-dev libgl1-mesa-dev libglu1-mesa-dev \
    python3 python3-dev python3-pip
./buildLibrealsense.sh -j4
sudo find /usr/local -name "pyrealsense2*.so"
nano ~/.bashrc
export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python3.6/pyrealsense2
source ~/.bashrc
---------------------------------------

Train Yolo5 model using Google Colab:
Runtime > Change runtime type > Hardware accelerator: GPU

!git clone https://github.com/ultralytics/yolov5

%cd yolov5

%pip install -r requirements.txt


Roboflow part to import the dataset:
!pip install roboflow
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("YOUR_WORKSPACE").project("YOUR_PROJECT")
dataset = project.version(1).download("yolov5")

!python train.py --img 640 --batch 16 --epochs 100 --data YOUR_PROJECT/data.yaml --weights yolov5s.pt --name mario_model

from google.colab import files
files.download('runs/train/mario_model/weights/best.pt')

**note that, on the training command change Your project with your project’s name created by Roboflow ex. /content/yolov5/MarioOD.v1i.yolov5pytorch/
from models.yolo import Model
====================
from google.colab import files
files.download('runs/train/FFRoboArm/weights/best.pt')
===================================
import torch

ckpt = torch.load("runs/train/FFRoboArm/weights/best.pt", map_location="cpu")

model = Model("models/yolov5s.yaml", ch=3, nc=4)  
model.load_state_dict(ckpt['model'].float().state_dict())  

torch.save({'model': model}, "best_windows.pt")  # 
