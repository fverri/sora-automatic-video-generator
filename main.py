from datetime import datetime, timedelta, timezone
from openai import OpenAI
from dotenv import dotenv_values
import time
from video_uploader import authenticate_youtube, upload_video, get_video_stats
import os
import json
from typing import Literal, cast

values = dotenv_values(".env")
client = OpenAI(api_key=values.get("OPENAI_API_KEY"))

CACHE_SIZE = 10
GENERATE_AT = (5, 0)
UPLOAD_TIMES = ((17, 0), (21, 0))


def call_llm(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-5.2",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    return json.loads(cast(str, content))


def read_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_cache(path):
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return data


def save_cache(path, items):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=True, indent=2)


def generate_video(
    video_number,
    prompt,
    duration: Literal["4", "8", "12"],
):
    video = client.videos.create(
        model="sora-2-pro",
        prompt=prompt,
        size="720x1280",
        seconds=duration,
    )

    last_video_progress = None

    while True:
        video = client.videos.retrieve(video.id)

        if last_video_progress != video.progress:
            print(f"Video progress: {video.progress}%")
            print("Waiting...")
            last_video_progress = video.progress

        if video.status == "completed":
            break
        if video.status == "failed":
            raise RuntimeError(video.error)

    response = client.videos.download_content(video_id=video.id)
    mp4_bytes = response.read()

    with open(f"videos/output_video_{video_number}.mp4", "wb") as f:
        f.write(mp4_bytes)


def upload_video_to_youtube(youtube, title, description, video_number):
    start_time = time.time()

    video_id = None
    file_path = f"videos/output_video_{video_number}.mp4"
    try:
        video_id = upload_video(
            youtube,
            file_path,
            title=title,
            description=description,
            category_id="22",
        )
        print(
            f"Uploaded video at https://www.youtube.com/shorts/{video_id} in {time.time() - start_time:.2f} seconds"
        )
        os.remove(file_path)
    except Exception as e:
        print(f"Error uploading video: {e}")
        print(f"Video file retained at {file_path}")

    return video_id


def convert_time_tuple_to_datetime(time_tuple):
    hour, minute = time_tuple
    now = datetime.now(timezone.utc)
    scheduled_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if scheduled_datetime <= now:
        scheduled_datetime += timedelta(days=1)
    return scheduled_datetime


def wait_until_datetime(target_datetime):
    while True:
        now = datetime.now(timezone.utc)
        remaining_seconds = (target_datetime - now).total_seconds()
        if remaining_seconds <= 0:
            break
        time.sleep(min(remaining_seconds, 10))


def build_upload_schedule_from_time_tuples(time_tuples):
    schedule = [convert_time_tuple_to_datetime(t) for t in time_tuples]
    schedule.sort()
    return schedule


system_prompt = read_prompt("prompts/system_prompt.txt")
user_prompt_base = read_prompt("prompts/user_prompt.txt")

generation_datetime = convert_time_tuple_to_datetime(GENERATE_AT)
upload_schedule = build_upload_schedule_from_time_tuples(UPLOAD_TIMES)
number_of_videos = len(upload_schedule)

print(
    f"Scheduled generation time (UTC): {generation_datetime.hour:02d}:{generation_datetime.minute:02d}"
)
print("Scheduled upload times (UTC):")
for dt in upload_schedule:
    print(f"{dt.hour:02d}:{dt.minute:02d}")
print(f"Number of videos: {number_of_videos}")

try:
    while True:
        print(
            f"Waiting for generation time (UTC): {generation_datetime.hour:02d}:{generation_datetime.minute:02d}"
        )
        wait_until_datetime(generation_datetime)

        youtube = authenticate_youtube()
        cache_items = load_cache("cache.json")
        for item in cache_items:
            item.pop("stats", None)

        pending_videos = []

        for video_index in range(number_of_videos):
            cache_with_stats = []
            for item in cache_items:
                enriched = dict(item)
                video_id = item.get("youtube_id")
                if video_id:
                    enriched["stats"] = get_video_stats(youtube, video_id)
                cache_with_stats.append(enriched)
            for pending in pending_videos:
                cache_with_stats.append(
                    {
                        "video_prompt": pending["video_prompt"],
                        "title": pending["title"],
                        "description": pending["description"],
                        "duration": pending["duration"],
                        "youtube_id": None,
                    }
                )

            cache_payload = json.dumps(cache_with_stats, ensure_ascii=True)
            user_prompt = f"{user_prompt_base}\n\nCACHE_JSON:\n{cache_payload}"

            payload = call_llm(system_prompt, user_prompt)
            video_prompt = payload["video_prompt"]
            title = payload["title"]
            description = payload["description"]
            duration = cast(Literal["4", "8", "12"], payload["duration"])

            video_number = video_index

            print(f"Generating video {video_number + 1}/{number_of_videos}")

            generate_video(video_number, video_prompt, duration)

            pending_videos.append(
                {
                    "video_prompt": video_prompt,
                    "title": title,
                    "description": description,
                    "duration": duration,
                    "video_number": video_number,
                }
            )

        for video_index, scheduled_datetime in enumerate(upload_schedule):
            print(
                f"Waiting for upload time (UTC): {scheduled_datetime.hour:02d}:{scheduled_datetime.minute:02d}"
            )
            wait_until_datetime(scheduled_datetime)

            youtube = authenticate_youtube()
            pending = pending_videos[video_index]
            print(f"Uploading video {video_index + 1}/{number_of_videos}")
            video_id = upload_video_to_youtube(
                youtube,
                pending["title"],
                pending["description"],
                pending["video_number"],
            )

            cache_items.append(
                {
                    "video_prompt": pending["video_prompt"],
                    "title": pending["title"],
                    "description": pending["description"],
                    "duration": pending["duration"],
                    "youtube_id": video_id,
                }
            )
            cache_items = cache_items[-CACHE_SIZE:]
            save_cache("cache.json", cache_items)

        generation_datetime += timedelta(days=1)
        upload_schedule = [dt + timedelta(days=1) for dt in upload_schedule]
except KeyboardInterrupt:
    print("Process interrupted by user")