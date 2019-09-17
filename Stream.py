#!/usr/bin/env python3
"""This is the script to join stream"""
import time
import subprocess
import threading

from utils.utils import *
from AutoFilter import AutoFilter
# import tempfile
# from ffmpy import FFmpeg
# import multiprocessing


class NopPusher:
    """这是一个空推流类，为了兼容本地推流做的，当视频源为直播时，使用这个空类"""
    def __init__(self):
        self.flag = True

    def poll(self):
        return self.flag

    def communicate(self, _in_put_):
        pass


class Stream(AutoFilter):
    def __init__(self, channel, outpath, videopath, keywords, vdmode, faceimages):
        super(Stream, self).__init__(channel, outpath, videopath, keywords, vdmode, faceimages)

    def ternimal_handling(self):
        while not (self.global_ternimal_carry[0] and self.global_ternimal_carry[1]):
            time.sleep(0.01)
        else:
            self.global_ternimal_carry[2] = True
            self.global_finish = True
        while True:
            print("---------Stream capture the ternimal signal and wait for be terminated ...----------")
            time.sleep(0.01)

    def push(self):
        print("Process push have start ...")
        while self.delay:
            time.sleep(1)
            self.delay -= 1
        # 开始准备推流
        self.streamcreater_start = True
        if self.vdmode == 'local':
            # 本地模式推流，直接推源视频，
            command = ["ffmpeg", "-loglevel", "error", "-re", "-strict", "-2", "-i", self.videopath, "-preset",
                       "superfast", "-tune", "zerolatency", "-c:v", "libx264", "-c:a", "aac", "-ar", "44100",
                       "-threads", "2", "-f", "flv", os.path.join("rtmp://114.213.210.211/", self.vdmode, self.channel)]
            use_shell = True if os.name == "nt" else False
            childpushlive = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, shell=use_shell)
        else:
            childpushlive = NopPusher()  # 直播的话就设置一个空推流对象，不需要推流，客户端直接播放直播地址

        while childpushlive.poll() != 0 and not self.global_ternimal_single[0]:  # 等待推流结束（以及推流异常）或者全局终止信号
            time.sleep(0.5)
        else:
            self.streamcreater_start = False
            if self.global_ternimal_single[0]:  # 判断动作，若为全局终止信号，则准备终结当前进程
                childpushlive.communicate('q'.encode())  # 停止推流
                self.ternimal_handling()  # 标记为安全进程，等待终结
            else:
                while not (self.cutvideo_finish and self.autofilter_finish):  # 播放结束，执行后台清理工作
                    time.sleep(0.1)
                else:
                    self.global_finish = True
                    while True:
                        # print("---------Play finished and wait for be terminated ...----------")
                        time.sleep(1)

        return True


if __name__ == "__main__":
    # stream = Stream('CCTV_News', 'None', './video/CCTV_News.mp4', '习近平', 'local', 'filsave')
    stream = Stream('cctv1hd', 'None', 'http://tv6.ustc.edu.cn/hls/cctv1hd.m3u8', '习近平', 'local', None)
    aa = threading.Thread(target=stream.filter_start)
    aa.start()
    # history-------早期，通过将合成片段规范化命名后，添加进txt文件来推流，但是切片跟不上就会断流，弃用-----------------3
    # ---------------------------------------文件列表推流的示范代码----------------------------------------------------
    # command = ["ffmpeg", "-loglevel", "error", "-f", "concat", "-re", "-i", "list.txt", "-max_muxing_queue_size",
    #            "1024", "-c:v", "libx264", "-preset", "superfast", "-tune", "zerolatency", "-c:a", "aac", "-ar",
    #            "44100", "-threads", "2", "-f", "flv",
    #            os.path.join("rtmp://114.213.210.211/", self.vdmode, self.channel)]
    # history----------------从推流进程中读取标准输出的进程，调了一会，发现有更好的方法，弃用---------------------------2
    # message = childpushlive.stdout.readlines()  # wait time
    # if message[5].decode().find('list.txt') != -1 and \
    #         message[5].decode().split(':')[1].find('No such file or directory') != -1:
    #     no_file_exit = True
    # if no_file_exit:
    #     while not self.global_ternimal_single[0]:
    #         print('----------------Exception exit waiting for be terminated---------')
    #         time.sleep(1)
    #     else:
    #         if self.global_ternimal_single[0]:
    #             self.global_ternimal_carry[2] = True
    #             while True:
    #                 print("---------Stream capture the ternimal signal and wait for be terminated ...----------")
    #                 time.sleep(0.01)
    # history----------------------------早期将片段合成推送的代码，已弃用----------------------------------------------1
    # def join(self):
    #     self.joindir = self.create_dir('-join')
    #     video_seqnum = 0
    #     print("Process john have start ...")
    #     time.sleep((self.Length+1)*10)
    #     while True:
    #         while count_files(self.output_dir) > self.Length+10:
    #             tfd, tpath = tempfile.mkstemp(suffix=".ts")
    #             with open(tpath, "wb") as tfile:
    #                 dirfilenames = sorted(os.listdir(self.output_dir))
    #                 dirfilenames = dirfilenames[:self.Length]
    #                 for num, videofname in enumerate(dirfilenames):
    #                     if videofname.endswith(".ts"):
    #                         with open(os.path.join(self.output_dir, videofname), "rb") as videofile:
    #                             for line in videofile:
    #                                 tfile.write(line)
    #                         videofile.close()
    #                         os.remove(os.path.join(self.output_dir, videofname))
    #                 tfile.flush()
    #                 os.fsync(tfile.fileno())
    #                 outname = os.path.join(self.get_outdir(), self.joindir,
    #                                        self.channel + '-' + (str(video_seqnum)).zfill(5) + '.mp4')
    #                 ff = FFmpeg(
    #                     global_options=['-y', '-loglevel error'],
    #                     inputs={tpath: None},
    #                     outputs={outname: '-c copy -bsf:a aac_adtstoasc'})
    #                 ff.run()
    #             if self.autofilter_finish and self.cutvideo_finish:
    #                 return True
    #             time.sleep(self.Length * self.freq)
    #             print('------------------------------john is alive-----------------------------------------')



