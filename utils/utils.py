import os
import shutil
from tqdm import tqdm


VIDEOPATH = '../video/CCTV_News.mp4'


class VideoFilter(object):
    def __init__(self, channel, outpath, vdmode):
        self.cutvideo_finish = False
        self.autofilter_finish = False
        self.streamcreater_start = False
        self.global_finish = False
        self.global_ternimal_single = False
        self.global_ternimal_carry = [False, False, False]
        self.freq = 10
        self.delay = 10
        self.out_order_num = 0
        self.channel = channel
        self.outpath = outpath
        self.vdmode = vdmode
        self.source_dir_comment = '-source'
        self.chips_dir_comment = '-chips'
        self.output_dir_comment = ''
        self.source_dir = self.create_dir(self.source_dir_comment)
        self.chips_dir = self.create_dir(self.chips_dir_comment)
        self.output_dir = self.create_dir(self.output_dir_comment)

    def get_outdir(self):
        if self.outpath == 'None':
            return os.getcwd()
        else:
            return self.outpath

    def create_dir(self, comment):
        new_dir = os.path.join(self.get_outdir(), self.channel + comment)
        if not os.path.exists(new_dir):
            os.mkdir(new_dir)
            return new_dir
        else:
            shutil.rmtree(new_dir)
            os.mkdir(new_dir)
            return new_dir

    def new_common_dir(self, comment):
        new_dir = os.path.join(self.get_outdir(), comment)
        if not os.path.exists(new_dir):
            os.mkdir(new_dir)
            return new_dir
        else:
            shutil.rmtree(new_dir)
            os.mkdir(new_dir)
            return new_dir

    def fill_list_txt(self):
        _list = []
        if self.outpath == 'None':
            for num in tqdm(range(1000)):
                item = 'file' + ' ' + '\'' + os.path.join(self.channel,
                                                          self.channel + '-' + (str(num)).zfill(5) + '.ts') + '\''
                _list.append(item)
        else:
            for num in tqdm(range(1000)):
                item = 'file' + ' ' + '\'' + os.path.join(self.outpath, self.channel,
                                                          self.channel + '-' + (str(num)).zfill(5) + '.ts') + '\''
                _list.append(item)
        return _list

    def mktxt(self):
        txt_concant = self.fill_list_txt()
        filewrite('./list.txt', txt_concant)

    def clear_dir(self):
        shutil.rmtree(self.source_dir)
        shutil.rmtree(self.chips_dir)
        shutil.rmtree(self.output_dir)



class Chip:
    def __init__(self, video_source):
        self.source = video_source
        self.way = ''
        self.length = ''
        self.keyfeature = ''
        self.chipname = ''


def get_filelist(dir_, filelist, ignoredir_):
    if os.path.isfile(dir_):
        filelist.append(dir_)
    elif os.path.isdir(dir_):
        for item_ in os.listdir(dir_):
            if item_ == ignoredir_:
                continue
            newdir = os.path.join(dir_, item_)
            get_filelist(newdir, filelist, ignoredir_)
    return filelist


def count_files(path):
    count = 0
    for _ in os.listdir(os.path.join(os.getcwd(), path)):  # fn 表示的是文件名
        count = count + 1
    return count


def mktime_form(_second):
    hours = _second//3600
    minutes = (_second % 3600)//60
    seconds = ((_second % 3600) % 60)
    return str(hours) + ":" + str(minutes).zfill(2) + ":" + str(seconds).zfill(2)


def filewrite(_filename, _cache, way='w'):
    with open(_filename, way) as f:
        for line in _cache:
            f.writelines('{}\n'.format(line))
            # f.write('{}\n'.format(line))
    f.close()


if __name__ == "__main__":
    # channel = (URL.split('/')[-1])[:-5]  # live
    channel = (os.path.split(VIDEOPATH)[-1])[:-4]  # local



# tempfile3 = os.path.join(os.getcwd(), str(tempdir), "padding.ts")
# command3 = ["ffmpeg", "-r", "25", "-loop", "1", "-i", "padding.jpeg", "-pix_fmt", "yuv420p",
#             "-vcodec", "libx264", "-b:v", "600k", "-r:v", "25", "-preset", "medium", "-crf",
#             "30", "-s", "1920x1080", "-vframes", "250", "-r", "25", "-t",
#             str((segment[0])[1] - (segment[0])[0]), tempfile3]
# After filtering, you can add fill in the original location, you can generate video.
# However, it is not possible to merge with the original video yet, and there will be a problem.


