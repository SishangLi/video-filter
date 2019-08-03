#!/usr/bin/env python3
"""This is the script to join stream"""
import time
import tempfile
import subprocess
import threading
# import multiprocessing

from utils.utils import *
from ffmpy import FFmpeg
from AutoFilter import AutoFilter


class Stream(AutoFilter):
    def __init__(self, channel, outpath, videopath, keywords, vdmode, faceimages):
        super(Stream, self).__init__(channel, outpath, videopath, keywords, vdmode, faceimages)
        self.Length = 10

    def ternimal_handling(self):
        self.global_ternimal_carry[2] = True
        while True:
            print("---------Stream capture the ternimal signal and wait for be terminated ...----------")
            time.sleep(0.01)

    def push(self):
        print("Process push have start ...")
        command = ["ffmpeg", "-loglevel", "error", "-re", "-strict", "-2", "-i", self.videopath, "-preset", "superfast",
                   "-tune", "zerolatency", "-c:v", "libx264", "-c:a", "aac", "-ar", "44100",
                   "-threads", "2", "-f", "flv", os.path.join("rtmp://114.213.210.211/", self.vdmode, self.channel)]
        self.streamcreater_start = True
        use_shell = True if os.name == "nt" else False
        childpush = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     shell=use_shell)
        while childpush.poll() != 0 and not self.global_ternimal_single[0]:
            time.sleep(0.5)
        else:
            if self.global_ternimal_single[0]:
                childpush.communicate('q'.encode())
                self.ternimal_handling()
            elif not self.cutvideo_finish:
                while not self.global_ternimal_single[0]:
                    print('------------Stream exception exit waiting for be terminated---------')
                    time.sleep(1)
                else:
                    self.ternimal_handling()
            else:
                waittime = 60
                while waittime:
                    time.sleep(1)
                    waittime -= 1
                    print('----------------------Push accomplish, exit after one minute-------------------------')
                self.global_finish = True
                return True

    def push_live(self):
        print("Process push have start ...")
        # prewaiting
        wait = self.delay
        while wait:
            time.sleep(1)
            wait -= 1
            print('Stream chips are initing, Push waiting ... ...')
        # loading
        while count_files(self.output_dir) == 0 and not self.global_ternimal_single[0]:
            time.sleep(0.1)
            # print('------------------------------Loading-----------------------------------------------')
        else:
            if self.global_ternimal_single[0]:
                self.ternimal_handling()
        command = ["ffmpeg", "-loglevel", "error", "-f", "concat", "-re", "-i", "list.txt", "-max_muxing_queue_size", "1024", "-c:v",
                   "libx264", "-preset", "superfast", "-tune", "zerolatency", "-c:a", "aac", "-ar", "44100",
                   "-threads", "2", "-f", "flv", os.path.join("rtmp://114.213.210.211/", self.vdmode, self.channel)]
        self.streamcreater_start = True
        use_shell = True if os.name == "nt" else False
        childpushlive = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         shell=use_shell)
        while childpushlive.poll() != 0 and not self.global_ternimal_single[0]:
            time.sleep(0.5)
        else:
            if self.global_ternimal_single[0]:
                childpushlive.communicate('q'.encode())
                self.ternimal_handling()
            else:
                while not self.global_ternimal_single[0]:
                    print('----------------Exception exit waiting for be terminated---------')
                    time.sleep(1)
                else:
                    if self.global_ternimal_single[0]:
                        self.global_ternimal_carry[2] = True
                        self.global_finish = True
                        while True:
                            print("---------Stream capture the ternimal signal and wait for be terminated ...----------")
                            time.sleep(0.01)
        return True

    def join(self):
        self.joindir = self.create_dir('-join')
        video_seqnum = 0
        print("Process john have start ...")
        time.sleep((self.Length+1)*10)
        while True:
            while count_files(self.output_dir) > self.Length+10:
                tfd, tpath = tempfile.mkstemp(suffix=".ts")
                with open(tpath, "wb") as tfile:
                    dirfilenames = sorted(os.listdir(self.output_dir))
                    dirfilenames = dirfilenames[:self.Length]
                    for num, videofname in enumerate(dirfilenames):
                        if videofname.endswith(".ts"):
                            with open(os.path.join(self.output_dir, videofname), "rb") as videofile:
                                for line in videofile:
                                    tfile.write(line)
                            videofile.close()
                            os.remove(os.path.join(self.output_dir, videofname))
                    tfile.flush()
                    os.fsync(tfile.fileno())
                    outname = os.path.join(self.get_outdir(), self.joindir,
                                           self.channel + '-' + (str(video_seqnum)).zfill(5) + '.mp4')
                    ff = FFmpeg(
                        global_options=['-y', '-loglevel error'],
                        inputs={tpath: None},
                        outputs={outname: '-c copy -bsf:a aac_adtstoasc'})
                    ff.run()
                if self.autofilter_finish and self.cutvideo_finish:
                    return True
                time.sleep(self.Length * self.freq)
                print('------------------------------john is alive-----------------------------------------')


if __name__ == "__main__":
    # stream = Stream('CCTV_News', 'None', './video/CCTV_News.mp4', '习近平', 'local', 'filsave')
    stream = Stream('cctv1hd', 'None', 'http://tv6.ustc.edu.cn/hls/cctv1hd.m3u8', '习近平', 'local', None)
    aa = threading.Thread(target=stream.filter_start)
    aa.start()
    # history---------------------------------------------------------------------------1
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




