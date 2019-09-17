import time
import subprocess
from utils.utils import *


class CutVideo(VideoFilter):
    def __init__(self, channel, outpath, videopath, vdmode):
        super(CutVideo, self).__init__(channel, outpath, vdmode)
        if vdmode == 'local':
            self.videopath = os.path.join(self.get_outdir(), videopath)
            self.m3u8path = os.path.join(self.source_dir, self.channel + '.m3u8')
        else:
            pass

    # 视频切割
    def cut_start(self):
        print("Process Cut have start ...")
        if not os.path.exists(self.videopath):
            print('Invalid input video path!')
            return 1
        command = ["ffmpeg", "-loglevel", "error", "-re", "-strict", "-2", "-i", self.videopath, "-preset", "superfast",
                   "-tune", "zerolatency", "-c:v", "copy", "-c:a", "copy",
                   "-f", "hls", "-threads", "2", "-hls_time", str(self.freq), "-hls_list_size", "10", "-hls_wrap",
                   "200", self.m3u8path]
        use_shell = True if os.name == "nt" else False
        childcut = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    shell=use_shell)
        while childcut.poll() != 0 and not self.global_ternimal_single[0]:
            time.sleep(0.1)
        else:
            if self.global_ternimal_single[0]:
                childcut.communicate('q'.encode())
                self.global_ternimal_carry[0] = True
                while True:
                    # print("---------Cut capture the ternimal signal and wait for be terminated ...-------------")
                    time.sleep(0.01)
            else:
                self.cutvideo_finish = True
                while not self.global_finish:
                    # print("------------------------Video cut has accomplished! Sleeping...---------------------")
                    time.sleep(1)
                else:
                    while True:
                        # print("-Video cut has accomplished and wait for be terminated ...-")
                        time.sleep(0.01)


if __name__ == "__main__":
    cuter = CutVideo('CCTV_News', 'None', '../video/CCTV_News.mp4', 'local')
    cuter.cut_start()


