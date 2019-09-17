# -*- coding:utf-8 -*-
import numpy as np
import time
import os
import dlib     # pip install dlib
import cv2      # pip install opencv-contrib-python
import utils.utils

detector = dlib.get_frontal_face_detector()     # 模型加载
currentpath = os.path.dirname(os.path.abspath(__file__))
face_rec_model = dlib.face_recognition_model_v1(currentpath + '/utils/models/dlib_face_recognition_resnet_model_v1.dat')
shape_predictor = dlib.shape_predictor(currentpath + '/utils/models/shape_predictor_68_face_landmarks.dat')
cascade = cv2.CascadeClassifier(currentpath + "/utils/models/haarcascade_frontalface_alt.xml")


def total_time(func):
    """
    Calculate the running time of the function
    :param func: the function need to been calculated
    :return:
    """
    def call_fun(*args, **kwargs):
        start_time = time.time()
        f = func(*args, **kwargs)
        end_time = time.time()
        print('%s() run time：%s s' % (func.__name__, int(end_time - start_time)))
        return f
    return call_fun


def extract_face_feature(imagename):
    """
    输入一张图片路径，返回此图片中人脸特征
    :param imagename: 图片路径+名称
    :return: 若检测到图片中人脸，返回128维人脸特征，否则返回None
    """
    img_bgr = cv2.imread(imagename) if isinstance(imagename, str) else imagename
    b, g, r = cv2.split(img_bgr)
    img_rgb = cv2.merge([r, g, b])
    face = detector(img_rgb, 1)
    if len(face):
        for index, face in enumerate(face):
            shape = shape_predictor(img_rgb, face)
            face_feature = face_rec_model.compute_face_descriptor(img_rgb, shape)
            return face_feature
    else:
        return None


def get_face_features(frame, faceposition):
    """
    获取视频中某一帧人脸128维特征向量作为输出
    :param frame: 一帧图片的RGB值
    :param detector: 人脸位置，矩形对角坐标表示
    :return: 人脸的128维特征向量
    """
    shape = shape_predictor(frame, faceposition)
    face_feature = face_rec_model.compute_face_descriptor(frame, shape)
    return face_feature


def frame_time(time_ms):
    """
    输入所播放帧的ms时间，返回hh:mm:ss,ms格式的时间
    :param time_ms: 当前帧ms数
    :return: 指定格式的时间
    """
    """注释掉算法，直接返回秒，后端适配---修改于2019.6.1"""
    return time_ms/1000


class FaceChipInfo:
    """人脸片段信息类，包括片段信息和片段信息处理方法，待检测人脸每人一个"""
    def __init__(self, name):
        self.name = name
        self.reinit()

    def reinit(self):
        self.start_time = ''
        self.end_time = ''
        self.show_flag = False
        self.time_show = []

    def process_info(self):
        """  储存上一次人物头像出现的开始结束时间，并且做一下次存储的准备  """
        time_interval = (self.start_time, self.end_time)
        self.time_show.append(time_interval)
        self.start_time = 0
        self.end_time = 0
        self.show_flag = False

    def clear_invalid_data(self):
        """
        删除检测到的无效信息，通过记录时间来判断,主要清除start_time=end_time的时间戳
        """
        for time_intervel in self.time_show[::-1]:
            if time_intervel[0] == time_intervel[1]:
                self.time_show.remove(time_intervel)
            # if time_intervel[0] > time_intervel[1]:
            #     self.time_show.append((time_intervel[1], time_intervel[0]))
        return self.time_show


class Facedetection(object):
    """人脸检测器，人脸检测器的函数和初始化函数等"""
    def __init__(self, faceimages, exit_signal, img_enlarge_times=0):
        self.current_time = 0
        self.frame_interval = 10
        self.img_enlarge_times = img_enlarge_times
        self.feature = None
        self.keyname = []
        self.keyface_feature_create(faceimages)
        self.person_info = {}
        self.person_info_create()
        self.exit_signal = exit_signal

    def person_info_create(self):
        for person in self.keyname:
            self.person_info[person] = FaceChipInfo(person)

    def person_info_init(self):
        for item in self.person_info:
            self.person_info[item].reinit()

    def keyface_feature_create(self, faceimages):
        self.feature = np.zeros(shape=(128, len(faceimages)))
        for i, key in enumerate(faceimages.keys()):
            self.keyname.append(key)
            self.feature[:, i] = extract_face_feature(faceimages[key])

    def face_detected(self, frame):
        """
        检测一帧图片上的所出现的人脸, 并用矩形框框出,同时记录下此人脸出现的时间
        :param frame:视频中的一帧
        :return:
        """
        """二次开发中实现多人脸检测，矩阵运算"""
        _faces = detector(frame, self.img_enlarge_times)  # 使用detector检测器来检测图像中的人脸 ,1 表示将图片放大一倍
        frameface_feature = np.zeros(shape=(128, len(_faces)))
        for i, face in enumerate(_faces):
            frameface_feature[:, i] = get_face_features(frame, face)
        if len(_faces):
            compare_result = np.zeros(shape=(len(self.keyname), len(_faces)))
            for i in range(len(self.keyname)):
                frameface_feature = np.array(frameface_feature).reshape(128, len(_faces))
                feature = np.array(self.feature[:, i]).reshape(128, 1)
                # 二范数
                compare_result[i] = np.array(np.linalg.norm(frameface_feature - feature, axis=0)).reshape(1, len(_faces))

            compare_result = np.min(compare_result, axis=1).reshape(len(self.keyname), 1)
            compare_result = np.array(compare_result < 0.4).reshape(len(self.keyname), 1)
            compare_result = [self.keyname[i] for i, item in enumerate(compare_result) if item]
            for person in compare_result:
                if not self.person_info[person].show_flag:            # 说明此人脸是第一次出现
                    self.person_info[person].start_time = self.current_time
                    self.person_info[person].end_time = self.current_time
                    self.person_info[person].show_flag = True         # 下次出现只更新end_time
                else:
                    self.person_info[person].end_time = self.current_time
        for person in self.keyname:
            if self.person_info[person].show_flag and self.person_info[person].end_time != self.current_time:
                self.person_info[person].process_info()

    @total_time
    def start(self, vidoepath):
        """ 将视频按固定间隔读取检测图片 """
        self.person_info_init()
        self.current_time = 0
        frame_index = 0
        cap = cv2.VideoCapture(vidoepath)
        count = 5
        while count and not cap.isOpened():
            cap = cv2.VideoCapture(vidoepath)
            count -= 1  # 读五次
            if not count and not cap.isOpened():
                print('Read error !')
                return
        success, frame = cap.read()  # success：是否读取到帧 frame：截取到一帧图像，三维矩阵表示
        while success:
            self.current_time = frame_time(int(cap.get(0)))  # 获取当前播放帧在视频中的时间
            if self.exit_signal[0]:  # 判断外部传入的信号，当有停止信号传入时，立即从任务中返回，不做任何处理
                return []
            if frame_index % self.frame_interval == 0:  # 隔几帧取一次，加快执行速度
                self.face_detected(frame)
            frame_index += 1
            success, frame = cap.read()
        cap.release()  # Release everything if job is finished

        for person in self.person_info:  # 人物信息处理工作，清理无效信息
            self.person_info[person].process_info()
            self.person_info[person].clear_invalid_data()
        return self.person_info


if __name__ == '__main__':
    faces = {}
    faces['习近平'] = cv2.imread('./utils/images/习近平.jpg')
    faces['李克强'] = cv2.imread('./utils/images/李克强.jpg')
    faces['李梓萌'] = cv2.imread('./utils/images/李梓萌.jpg')
    faces['康辉'] = cv2.imread('./utils/images/康辉.jpg')
    fd = Facedetection(faces)
    result = fd.start('./utils/video/cctv1hd-1564737645000.ts')
    for k in result:
        print(k)
        print(result[k].time_show)






