# -*- coding: utf-8 -*-
import os
import re
import requests
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_from_directory
from pytrends.request import TrendReq
from datetime import datetime, timedelta, timezone

app = Flask(__name__, static_folder='public', template_folder='public')

# 🚨🚨🚨 중요: 이 부분을 반드시 본인의 유효한 유튜브 API 키로 교체해야 합니다! 🚨🚨🚨
API_KEY = 'AIzaSyAvQGtMOXN2RYKDw4MD98jBxDAZTNTyLFs'

# ISO 8601 형식의 영상 길이(예: PT1M30S)를 초 단위로 변환하는 함수
def parse_duration(duration):
    if not duration: return 0
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match: return 0
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    return hours * 3600 + minutes * 60 + seconds

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('public', path)

@app.route('/api/trending-keywords')
def trending_keywords():
    geo_code = request.args.get('geo', 'US')
    country_map = {'KR': 'KR', 'US': 'US', 'JP': 'JP'}
    country_code = country_map.get(geo_code, 'US')

    try:
        pytrends = TrendReq(hl='ko-KR', tz=540)
        trending_df = pytrends.today_searches(pn=country_code)
        keywords = trending_df.head(30).values.flatten().tolist()
        return jsonify(keywords)
    except Exception as e:
        print(f"🚨 Pytrends Error: {e}")
        return jsonify({"error": "트렌드 데이터를 가져오는 데 실패했습니다."}), 500

@app.route('/api/search')
def search():
    keyword = request.args.get('keyword')
    period = request.args.get('period')
    if not keyword or not period: return jsonify({"error": "검색어와 기간이 필요합니다."}), 400

    try:
        search_end_date = datetime.now(timezone.utc)
        search_start_date = search_end_date - timedelta(days=int(period))
        published_after = search_start_date.isoformat().replace('+00:00', 'Z')

        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {'part': 'snippet', 'q': keyword, 'maxResults': 50, 'order': 'viewCount', 'type': 'video', 'regionCode': 'KR', 'publishedAfter': published_after, 'key': API_KEY}
        search_res = requests.get(search_url, params=search_params)
        search_res.raise_for_status()
        search_response = search_res.json()

        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        if not video_ids: return jsonify([])

        video_url = "https://www.googleapis.com/youtube/v3/videos"
        video_params = {'part': 'snippet,statistics,contentDetails', 'id': ','.join(video_ids), 'key': API_KEY}
        video_res = requests.get(video_url, params=video_params)
        video_items = video_res.json().get('items', [])

        channel_ids = list(set([item['snippet']['channelId'] for item in video_items]))
        channel_url = "https://www.googleapis.com/youtube/v3/channels"
        channel_params = {'part': 'snippet,statistics', 'id': ','.join(channel_ids), 'key': API_KEY}
        channel_res = requests.get(channel_url, params=channel_params)
        channel_response = channel_res.json()

        channel_data_map = {
            item['id']: {
                'subscriberCount': '비공개' if item['statistics'].get('hiddenSubscriberCount') else item['statistics'].get('subscriberCount', '0'),
                'publishedAt': item['snippet']['publishedAt'].split('T')[0]
            } for item in channel_response.get('items', [])
        }

        final_data = []
        for item in video_items:
            channel_info = channel_data_map.get(item['snippet']['channelId'], {})
            duration_in_seconds = parse_duration(item['contentDetails']['duration'])
            final_data.append({
                'id': item['id'],
                'title': item['snippet']['title'],
                'channelTitle': item['snippet']['channelTitle'],
                'thumbnail': item['snippet']['thumbnails']['default']['url'],
                'viewCount': item.get('statistics', {}).get('viewCount', '0'),
                'subscriberCount': channel_info.get('subscriberCount', '정보 없음'),
                'channelPublishedAt': channel_info.get('publishedAt', '정보 없음'),
                'isShort': 0 < duration_in_seconds <= 60
            })

        final_data.sort(key=lambda x: int(x['viewCount']), reverse=True)
        return jsonify(final_data)

    except Exception as e:
        print(f"🚨 YouTube API Error: {e}")
        return jsonify({"error": "API 요청 중 오류가 발생했습니다."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)