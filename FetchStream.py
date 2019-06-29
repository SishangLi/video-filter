"""This is the script to fetch hls stream"""
import datetime
import logging
import m3u8
import time
from utils.utils import *
from concurrent.futures import ThreadPoolExecutor
from requests import get
from CutVideo import CutVideo


class FetchStream(CutVideo):
    def __init__(self, channel, outpath, videourl, vdmode):
        super(FetchStream, self).__init__(channel, outpath, videourl, vdmode)
        if vdmode == 'live':
            self.url = videourl
            self.dlset = set()
            self.dlpool = ThreadPoolExecutor(max_workers=4)
            self.logger = logging.getLogger("fetch_hls_stream")
            self.freq = int(m3u8.load(self.url).target_duration)
            self.mktxt()
        else:
            pass

    def download_file(self, uri, outputdir, filename):
        """Download a ts video and save on the outputdir as the following file:
        outputdir/date_filename"""
        try:
            fpath = os.path.join(outputdir, filename)
            with open(fpath, "wb") as file:
                response = get(uri)
                file.write(response.content)
                file.close()
        except Exception as ex:
            self.logger.error(ex)

    def fetch(self):
        """Fetch a HLS stream by periodically retrieving the m3u8 url for new
        playlist video files every freq seconds. For each segment that exists,
        it downloads them to the output directory as a TS video file."""

        print("Process fetch have start ...")
        while not self.global_ternimal_single:
            dynamicplaylist = m3u8.load(self.url)
            for videosegment in dynamicplaylist.segments:
                videouri = videosegment.absolute_uri
                videofname = videosegment.uri.split('/')[3]
                if videofname not in self.dlset:
                    self.dlset.add(videofname)
                    self.dlpool.submit(self.download_file, videouri, self.source_dir, videofname)
            # print("------------------------------fetch is alive------------------------------------------")
            time.sleep(0.1)
        else:
            self.global_ternimal_carry[0] = True
            while True:
                print("---------Fetch capture the ternimal signal and wait for be terminated ...-------------")
                time.sleep(0.001)


if __name__ == "__main__":
    fetcher = FetchStream('cctv1hd', 'None', 'http://tv6.ustc.edu.cn/hls/cctv1hd.m3u8', 'live')
    fetcher.fetch()










