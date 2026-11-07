import os
import json
import requests
from yt_dlp import YoutubeDL
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# 1. Load Configuration
with open("config.json", "r") as f:
    config = json.load(f)

if not config.get("workflow_enabled", False):
    print("Workflow is disabled in config.json. Exiting.")
    exit(0)

# 2. Read URLs from urls.txt
with open("urls.txt", "r") as f:
    lines = f.readlines()

target_url = None
target_index = -1

for i, line in enumerate(lines):
    line = line.strip()
    if line and not line.startswith("#"):
        target_url = line
        target_index = i
        break

if not target_url:
    print("No pending URLs found in urls.txt.")
    exit(0)

print(f"Processing URL: {target_url}")

# 3. Download Audio using yt-dlp
audio_opts = {
    'format': 'bestaudio/best',
    'outtmpl': 'temp_audio.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

with YoutubeDL(audio_opts) as ydl:
    ydl.download([target_url])

audio_path = "temp_audio.mp3"
audio_clip = AudioFileClip(audio_path)
audio_duration = audio_clip.duration
print(f"Audio downloaded. Duration: {audio_duration} seconds")

# 4. Fetch Images from Wikimedia Commons API (No API Key / No VPN needed)
query = config.get("search_query", "Buddha meditation")
image_duration = config.get("image_duration", 5)
num_images_needed = int(audio_duration / image_duration) + 1

wiki_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={query}&gsrnamespace=6&gsrlimit={min(num_images_needed, 15)}&prop=imageinfo&iiprop=url&format=json"

headers = {'User-Agent': 'AutoVideoRenderBot/1.0 (Contact: user@example.com)'}
response = requests.get(wiki_url, headers=headers)

images = []
if response.status_code == 200:
    data = response.json()
    pages = data.get("query", {}).get("pages", {})
    for page_id, page_info in pages.items():
        if "imageinfo" in page_info:
            img_url = page_info["imageinfo"][0]["url"]
            # ဒေါင်းလုပ်ဆွဲခြင်း
            img_data = requests.get(img_url, headers=headers).content
            img_file = f"temp_img_{len(images)}.jpg"
            with open(img_file, "wb") as handler:
                handler.write(img_data)
            images.append(img_file)

if not images:
    print("Error: Could not fetch images from Wikimedia Commons.")
    audio_clip.close()
    exit(1)

print(f"Successfully fetched {len(images)} images.")

# 5. Render Video using MoviePy
clips = []
for i in range(int(audio_duration)):
    img_path = images[(i // image_duration) % len(images)]
    clip = ImageClip(img_path).set_duration(1)
    clips.append(clip)

video = concatenate_videoclips(clips, method="compose")
video = video.set_audio(audio_clip)

output_video = "output_video.mp4"
video.write_videofile(output_video, fps=24, codec="libx264", audio_codec="aac")

# Cleanup clips
audio_clip.close()
video.close()

# 6. Mark URL as DONE in urls.txt
lines[target_index] = f"# [DONE] {target_url}\n"
with open("urls.txt", "w") as f:
    f.writelines(lines)

print("Video rendering completed successfully!")
