from flask import Flask, request, jsonify
import os
import cv2
import numpy as np
import pyautogui
import pyaudio
import wave
import time
import subprocess
import ffmpeg
import threading
import requests
import multiprocessing
from multiprocessing import Process, Event

app = Flask(__name__)

# Global variables for controlling recording
recording = False
release = False
audio_thread = None
video_thread = None
audio_process = None
video_process = None
audio_stop_event = None
video_stop_event = None

#Creating of directory for saving the video
def create_directory_if_not_exists(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Directory '{directory_path}' created.")
    else:
        print(f"Directory '{directory_path}' already exists.")

#recording the audio seperately
def record_audio(filename, rate, channels, stop_event):
    CHUNK = 1024
    audio_format = pyaudio.paInt16
    
    p = pyaudio.PyAudio()

    stream = p.open(format=audio_format,
                    channels=channels,
                    rate=rate,
                    input=True,
                    frames_per_buffer=CHUNK)

    frames = []

    while not stop_event.is_set():  # Continuously record audio
        data = stream.read(CHUNK)
        frames.append(data)

    stream.stop_stream()
    stream.close()

    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(audio_format))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()
  
#recording the video seperately ie... capturing the screenshots of the system and merging them together to form the video
def record_video(filenameV,stop_event):
    SCREEN_SIZE = pyautogui.size()
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    fps = 13.3
    out = cv2.VideoWriter(filenameV, fourcc, fps, SCREEN_SIZE)

    while not stop_event.is_set():
        img = pyautogui.screenshot()
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        out.write(frame)
    
    out.release()

#We can merge the audio and video of images
def run_ffmpeg_command(command):
    try:
        subprocess.run(
            command,
            shell=True,
            check=True,
            stderr=subprocess.PIPE,
            text=True
            # executable="ffmpeg"
        )
    except subprocess.CalledProcessError as e:
        print("Error executing ffmpeg command:")
        print(e.stderr)
        raise e
      
#initilize the app
@app.route('/record', methods=['POST'])
def handle_record_request():
    global recording
    global audio_process
    global video_process
    global audio_stop_event
    global video_stop_event

    data = request.json

    if data['ACTION'] == 'START':
        recording = True

        audio_stop_event = multiprocessing.Event()
        video_stop_event = multiprocessing.Event()

        audio_process = multiprocessing.Process(target=record_audio, args=(data['AUDIO_NAME'] + ".wav", 44100, 2, audio_stop_event))
        video_process = multiprocessing.Process(target=record_video, args=(data['VIDEO_NAME'] + ".avi", video_stop_event))

        audio_process.start()
        video_process.start()

        message = "Recording started"
    elif data['ACTION'] == 'STOP':
        # global recording
        recording = False
        audio_stop_event.set()
        video_stop_event.set()
        audio_process.join()
        video_process.join()
        message = "Recording stopped"
    elif data['ACTION'] == 'RELEASE':
        global release
        release = True
        recording = False
        audio_stop_event.set()
        video_stop_event.set()
        audio_process.join()
        video_process.join()
        postaudio = data['AUDIO_NAME'] + ".wav"
        postvideo = data['VIDEO_NAME'] + ".avi"
        directory_path = data['VIDEO_PATH']
      
        output_video = data['VIDEO_PATH']+data['OUTPUT_VIDEO_NAME'] + ".avi"
        create_directory_if_not_exists(directory_path)
        
        command = [
        'ffmpeg',
        '-i', postvideo,
        '-i', postaudio,
        '-c:v', 'copy',
        '-c:a', 'aac',
        output_video
        ]
        print(command)
        run_ffmpeg_command(command)

        os.remove(data['VIDEO_NAME'] + ".avi")
        os.remove(data['AUDIO_NAME'] + ".wav")
        release = False
      
        print (server_response)
        message = "Video released"
    else:
        message = "Invalid action"

    return jsonify({'message': message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)


