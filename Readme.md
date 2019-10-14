## 视频关键字、关键帧过滤系统

## 综述

本系统可以根据用户提供的关键字和人脸图像，实时过滤选定文件中的内容，并提取出包含关键字和人脸图像的视频片段。

## 后台

### 环境配置

1. 本系统基于python，人脸检测使用dlib库，需要使用GPU加速，需要预先[配置CUDA环境](#配置CUDA环境)

2. 建立 python3.5+ 虚拟环境 ```conda create -n videosearch python=3.7```

3. 安装依赖 ```pip install -r requirements.txt```

4. [安装 GPU-dlib](#安装GPU-dlib)

### 文件结构

.
├── AutoFilter.py                关键字过滤脚本  
├── CutVideo.py                视频切割脚本  
├── FaceRecognition.py    关键帧检测脚本  
├── FetchStream.py          直播流抓取脚本  
├── __init__.py  
├── main.py                       主函数  
├── Node-Media-Server    推流服务  
├── Stream.py                   推流脚本  
├── utils                             辅助函数  
└── video                           视频库   

### 附录

##### 配置CUDA环境

- 下载适合机器的CUDA10.0和Cudnn包（deb包）
- sudo dpkg -i xxx.deb

##### 安装GPU-dlib

1. 配置好Cuda10.0、Cudnn 环境，并将路径添加到~/.bashrc中，如下：

```shell
export CUDA_HOME="/path/to/cuda/cuda-10.0"
export PATH="$PATH:$CUDA_HOME/bin"
export LD_LIBRART_PATH="$CUDA_HOME/lib64"
```

2. 下载dlib源码

```shell
git clone https://github.com/davisking/dlib.git
```

3. 在建好的python环境中执行


```shell
python setup.py install --set DLIB_USE_CUDA=1 --set USE_AVX_INSTRUCTIONS=1
```