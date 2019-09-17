import cv2
import json
import time
import wave
import math
import m3u8
# import pysrt
import base64
import audioop
import subprocess
import multiprocessing

from utils.utils import *
# from CutVideo import CutVideo
from FetchStream import FetchStream

from urllib.request import urlopen
from urllib.request import Request
from urllib.error import URLError
from urllib.parse import urlencode
from moviepy.editor import VideoFileClip

import FaceRecognition as FR
from progressbar import ProgressBar, Percentage, Bar, ETA

API_KEY = '4brKeEDaGTzSn9AbmXR0B6gs'
SECRET_KEY = 'FAoMX8GofXvdiA0XXBAOE7GE3yKftIyI'


def which(program):
    """
    Return the path for a given executable.
    """
    def is_exe(file_path):
        """
        Checks whether a file is executable.
        """
        return os.path.isfile(file_path) and os.access(file_path, os.X_OK)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


# 从视频中提取音频
def extract_audio(filepath, channels=1, rate=16000):
    if not os.path.isfile(filepath):
        print("The given file does not exist: {}".format(filepath))
        raise Exception("Invalid filepath: {}".format(filepath))
    if not which("ffmpeg"):
        print("ffmpeg: Executable not found on machine.")
        raise Exception("Dependency not found: ffmpeg")
    dirname = (os.path.split(filepath)[-1]).split(".")[0]
    filename = (os.path.split(filepath)[-1]).split(".")[0] + str('.wav')
    if not os.path.exists(dirname):
        os.mkdir(str(dirname))
    tempname = os.path.join(os.getcwd(), str(dirname), filename)
    command = ["ffmpeg", "-y", "-i", filepath, "-ac", str(channels), "-ar", str(rate), "-loglevel", "error", tempname]
    use_shell = True if os.name == "nt" else False
    subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
    return tempname, dirname


# 声音检测中用到的函数，阈值判断
def percentile(arr, percent):
    arr = sorted(arr)
    k = (len(arr) - 1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return arr[int(k)]
    d0 = arr[int(f)] * (c - k)
    d1 = arr[int(c)] * (k - f)
    return d0 + d1


# 寻找音频中有话语的片段，并记录
def find_speech_regions(filename, frame_width=4096, min_region_size=0.5, max_region_size=6):
    reader = wave.open(filename)
    sample_width = reader.getsampwidth()
    rate = reader.getframerate()
    n_channels = reader.getnchannels()
    chunk_duration = float(frame_width) / rate
    n_chunks = int(math.ceil(reader.getnframes()*1.0 / frame_width))
    energies = []
    for i in range(n_chunks):
        chunk = reader.readframes(frame_width)
        energies.append(audioop.rms(chunk, sample_width * n_channels))
    threshold = percentile(energies, 0.2)
    elapsed_time = 0
    regions = []
    region_start = None
    num = 0
    for energy in energies:
        is_silence = energy <= threshold
        max_exceeded = region_start and elapsed_time - region_start >= max_region_size
        if (max_exceeded or is_silence) and region_start:
            if elapsed_time - region_start >= min_region_size:
                num = num + 1
                regions.append((region_start, elapsed_time, num))
                region_start = None
        elif (not region_start) and (not is_silence):
            region_start = elapsed_time
        elapsed_time += chunk_duration
    return regions


# 按照记录的有话语的时间戳将片段从音频中切出
class WAVConverter(object):
    def __init__(self, include_before=0.25, include_after=0.25):
        self.source_path = None
        self.dirname = None
        self.include_before = include_before
        self.include_after = include_after

    def __call__(self, region):
        try:
            start, end, num = region
            start = max(0, start - self.include_before)
            end += self.include_after
            tempname = os.path.join(os.getcwd(), str(self.dirname), str(self.dirname) + str(num) + '.wav')
            command = ["ffmpeg", "-ss", str(start), "-t", str(end - start), "-y", "-i", self.source_path,
                       "-loglevel", "error", tempname]
            use_shell = True if os.name == "nt" else False
            subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
            return tempname
        except KeyboardInterrupt:
            return 1


# 调用百度语音转录API进行语音识别并回传
class SpeechRecognizer(object):
    def __init__(self, api_key, secret_key, rate, audioformat='wav', retries=3):
        self.api_key = api_key
        self.secret_ket = secret_key
        self.rate = rate
        self.format = audioformat
        self.dev_pid = 1536  # 1537 表示识别普通话，使用输入法模型。1536表示识别普通话，使用搜索模型
        self.cuid = '123456PYTHON'
        self.asr_url = 'http://vop.baidu.com/server_api'
        self.token_url = 'http://openapi.baidu.com/oauth/2.0/token'
        self.scope = 'audio_voice_assistant_get'  # 若授权认证返回值中没有此字符串，那么表示用户应用中没有开通asr功能，需要到网页端开通
        self.retries = retries
        self.token = self.fetch_token()

    def fetch_token(self):
        params = {'grant_type': 'client_credentials',
                  'client_id': self.api_key,
                  'client_secret': self.secret_ket}
        post_data = urlencode(params)
        post_data = post_data.encode('utf-8')
        req = Request(self.token_url, post_data)

        try:
            f = urlopen(req)
            result_str = f.read()
        except URLError as err:
            result_str = err.read()
            print('token http response http code : ' + str(err.code) + str(result_str))
            return 1

        result_str = result_str.decode()
        result = json.loads(result_str)
        if 'access_token' in result.keys() and 'scope' in result.keys():
            if self.scope not in result['scope'].split(' '):
                print('scope is not correct')
                return 0
            # print('SUCCESS WITH TOKEN: %s ; EXPIRES IN SECONDS: %s' % (result['access_token'], result['expires_in']))
            print('API Handshake success')
            return result['access_token']
        else:
            print('MAYBE API_KEY or SECRET_KEY not correct: access_token or scope not found in token response')
            return 0

    def __call__(self, filepath):
        with open(filepath, 'rb') as speech_file:
            speech_data = speech_file.read()
        length = len(speech_data)
        if length == 0:
            print('file %s length read 0 bytes' % filepath)
            return 1
        for i in range(self.retries):
            speech = base64.b64encode(speech_data)
            speech = str(speech, 'utf-8')
            params = {'dev_pid': self.dev_pid,
                      'format': self.format,
                      'rate': self.rate,
                      'token': self.token,
                      'cuid': self.cuid,
                      'channel': 1,
                      'speech': speech,
                      'len': length
                      }
            post_data = json.dumps(params, sort_keys=False)
            # print post_data
            req = Request(self.asr_url, post_data.encode('utf-8'))
            req.add_header('Content-Type', 'application/json')
            try:
                f = urlopen(req)
                result_str = f.read()
                result_str = str(result_str, 'utf-8')
                if ((json.loads(result_str))["err_no"]) == 0:
                    result_str = ((json.loads(result_str))["result"])[0]
                    return result_str
                elif ((json.loads(result_str))["err_no"]) == 3301:
                    # print('Poor audio quality, processed as blank voice!')
                    return ''
                elif ((json.loads(result_str))["err_no"]) == 3302:
                    self.token = self.fetch_token()
                    continue
                else:
                    error_no = ((json.loads(result_str))["err_no"])
                    print('Error % s' % error_no)
                    continue
            except URLError as err:
                print('asr http response http code : ' + str(err.code) + str(err.read()))
                continue

        print("Retry failed !")
        return 'Conversion failed'


# 语音识别最高层的一个API
class AutoSub(object):
    def __init__(self, _concurrency=10):
        self.subformat = 'srt'
        self.pool = multiprocessing.Pool(_concurrency)
        self.converter = WAVConverter()
        self.recognizer = SpeechRecognizer(api_key=API_KEY, secret_key=SECRET_KEY, rate=16000)

    def __call__(self, filepath):
        audio_filename, dirname = extract_audio(filepath)
        regions = find_speech_regions(audio_filename)
        transcripts = []
        self.converter.source_path = audio_filename
        self.converter.dirname = dirname
        if regions:
            try:
                widgets = ["Converting speech regions to WAV files: ", Percentage(), ' ', Bar(), ' ', ETA()]
                pbar = ProgressBar(widgets=widgets, maxval=len(regions)).start()
                extracted_regions = []
                for i, extracted_region in enumerate(self.pool.imap(self.converter, regions)):
                    extracted_regions.append(extracted_region)
                    pbar.update(i)
                pbar.finish()
                widgets = ["Performing speech recognition: ", Percentage(), ' ', Bar(), ' ', ETA()]
                pbar = ProgressBar(widgets=widgets, maxval=len(regions)).start()
                for i, transcript in enumerate(self.pool.imap(self.recognizer, extracted_regions)):
                    if transcript == 1:
                        return 0
                    else:
                        transcripts.append(transcript)
                    pbar.update(i)
                pbar.finish()
            except KeyboardInterrupt:
                pbar.finish()
                self.pool.terminate()
                self.pool.join()
                print("Cancelling transcription")
                return 0
        timed_subtitles = [(r, t) for r, t in zip(regions, transcripts) if t]
        "Creat the sub file"
        dest = None
        # formatter = FORMATTERS.get(self.subformat)
        # formatted_subtitles = formatter(timed_subtitles)
        #
        # base, ext = os.path.splitext(filepath)
        # dest = "{base}.{format}".format(base=base, format=self.subformat)
        #
        # with open(dest, 'wb') as f:
        #     f.write(formatted_subtitles.encode("utf-8"))
        shutil.rmtree(str(self.converter.dirname))
        return dest, timed_subtitles


# 自动过滤综合（最上层）API
class AutoFilter(FetchStream):
    def __init__(self, channel, outpath, videopath, keywords, vdmode, faceimages):
        super(AutoFilter, self).__init__(channel, outpath, videopath, vdmode)
        self.keywords = keywords
        self.sub_creater = AutoSub()
        self.img_enlarge_times = self.get_video_size(self.videopath) if self.vdmode == 'local' else 0
        self.face_recognizer = FR.Facedetection(faceimages, self.global_ternimal_single, self.img_enlarge_times)
        self.filedset = set()
        self.history = {}

    @staticmethod
    def get_video_size(video):
        """本地视频获取视频大小，根据大小调整人脸识别中使用的分辨率，分辨率太大会耗时太多，影响时效性"""
        cap = cv2.VideoCapture(video)
        count = 5
        while count and not cap.isOpened():
            cap = cv2.VideoCapture(video)
            count -= 1  # 读五次
            if not count and not cap.isOpened():
                print('Read error !')
                return
        _, frame = cap.read()  # success：是否读取到帧 frame：截取到一帧图像，三维矩阵表示
        size = frame.shape
        large_time = 1 if size[0] * size[1] < 384000 else 0
        cap.release()
        return large_time

    def keyword_search(self, srcfilepath):
        """调用语音识别API进行语音识别，并搜多关键词，若存在关键词返回相关信息"""
        _, subcontent = self.sub_creater(srcfilepath)
        chips = []
        for key_word in self.keywords:
            sub_records = [segment[0] for segment in subcontent if segment[1].find(key_word) is not -1]
            for item in sub_records:
                temp = Chip(self.channel)
                temp.length = item
                temp.way = 'Sub'
                temp.keyfeature = key_word
                chips.append(temp)
        return chips

    def keyface_search(self, srcfilepath):
        """调用人脸识别API进行人脸检测，若存在关键人脸返回相关信息"""
        facecontent = self.face_recognizer.start(srcfilepath)
        chips = []
        for person in facecontent:
            face_records = [item for item in facecontent[person].time_show]
            for item in face_records:
                temp = Chip(self.channel)
                temp.length = item
                temp.way = 'Face'
                temp.keyfeature = person
                chips.append(temp)
        return chips

    def filter_save(self, filename):
        """过滤器主函数，用来调用人脸和关键词过滤，并按回传的片段进行切割，存储到相关文件夹"""
        srcfilepath = os.path.join(self.get_outdir(), self.source_dir, filename)
        dstfilepath = os.path.join(self.get_outdir(), self.output_dir, filename) if self.vdmode == 'local' else \
            os.path.join(self.get_outdir(), self.output_dir,
                         self.channel + '-' + str(self.out_order_num).zfill(5) + '.ts')
        self.out_order_num += 1
        if self.vdmode == 'live':
            while not os.path.exists(srcfilepath) or os.path.getsize(srcfilepath) == 0:
                time.sleep(1)
                print("This chip is downloading ... ...")
            if (os.path.getsize(srcfilepath) > 0) and (os.path.getsize(srcfilepath) / (1024 * 1024) < 0.5):
                os.remove(srcfilepath)
                self.out_order_num -= 1
                print("Broken piece, skip !")
                return False

        chips = self.keyword_search(srcfilepath)
        chips += self.keyface_search(srcfilepath)

        if len(chips) == 0:
            shutil.move(srcfilepath, dstfilepath)
            return True
        else:
            exname = '.mp4'
            for num, chip in enumerate(chips):
                starttime = mktime_form(int(chip.length[0]))
                endtime = mktime_form(int(chip.length[1]) + 1) \
                    if int(chip.length[1]) + 1 < VideoFileClip(srcfilepath).duration \
                    else mktime_form(int(VideoFileClip(srcfilepath).duration))
                if starttime == endtime:
                    continue

                outfile = os.path.join(self.get_outdir(), self.chips_dir,
                                       (os.path.split(srcfilepath)[-1]).split(".")[0] + '_' + str(num) + exname)
                chip.chipname = (os.path.split(srcfilepath)[-1]).split(".")[0] + '_' + str(num) + exname
                chip.path = os.path.join(self.get_outdir(), self.chips_dir)
                command = ["ffmpeg", "-loglevel", "error", "-y", "-i", srcfilepath, "-ss", starttime,
                           "-to", endtime, "-c:v", "libx264", "-c:a", "aac", "-ar", "44100", outfile]
                use_shell = True if os.name == "nt" else False
                subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
                self.history[chip.chipname] = [chip.chipname, chip.source, chip.way, chip.length, chip.keyfeature]
            shutil.move(srcfilepath, dstfilepath)

    def filter_start(self):
        """过滤器控制函数，用来加载新的片段并启动过滤，监测全局开始和停止信号以及过滤任务（本地和直播两种模式）的判断"""
        print("Process autosub have start ...")
        # prewaiting
        wait = self.delay
        while wait:
            time.sleep(1)
            wait -= 2
            print('Stream chips are initing, Filter waiting ... ...')
        while not (self.global_ternimal_single[0] or self.autofilter_finish):
            while self.vdmode == 'local' and not os.path.exists(self.m3u8path):
                time.sleep(2)
                print("No m3u8 file was detected! Wating ... ...")
            while count_files(self.source_dir) < 2 and not self.global_ternimal_single[0]:
                time.sleep(1)
                print('Too few buffer files, downloading ...')
            dynamicplaylist = m3u8.load(self.m3u8path) if self.vdmode == 'local' else m3u8.load(self.url)
            for filename in dynamicplaylist.files:
                filename = filename if self.vdmode == 'local' else filename.split('/')[-1]
                if filename not in self.filedset and not self.global_ternimal_single[0]:
                    self.filedset.add(filename)
                    self.filter_save(filename)
            # print('------------------------------sub is alive------------------------------------------')
            time.sleep(0.1)
            if dynamicplaylist.data['is_endlist'] and self.cutvideo_finish:
                self.autofilter_finish = True
        else:
            if self.global_ternimal_single[0]:
                self.global_ternimal_carry[1] = True
                while True:
                    # print("-Sub capture the ternimal signal and wait for be terminated ...-")
                    time.sleep(0.01)
            else:
                while not self.global_finish:
                    # print("-----------Video filter has accomplished! Sleeping...------------")
                    time.sleep(1)
                else:
                    while True:
                        # print("-Video filter has accomplished and wait for be terminated ...-")
                        time.sleep(0.01)


if __name__ == "__main__":
    autofilter = AutoFilter('cctv1hd', 'None', 'http://tv6.ustc.edu.cn/hls/cctv1hd.m3u8',
                            '习近平', 'live', 'filsave', None)
    autofilter.filter_start()

# def filter(self, filename):
#     srcfilepath = os.path.join(self.get_outdir(), self.source_dir, filename)
#     dstfilepath = os.path.join(self.get_outdir(), self.output_dir, filename)
#     tempfiles = "concat:"
#     if self.vdmode == 'live':
#         while os.path.getsize(srcfilepath) == 0:
#             time.sleep(0.5)
#             print("This chip is downloading ... ...")
#         if (os.path.getsize(srcfilepath) > 0) and (os.path.getsize(srcfilepath) / (1024 * 1024) < 1):
#             os.remove(srcfilepath)
#             print("Broken piece, skip !")
#             time.sleep(1)
#             return False
#     _, subcontent = self.sub_creater(srcfilepath)
#     records = self.keyword_search(srcfilepath)
#     if len(records) == 0:
#         shutil.move(srcfilepath, dstfilepath)
#         return True
#     else:
#         tempdir = (os.path.split(srcfilepath)[-1]).split(".")[0]
#         self.new_common_dir(tempdir)
#         exname = (os.path.split(srcfilepath)[-1]).split(".")[-1]
#         nums = len(records) if int(records[0][0]) == 0 else len(records) + 1
#         for num in range(nums):
#             starttime = mktime_form(int(records[num - 1][1])) if not num == 0 else mktime_form(0)
#             endtime = mktime_form(int(records[num][0]) + 1) if not num == nums - 1 \
#                 else mktime_form(int(VideoFileClip(srcfilepath).duration))
#             tempfile = os.path.join(self.get_outdir(), str(tempdir),
#                                     (os.path.split(srcfilepath)[-1]).split(".")[0] + '_' + str(num) + '.' + exname)
#             tempfiles = tempfiles + tempfile + "|"
#
#             command = ["ffmpeg", "-loglevel", "error", "-y", "-i", srcfilepath, "-ss", starttime,
#                        "-to", endtime, "-c:v", "libx264", "-c:a", "aac", "-ar", "44100", tempfile]
#             use_shell = True if os.name == "nt" else False
#             subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
#
#         tempfile = dstfilepath
#         tempfiles = tempfiles[:-1]
#         command = ["ffmpeg", "-y", "-i", tempfiles, "-c", "copy", tempfile]
#         use_shell = True if os.name == "nt" else False
#         subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
#         os.remove(srcfilepath)
#         if os.path.exists(os.path.join(self.get_outdir(), str(tempdir))):
#             shutil.rmtree(os.path.join(self.get_outdir(), str(tempdir)))



