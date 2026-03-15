import os
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def authenticate_youtube():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, file_path, title, description, category_id="22"):
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": category_id,
            },
            "status": {"privacyStatus": "public"},
        },
        media_body=MediaFileUpload(file_path),
    )
    response = request.execute()
    return response["id"]


def get_video_stats(youtube, video_id):
    if not video_id:
        return {}

    request = youtube.videos().list(part="statistics,snippet", id=video_id)
    try:
        response = request.execute()
    except HttpError as exc:
        print(f"Error fetching video stats: {exc}")
        return {}

    items = response.get("items", [])
    if not items:
        return {}

    stats = items[0].get("statistics", {})
    snippet = items[0].get("snippet", {})
    published_at = snippet.get("publishedAt")
    seconds_since_published = None
    if published_at:
        try:
            published_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            if published_dt.tzinfo is None:
                published_dt = published_dt.replace(tzinfo=timezone.utc)
            seconds_since_published = int(
                (datetime.now(timezone.utc) - published_dt).total_seconds()
            )
        except ValueError:
            seconds_since_published = None
    return {
        "viewCount": stats.get("viewCount"),
        "likeCount": stats.get("likeCount"),
        "commentCount": stats.get("commentCount"),
        "seconds_since_published": seconds_since_published,
    }