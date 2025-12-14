import os
import random
import datetime
import time
import requests
from gtts import gTTS
from google.auth.transport.requests import Request
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def safe_download(url, filename, max_retries=3):
    for attempt in range(max_retries):
        try:
            print(f"⬇️ Attempt {attempt + 1}: Downloading {filename}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"✅ Success: {filename}")
            return True
        except Exception as e:
            print(f"❌ Failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5)
    return False

def safe_tts(text, filename, max_retries=3):
    for attempt in range(max_retries):
        try:
            print(f"🗣️ Attempt {attempt + 1}: Generating voice...")
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(filename)
            print("✅ Voice generated")
            return True
        except Exception as e:
            print(f"❌ TTS failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5)
    return False

def safe_ffmpeg(cmd, description, max_retries=2):
    for attempt in range(max_retries):
        try:
            print(f"🎥 Attempt {attempt + 1}: {description}...")
            result = os.system(cmd)
            if result == 0:
                print(f"✅ {description} succeeded")
                return True
            else:
                print(f"❌ {description} failed (exit code {result})")
        except Exception as e:
            print(f"❌ {description} error: {str(e)}")
        if attempt < max_retries - 1:
            time.sleep(5)
    return False

# ===== GENERATE STORY =====
TITLES = ["The Last Shift at the Gas Station", "They Found Her Phone... Still Recording"]
STORIES = [
    "In the winter of 2021, a night clerk at a remote gas station in Oregon checked in a customer with no reflection in the security monitor. What happened next was captured on tape—and it still haunts investigators to this day.",
    "A college student left her apartment for just ten minutes. When she returned, her door was wide open... and her smart speaker was playing a voice that wasn't hers."
]
title = random.choice(TITLES)
story = random.choice(STORIES)
full_text = f"Published on {datetime.datetime.now().strftime('%B %d, %Y')}. {story}"

# ===== DOWNLOAD FOOTAGE (with retry) =====
FOOTAGE_URL = "https://download.pexels.com/videos/19171430-uhd_3840_2160_25fps.mp4?ph=d76b7a6a4a"
if not safe_download(FOOTAGE_URL, "bg.mp4"):
    print("💀 Critical failure: Could not download footage. Exiting.")
    exit(1)

# ===== GENERATE VOICE (with retry) =====
if not safe_tts(full_text, "voice.mp3"):
    print("💀 Critical failure: Could not generate voice. Exiting.")
    exit(1)

# ===== ADD AMBIENCE =====
if not safe_ffmpeg(
    'ffmpeg -f lavfi -i anullsrc=r=24000:cl=mono -t 1 silence.mp3 -y',
    "Create silence file"
):
    exit(1)

if not safe_ffmpeg(
    'ffmpeg -i voice.mp3 -i silence.mp3 -filter_complex "[0:a]aecho=0.8:0.9:1000ms:0.3[a]" final.mp3 -y',
    "Add reverb"
):
    exit(1)

# ===== RENDER VIDEO =====
if not safe_ffmpeg(
    'ffmpeg -stream_loop -1 -i bg.mp4 -i final.mp3 -shortest -c:v libx264 -preset ultrafast -c:a aac output.mp4 -y',
    "Render final video"
):
    exit(1)

# ===== UPLOAD TO YOUTUBE =====
try:
    with open("token.pickle", "rb") as f:
        creds = pickle.load(f)
    if creds.expired:
        creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": "Welcome to The 3AM Files — original horror stories, documented nightly.\n\n#horror #truehorror #3am",
            "tags": ["horror stories", "true horror", "The 3AM Files"],
            "categoryId": "27"
        },
        "status": {"privacyStatus": "public"}
    }

    media = MediaFileUpload("output.mp4", resumable=True)
    request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
    print(f"✅ LIVE: https://youtube.com/watch?v={response['id']}")

except Exception as e:
    print(f"💀 YouTube upload failed: {str(e)}")
    exit(1)
