from multiprocessing.sharedctypes import Value
from tkinter import Image
from boto3 import client, resource
from datetime import datetime, timedelta
from icrawler.builtin import GoogleImageCrawler
from os import path, listdir, remove
from random import randint, uniform
from re import sub as char_sub
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from shutil import copy, move
from subprocess import Popen, PIPE
from time import sleep
from time import sleep, time
from urllib.request import urlretrieve
from webdriver_manager.chrome import ChromeDriverManager
import pageviewapi
import wikipedia
from PIL import Image
from moviepy.editor import *
from traceback import format_exc
from math import ceil

class Wikipediator:

    def __init__(self):

        fileLocation = path.abspath(__file__)
        if fileLocation.rfind('/') >= 0:
            self.conjoiner = '/'

            options = Options()
            options.headless = True
            driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
        else:
            self.conjoiner = '\\'

            options = webdriver.ChromeOptions()
            # options.add_argument("--headless")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        instance = fileLocation.rfind(self.conjoiner)
        self.directory = fileLocation[0:instance]

        self.driver = driver
        self.usedTextfile = self.directory+self.conjoiner+'used.txt'
        self.uploadVideoTextfile = self.directory+self.conjoiner+'upload_video.txt'
        self.uploadVideoSH = self.directory+self.conjoiner+'upload_video.sh'
        self.audio = self.directory+self.conjoiner+'Audio'
        self.extraImages = self.directory+self.conjoiner+'Extra Images'
        self.mainImages = self.directory+self.conjoiner+'Main Images'
        self.finalVideo = self.directory+self.conjoiner+'Final Video'

        s3client = client('s3', aws_access_key_id=open(self.directory+self.conjoiner+'aws_access.txt').read() , aws_secret_access_key=open(self.directory+self.conjoiner+'aws_secret.txt').read())
        self.s3client = s3client

    def cleanList(self, list):

        for counter in range(len(list)):
            list[counter] = list[counter].strip()
        
        return list

    def textToSpeech(self, TTStext):

        if len(listdir(self.audio)) != 0:
            print('already audio')
            return self.audio+self.conjoiner+listdir(self.audio)[0], listdir(self.audio)[0]

        polly = client('polly')
        startResponse = polly.start_speech_synthesis_task(Engine='neural', OutputS3BucketName='braunbucket2004', Text=TTStext, OutputFormat='mp3', VoiceId='Amy')
        taskID = startResponse['SynthesisTask']['TaskId']

        while(1):
            getResponse = polly.get_speech_synthesis_task(TaskId=taskID)
            sleep(5)
            if getResponse['SynthesisTask']['TaskStatus'] == 'completed':
                break
            
        self.s3client.download_file('braunbucket2004', getResponse['SynthesisTask']['TaskId']+'.mp3', self.audio+self.conjoiner+getResponse['SynthesisTask']['TaskId']+'.mp3')

        return self.audio+self.conjoiner+getResponse['SynthesisTask']['TaskId']+'.mp3', getResponse['SynthesisTask']['TaskId']+'.mp3'

    def getTopWikipedia(self, amountOfTopics):
        yesterday = datetime.strftime(datetime.now() - timedelta(1), '%Y %m %d').split(' ')
        results = pageviewapi.top('en.wikipedia', yesterday[0], yesterday[1], yesterday[2], access='all-access')
        try:
            usedPages = self.cleanList(open(self.usedTextfile, 'r', encoding='utf-8').readlines())
        except UnicodeDecodeError as e:
            print(e)
            usedPages = self.cleanList(open(self.usedTextfile, 'r', encoding='latin-1').readlines())
        valid, counter = [], 0

        while(len(valid) < amountOfTopics):
            article = results['items'][0]['articles'][counter]
            pageTitle = article['article']
            if (pageTitle != 'Main_Page') and (':' not in pageTitle) and (pageTitle not in usedPages) and ('Deaths_in' not in pageTitle):
                with open(self.usedTextfile, "a+", encoding='utf-8') as file_object:
                    file_object.seek(0)
                    data = file_object.read(100)
                    if len(data) > 0:
                        file_object.write("\n")
                    file_object.write(pageTitle)
                
                sleep(uniform(2,6))
                try:
                    summary = char_sub("[\(\[].*?[\)\]]", "", wikipedia.summary(pageTitle, auto_suggest=False))
                    summary = char_sub("{.*?}", "", summary)
                    
                    replaceList = ['\n', "\'", ';">']
                    for string in replaceList:
                        summary = summary.replace(string,'')

                except wikipedia.exceptions.PageError as e:
                    print(e)
                    summary = ''

                if len(summary) >= 1800:
                    valid.append([pageTitle, summary])
                    print('Topics extracted: '+str(len(valid)))

            counter+=1
        
        return valid

    def cleanUp(self, bucketFileID):

        for file in listdir(self.audio):
            remove(self.audio+self.conjoiner+file)
        for file in listdir(self.extraImages):
            remove(self.extraImages+self.conjoiner+file)

        s3 = resource('s3')
        s3.Object('braunbucket2004', bucketFileID).delete()
    
    def extractImages(self, pageTitle):

        self.driver.get('https://en.wikipedia.org/wiki/'+(pageTitle))
        randomChoose = False

        try:
            mainImage = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'infobox-image')))
            tag = WebDriverWait(mainImage, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'a')))
            href = tag.get_attribute('href')
            imageName = href[href.rfind('/')+6:]
            src = WebDriverWait(mainImage, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'img'))).get_attribute('src')
            urlretrieve('https://upload.wikimedia.org/wikipedia/commons/'+src[53:58]+imageName, self.mainImages+self.conjoiner+'MAIN_IMAGE.jpg')
        except Exception as e:
            print('main image error:'+str(e)+'('+imageName+')')
            randomChoose = True

        imageSections = WebDriverWait(self.driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'thumbinner')))
        imageSections.append(WebDriverWait(self.driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'thumb'))))
        imageData = []

        for section in imageSections:
            
            try:
                section.find_element(By.CLASS_NAME, 'tsingle')
            except Exception:
                pass
            else:
                continue

            try:
                imageName = 'invalid'
                tag = WebDriverWait(section, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'a')))
                href = tag.get_attribute('href')
                if '.gif' in href:
                    continue
                imageName = href[href.rfind('/')+6:]
                src = WebDriverWait(section, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'thumbimage'))).get_attribute('src')
                urlretrieve('https://upload.wikimedia.org/wikipedia/commons/'+src[53:58]+imageName, self.mainImages+self.conjoiner+imageName)
                if (self.mainImages+self.conjoiner+imageName)[-3:] != 'jpg':
                    remove(self.mainImages+self.conjoiner+imageName)
                    continue
                caption = WebDriverWait(section, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'thumbcaption'))).text
                imageData.append([caption, imageName])
            except Exception as e:
                continue
        
        imageNames = []
        for name in range(len(imageData)):
            imageNames.append(imageData[name][1])

        validImages = listdir(self.mainImages)
        for counter in range(len(imageNames)):
            if imageNames[counter] not in validImages:
                imageData.pop(counter)
    
        if randomChoose == True:
            extractedImages = listdir(self.mainImages)
            chosenImage = extractedImages[randint(0,len(extractedImages)-1)]
            copy(self.mainImages+self.conjoiner+chosenImage, self.mainImages+self.conjoiner+'MAIN_IMAGE.jpg')
        
        return imageData

    def getExtraImages(self, pageTitle, pageText):
        
        totalNeededImages = (len(pageText)//70)+1
        extraImagesNeeded = totalNeededImages - len(listdir(self.mainImages))

        if extraImagesNeeded > 0:
            google_crawler = GoogleImageCrawler(storage={'root_dir' : self.extraImages})
            google_crawler.crawl(keyword=pageTitle.replace('_', ' '), max_num=extraImagesNeeded, min_size=(500, 500))

    def makeVideo(self, audioFile, imageData):
        
        ttsAudio = AudioFileClip(audioFile)
        videoDuration = ttsAudio.duration

        scenes = []
        scenes.append(ImageClip(self.mainImages+self.conjoiner+'MAIN_IMAGE.jpg', duration=5))
        remove(self.mainImages+self.conjoiner+'MAIN_IMAGE.jpg')

        imageNames = []
        for name in range(len(imageData)):
            imageNames.append(imageData[name][1])

        mainImages = listdir(self.mainImages)
        extraImages = listdir(self.extraImages)
        counter = 0

        while(len(mainImages)*7 < videoDuration):
            mainImages.append(extraImages[counter])
            move(self.extraImages+self.conjoiner+extraImages[counter], self.mainImages+self.conjoiner+extraImages[counter])
            counter+=1
        
        mainImages = listdir(self.mainImages)
        for sceneCounter in mainImages:
            try:
                videoClip = ImageClip(self.mainImages+self.conjoiner+sceneCounter, duration=7)
            except ValueError as e:
                print(e)
                try:
                    imageData.pop(imageNames.index(sceneCounter))
                except ValueError:
                    pass
                remove(self.mainImages+self.conjoiner+sceneCounter)
            scenes.append(videoClip)
        
        scenes.reverse()
        finalVideo = concatenate_videoclips(scenes, method='compose')
        finalVideo = finalVideo.subclip(0, ceil(videoDuration)+1)
        finalVideo = finalVideo.set_audio(ttsAudio)
        finalVideo.write_videofile(self.finalVideo+self.conjoiner+'finalVideo.mp4', fps=24)
        
    def uploadVideo(self, file, title, description):

        uploadTemplate = open(self.uploadVideoTextfile, 'r').read()
        uploadTemplate = uploadTemplate.replace('""', '"'+str(file)+'"', 1)
        uploadTemplate = uploadTemplate.replace('""', '"'+str(title)+'"', 1)
        uploadTemplate = uploadTemplate.replace('""', '"'+str(description)+'"', 1)

        open(self.uploadVideoSH, 'x').write(uploadTemplate)
        Popen('sh '+str(self.directory+self.conjoiner)+'upload_video.sh')
        remove(self.uploadVideoSH)

object = Wikipediator()
pages = object.getTopWikipedia(1)
audioFile, audioID = object.textToSpeech(pages[0][1])
imageData = object.extractImages(pages[0][0])
object.getExtraImages(pages[0][0], pages[0][1])
videoLocation = object.makeVideo(audioFile, imageData)
# object.uploadVideo(videoLocation, pages[0][0], open(object.directory+object.conjoiner+'description.txt'))