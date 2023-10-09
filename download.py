from os import path
from typing import List, Mapping

from pytube import YouTube
# import youtube_dl
import yt_dlp as youtube_dl
from moviepy.editor import VideoFileClip

from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

class YoutubeScraper():
    @staticmethod
    def search(*keywords: str, wait_time: int = 2) -> str:
        driver = webdriver.Chrome()
        query: str = "https://www.youtube.com/results?search_query=" + "+".join(keywords)
        
        try:
            driver.get(query)
            driver.implicitly_wait(wait_time)
            page_source = driver.page_source

        finally:
            driver.quit()

        return page_source

    @staticmethod
    def get_video_info(url: str) -> Mapping[str, str]:
        video = YouTube(url)
        video_info = {
            "Title": video.title,
            "Author": video.author,
            "Views": video.views,
            "Description": video.description,
            "Publish Date": video.publish_date,
            "Length (seconds)": video.length,
        }
        return video_info

class HTMLParser():
    @staticmethod
    def find_ytb_videos(page_source: str, limit: int = 10) -> List[str]:
        soup = BeautifulSoup(page_source, 'html.parser')
        contents = soup.find(id="contents").find("ytd-item-section-renderer").find(id="contents")
        results = []

        for i, child in enumerate(contents.children):
            link = child.find("a")
            if not link:
                break

            results.append("https://youtube.com" + link["href"])
            if i == limit - 1:
                break

        return results


class YoutubeDownloader():
    @staticmethod
    def download(url: str, folder: str) -> bool:
        methods = [YoutubeDownloader._download_pytube, YoutubeDownloader._download_ytdl]
        
        success = False
        i = 0
        while not success and i < len(methods):
            success = methods[i](url, folder)
        
        return success

    @staticmethod
    def _download_pytube(url: str, folder: str) -> bool:
        try:
            yt = YouTube(url)
            video_path = yt.title
            video_path = yt.streams.get_highest_resolution().download(folder)
            video_path = yt.streams.filter(file_extension="mp4").get_highest_resolution().download(folder)
            return True
        except:
            return False

    @staticmethod
    def _download_ytdl(url: str, folder: str) -> bool:
        try:
            ydl_opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "outtmpl": folder + "/%(title)s",
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except:
            return False


class AudioConverter():
    @staticmethod
    def convert_videos_to_audio(video_folder: str, audio_folder: str) -> None:
        for video_path in Path(video_folder).iterdir():
            video = VideoFileClip(str(video_path))
            name = video.filename.split(".")[-2].split("\\")[-1] + ".mp3"
            video.audio.write_audiofile(f"{audio_folder}/{name}")


class DownloadManager():
    def __init__(self, default_number_videos: int = 3, target_audio_folder: str = "mp3s", target_video_folder: str = "videos", tmp_folder: str = "tmp") -> None:
        self.save_audio: bool = self._get_input("Do you want to extract the audio from downloaded videos ? yes / no : ", ["yes", "no"]) == "yes"
        print("not " * (not self.save_audio) + "saving audio\n")

        self.n_videos = default_number_videos
        self.audio_folder = target_audio_folder
        self.video_folder = target_video_folder
        self.tmp_folder = tmp_folder

    def run(self):
        while True:
            answer = input("Enter a query (i.e. list of keywords) to search on youtube. Type \"quit\" to exit program.\n")
            if answer.lower() == "quit":
                break

            self._handle_query(*answer.split(" "))
        
        if self.save_audio:
            AudioConverter.convert_videos_to_audio(self.tmp_folder, self.audio_folder)

    def _handle_query(self, *keywords, query_wait_time: int = 2):
        page_content = YoutubeScraper.search(*keywords, wait_time=query_wait_time)
        
        n_videos = self.n_videos
        while True:
            video_links = HTMLParser.find_ytb_videos(page_content, n_videos)
            print(f"\n{min(n_videos, len(video_links))} videos have been found.\n")

            for idx, link in enumerate(video_links):
                print(f"Option no. {idx + 1}")
                self._show_video_info(link)
                print()
                print("------------------")
                print()

            if len(video_links) < n_videos:
                answer = self._get_input("Type in the number of the video you want to download, or type 'cancel' to cancel. Type 'restart' to search for videos again with more loading time for the browser. \n", ["cancel", "restart"] + [f"{i+1}" for i in range(n_videos)])
            else:
                answer = self._get_input("Type in the number of the video you want to download, type 'more' to see more options, or type 'cancel' to cancel. \n", ["more", "cancel"] + [f"{i+1}" for i in range(n_videos)])

            if answer == "more":
                n_videos *= 2
            elif answer == "cancel":
                return
            elif answer == "restart":
                t = "a"
                while not t.isnumeric():
                    t = input("How much time do you want to give the browser to look for videos ? \n")
                self._handle_query(*keywords, t)
                return

            else:
                chosen_video_idx = int(answer) - 1
                break
        
        url = video_links[chosen_video_idx]
        info = YoutubeScraper.get_video_info(url)
        print(f"""\nDownloading {info["Title"]}, from {info["Author"]}...\n""")
        YoutubeDownloader.download(video_links[chosen_video_idx], self.tmp_folder)


    def _show_video_info(self, url):
        info = YoutubeScraper.get_video_info(url)
        for key, value in info.items():
            print(f"{key}: {value}")

    
    def _get_input(self, message: str, accepted_values: List[str]) -> str:
        result = None
        while result not in accepted_values:
            result = input(message)
        return result

if __name__ == "__main__":
    
    download_manager = DownloadManager()
    download_manager.run()

    # save_audio = input("Save audio too ? y / n : ") == "y"
    # print("not " * (not save_audio) + "saving audio")
    # multiple_urls = input("Input single successive or multipe urls ? s / m : ") == "m"
    # print("You will be prompted to enter your urls" if multiple_urls else "Wait for each download after entering a url")

    # if not multiple_urls:
    #     ytb_link = input("Input the youtube URL, or type 'q' to stop the program :\n")
    #     while ytb_link != "q":
    #         download(ytb_link, save_audio)
    #         ytb_link = input("\nInput the youtube URL, or type 'q' to stop the program :\n")
    # else:
    #     urls = []
    #     input_str = input("Enter url, or press enter to stop:\n")
    #     while input_str != "":
    #         urls.append(input_str)
    #         input_str = input("Enter url, or press enter to stop:\n")
    #     for url in tqdm(urls, desc="Videos downloaded"):
    #         print("downloading ...")
    #         download(url, save_audio)

    # if save_audio:
    #     convert_videos_to_audio("tmp_videos")
