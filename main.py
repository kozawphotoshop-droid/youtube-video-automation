import os
import json
import requests
from yt_dlp import YoutubeDL
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# Load Configuration
with open("config.json", "r") as f:
    config = json.load(f)

if not config.get("workflow_enabled", False):
    print("Workflow is disabled in config.json. Exiting.")
    exit(0)

# Read URLs
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

# 1. Download Audio using yt-dlp
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

# 2. Fetch Images (Using Pexels or Pixabay API / Or placeholder logic)
# Note: Pexels API key ကို GitHub Secrets ထဲမှာ ထည့်ထားရပါမယ်။
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
query = config.get("search_query", "buddha meditation")
image_duration = config.get("image_duration", 5)
num_images_needed = int(audio_duration / image_duration) + 1

images = []
if PEXELS_API_KEY:
    headers = {"Authorization": PEXELS_API_KEY}
    response = requests.get(
        f"https://api.pexels.com/v1/search?query={query}&per_page={min(num_images_needed, 15)}",
        headers=headers
    )
    if response.status_code == 200:
        data = response.json()
        photos = data.get("photos", [])
        for idx, photo in enumerate(photos):
            img_url = photo["src"]["large"]
            img_data = requests.get(img_url).content
            img_file = f"temp_img_{idx}.jpg"
            with open(img_file, "wb") as handler:
                handler.write(img_data)
            images.append(img_file)

if not images:
    print("Error: Could not fetch images or API key missing.")
    audio_clip.close()
    exit(1)

# 3. Render Video using MoviePy
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

# 4. Mark URL as DONE in urls.txt
lines[target_index] = f"# [DONE] {target_url}\n"
with open("urls.txt", "w") as f:
    f.writelines(lines)

print("Video rendering complete successfully!")
