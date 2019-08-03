"""This script is to fetch the live videos and filter thems.
Then john them and push a live again"""
# -*-：coding: utf-8 -*-
import cv2
import json
import time
import base64
import inspect
import ctypes
import subprocess
import threading
import multiprocessing
import numpy as np

from utils.utils import *
from Stream import Stream
from easydict import EasyDict as edict
from flask import Flask, request, send_from_directory
from flask import json, jsonify, make_response

OUTPATH = 'None'
URL = 'http://tv6.ustc.edu.cn/hls/jlu_cctv13.m3u8'
LOCAL_PATH = './video/CCTV_News.mp4'
vdfilteror = None


def watch_dog():
    global vdfilteror
    while True:
        if isinstance(vdfilteror, Vdfilter):
            if not vdfilteror.newfilter.global_finish:
                time.sleep(5)
            else:
                time.sleep(10)
                vdfilteror = None


def chencode(to_content):
    return str(base64.b64encode(to_content.encode('utf-8')), 'utf-8')


class Vdfilter:
    def __init__(self, config):
        self.vd_mode = config['video_mode']  # local/live
        self.vd_ad = config['video_address']  # url for live mode or path of video for local mode
        self.key_wds = config['key_words']
        self.key_fcs = {}
        for key in config['key_faces']:
            self.key_fcs[key] = np.array(eval(config['key_faces'][key]), dtype=np.uint8)
        self.out_path = 'None'
        self.message = []
        if self.vd_mode == 'local' and not os.path.exists(os.path.join(os.getcwd(), self.vd_ad)):
            print("%s is invalid !" % os.path.join(os.getcwd(), self.vd_ad))
            self.message.append(chencode('无效的视频路径！！！'))
        self.channel = (self.vd_ad.split('/')[-1])[:-5] if self.vd_mode == 'live' else \
            (os.path.split(self.vd_ad)[-1]).split(".")[0]
        self.pushadress = os.path.join("http://114.213.210.211:8000/", self.vd_mode, self.channel + '.flv')
        self.newfilter = Stream(self.channel, self.out_path, self.vd_ad, self.key_wds, self.vd_mode, self.key_fcs)
        self.init()
        self.chipsthumbnail_set = set()  # 用于记录已经传送完成的缩略图文件名
        self.chips_set = set()  # 用于记录已经传送完成的片段文件名

    def init(self):
        if self.newfilter.vdmode == 'local':
            self.vdsource = threading.Thread(target=self.newfilter.cut_start)
            self.sub = threading.Thread(target=self.newfilter.filter_start)
            self.publish = threading.Thread(target=self.newfilter.push)
        else:
            self.vdsource = threading.Thread(target=self.newfilter.fetch)
            self.sub = threading.Thread(target=self.newfilter.filter_start)
            self.publish = threading.Thread(target=self.newfilter.push_live)

    def start(self):
        self.vdsource.setDaemon(True)
        self.vdsource.start()
        self.sub.setDaemon(True)
        self.sub.start()
        self.publish.setDaemon(True)
        self.publish.start()

    @staticmethod
    def _async_raise(tid, exctype):
        """raises the exception, performs cleanup if needed"""
        tid = ctypes.c_long(tid)
        if not inspect.isclass(exctype):
            exctype = type(exctype)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("invalid thread id")
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    def stop(self):
        self.newfilter.global_ternimal_single[0] = True
        while not (self.newfilter.global_ternimal_carry[0] and self.newfilter.global_ternimal_carry[1]
                   and self.newfilter.global_ternimal_carry[2]):
            time.sleep(0.01)
        if self.publish.is_alive():
            self._async_raise(self.publish.ident, SystemExit)
            self.publish.join()
        if self.sub.is_alive():
            self._async_raise(self.sub.ident, SystemExit)
            self.sub.join()
        if self.vdsource.is_alive():
            self._async_raise(self.vdsource.ident, SystemExit)
            self.vdsource.join()
        self.newfilter.clear_dir()
        return not self.vdsource.is_alive() or self.sub.is_alive() or self.publish.is_alive()

    def is_alive(self):
        return True if self.vdsource.is_alive() and self.sub.is_alive() and self.publish.is_alive() else False

    def get_fildthumbpic(self, fileddir):
        video_list = edict()
        dynamicplaylist = sorted(os.listdir(fileddir))
        for filename in dynamicplaylist:
            if filename in self.chipsthumbnail_set:
                continue
            else:
                self.chipsthumbnail_set.add(filename)
                filepath = os.path.join(self.newfilter.chips_dir, filename)
                cap = cv2.VideoCapture(filepath)
                rval, pic_data = cap.read()
                num = 30  # Read frame 30
                while rval and num > 0:
                    _, pic_data = cap.read()
                    num -= 1
                _pic_data = cv2.resize(pic_data, (320, 240))
                cap.release()
                video_list[filepath] = str(pic_data.tolist())
        return video_list

    def get_chipsdata(self):
        chipspath = os.path.join(self.newfilter.get_outdir(), self.newfilter.chips_dir)
        if not len(self.newfilter.history):
            return None
        else:
            for key in self.newfilter.history:
                chips_info = self.newfilter.history[key]
                self.newfilter.history.pop(key)
                respose = make_response(send_from_directory(chipspath, key, as_attachment=True))
                respose.headers["Chip-name"] = chips_info[0]
                respose.headers["Chip-source"] = chips_info[1]
                respose.headers["Chip-way"] = chips_info[2]
                respose.headers["Chip-length"] = chips_info[3]
                respose.headers["Chip-keyfeature"] = str(base64.b64encode(chips_info[4].encode('utf-8')), 'utf-8')
                respose.headers["Live-address"] = str(vdfilteror.pushadress)
                return respose


app = Flask(__name__)


@app.route('/vdpreview', methods=['POST'])
def vdpreview():
    res = json.loads(request.data)
    video_path = res['video_path']
    video_list = edict()
    picdir = os.path.join(os.getcwd(), video_path, 'thumbpic')
    if not os.path.exists(picdir):
        os.mkdir(picdir)

    dirfilepaths = os.listdir(os.path.join(os.getcwd(), video_path))
    """The following code is used to send thumbnails"""
    # dirfilepaths = []
    # dirfilepaths = get_filelist(os.path.join(os.getcwd(), video_path), dirfilepaths, ignoredir_='thumbpic')
    # for filepath in dirfilepaths:
    #     hfilename = (os.path.split(filepath)[-1]).split(".")[0]
    #     picfilename = os.path.join(picdir, hfilename + str('.jpg'))
    #     if os.path.exists(picfilename):
    #         pic_data = cv2.imread(picfilename)
    #     else:
    #         filepath = os.path.join(video_path, filepath)
    #         cap = cv2.VideoCapture(filepath)
    #         rval, pic_data = cap.read()
    #         num = 30  # Read frame 30
    #         while rval and num > 0:
    #             _, pic_data = cap.read()
    #             num -= 1
    #         pic_data = cv2.resize(pic_data, (320, 240))
    #         cv2.imwrite(picfilename, pic_data)
    #         cap.release()
    #     video_list[filepath] = str(pic_data.tolist())
    for filepath in dirfilepaths:
        filepath = os.path.join(video_path, filepath)
        video_list[filepath] = str(filepath)
    return jsonify({'video_path': video_path, 'video_list': video_list})


@app.route('/vdfilter', methods=['POST'])
def vdfilter():
    global vdfilteror
    res = json.loads(request.data)
    if res['stop']:
        if not isinstance(vdfilteror, Vdfilter):
            return jsonify({'status': 'Failed',
                            'message': chencode('进程尚未创建，无需停止！！！')})
        else:
            if vdfilteror.stop():
                vdfilteror = None
                return jsonify({'status': 'Stop', 'message': chencode('停止成功！')})
            else:
                vdfilteror = None
                return jsonify({'status': 'Stop',
                                'message': chencode('出现异常，已强行停止，可能存在残留进程！')})
    elif res['init']:
        if not isinstance(vdfilteror, Vdfilter):
            vdfilteror = Vdfilter(res)
            vdfilteror.start()
            if vdfilteror.is_alive():
                return jsonify({'status': 'Initing',
                                'message': chencode('启动成功,正在初始化 ... ')})
            else:
                message = vdfilteror.message
                vdfilteror.stop()
                vdfilteror = None
                return jsonify({'status': 'Stop',
                                'message': chencode('启动失败，请重试或检查后台进程！' + message[0])})
        else:
            return jsonify({'status': 'Initing',
                            'message': chencode('进程已创建，请勿重复创建，正在运行！若要切换视频，请首先停止当前进程！')})
    else:
        if not isinstance(vdfilteror, Vdfilter):
            return jsonify({'status': 'Failed',
                            'message': chencode('进程尚未创建，在刷新前请先创建进程！')})
        else:
            if vdfilteror.is_alive():
                if vdfilteror.newfilter.streamcreater_start:
                    resposedata = vdfilteror.get_chipsdata()
                    if resposedata is not None:
                        return resposedata
                    else:
                        return jsonify({'status': 'Pushing',
                                        'message': chencode('已开始推流，当前无最新的片段！！'),
                                        'Live address': str(vdfilteror.pushadress)})
                else:
                    return jsonify({'status': 'Loading',
                                    'message': chencode('视频正在加载！！！')})
            else:
                return jsonify({'status': 'Termination',
                                'message': chencode('运行出错，后台已停止运行！！！')})


def node_start():
    os.chdir('./Node-Media-Server')
    command = ["/home/lisishang/.nvm/versions/node/v8.16.0/bin/node", "app.js"]
    use_shell = True if os.name == "nt" else False
    subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)


if __name__ == "__main__":
    port = 9999
    vdsource = multiprocessing.Process(target=node_start)
    vdsource.start()
    wcdog = threading.Thread(target=watch_dog)
    wcdog.start()
    app.run(host="0.0.0.0", port=port, debug=True)
    print("Flask have started! Listening on 0.0.0.0:%d !" % port)


