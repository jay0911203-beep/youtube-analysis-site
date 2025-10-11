# -*- coding: utf-8 -*-
import os
import re
import requests
import pandas as pd
from flask import Flask, request, jsonify, render_template
from pytrends.request import TrendReq
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

# Vercel 환경 변수를 우선적으로 사용하고, 없을 경우 코드에 있는 키를 사용합니다.
API_KEY = os.environ.get('API_KEY', 'AIzaSyAvQGtMOXN2RYKDw4MD98jBxDAZTNTyLFs')

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

@app.route('/api/trending-keywords')
def trending_keywords():
    geo_code = request.args.get('geo', 'US')
    category = request.args.get('category', 'all')  # 카테고리 추가
    
    # YouTube 카테고리 ID 매핑
    category_map = {
        'all': None,  # 전체
        'news': '25',  # 뉴스/정치
        'education': '27',  # 교육
        'howto': '26',  # 실용/DIY
        'people': '22',  # 인물/블로그
        'travel': '19',  # 여행
        'health': None,  # 건강 (검색어 기반)
        'music': '10',  # 음악 (트로트/가요)
        'religion': None,  # 종교 (검색어 기반)
        'cooking': None,  # 요리 (검색어 기반)
        'hobby': None,  # 취미/원예 (검색어 기반)
    }
    
    category_id = category_map.get(category, None)
    print(f"🔍 Fetching trends for: {geo_code}, category: {category}")
    
    # 검색어 기반 카테고리들
    search_based_categories = ['health', 'religion', 'cooking', 'hobby']
    if category in search_based_categories:
        return get_search_based_videos(geo_code, category)
    
    # YouTube API로 인기 동영상 정보 가져오기
    try:
        video_url = "https://www.googleapis.com/youtube/v3/videos"
        video_params = {
            'part': 'snippet,statistics',
            'chart': 'mostPopular',
            'regionCode': geo_code,
            'maxResults': 30,
            'key': API_KEY
        }
        
        # 카테고리가 지정된 경우 추가
        if category_id:
            video_params['videoCategoryId'] = category_id
        
        print(f"🔍 Trying YouTube API for {geo_code} with category {category}...")
        video_res = requests.get(video_url, params=video_params, timeout=10)
        
        if video_res.status_code == 200:
            video_items = video_res.json().get('items', [])
            if video_items:
                trending_videos = []
                for item in video_items:
                    trending_videos.append({
                        'id': item['id'],
                        'title': item['snippet']['title'],
                        'channelTitle': item['snippet']['channelTitle'],
                        'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                        'viewCount': item.get('statistics', {}).get('viewCount', '0')
                    })
                print(f"✅ YouTube API success for {geo_code}: {len(trending_videos)} items")
                return jsonify(trending_videos)
        else:
            print(f"❌ YouTube API failed: {video_res.status_code}")
    except Exception as yt_error:
        print(f"🚨 YouTube Trending Error for {geo_code}: {yt_error}")
    
    # 모든 방법 실패 시
    print(f"❌ All methods failed for {geo_code}")
    return jsonify({"error": f"{geo_code} 국가의 트렌드 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요."}), 500

def get_search_based_videos(geo_code, category):
    """검색어 기반 카테고리 동영상 가져오기"""
    try:
        # 60대 이상이 관심있는 키워드들
        keywords_map = {
            'health': {
                'KR': '건강 60대 시니어',
                'US': 'health tips seniors 60+',
                'JP': '健康 60代 シニア'
            },
            'religion': {
                'KR': '명상 힐링 설교',
                'US': 'meditation spiritual',
                'JP': '瞑想 癒し'
            },
            'cooking': {
                'KR': '요리 반찬 만들기',
                'US': 'cooking recipes traditional',
                'JP': '料理 レシピ 伝統'
            },
            'hobby': {
                'KR': '텃밭 원예 취미',
                'US': 'gardening hobby seniors',
                'JP': '園芸 趣味 シニア'
            }
        }
        
        keyword = keywords_map.get(category, {}).get(geo_code, 'seniors lifestyle')
        
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            'part': 'snippet',
            'q': keyword,
            'type': 'video',
            'order': 'viewCount',
            'regionCode': geo_code,
            'maxResults': 30,
            'key': API_KEY
        }
        
        search_res = requests.get(search_url, params=search_params, timeout=10)
        if search_res.status_code != 200:
            return jsonify({"error": "검색 실패"}), 500
        
        video_ids = [item['id']['videoId'] for item in search_res.json().get('items', [])]
        if not video_ids:
            return jsonify([])
        
        # 동영상 상세 정보 가져오기
        video_url = "https://www.googleapis.com/youtube/v3/videos"
        video_params = {
            'part': 'snippet,statistics',
            'id': ','.join(video_ids),
            'key': API_KEY
        }
        
        video_res = requests.get(video_url, params=video_params, timeout=10)
        video_items = video_res.json().get('items', [])
        
        trending_videos = []
        for item in video_items:
            trending_videos.append({
                'id': item['id'],
                'title': item['snippet']['title'],
                'channelTitle': item['snippet']['channelTitle'],
                'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                'viewCount': item.get('statistics', {}).get('viewCount', '0')
            })
        
        return jsonify(trending_videos)
    except Exception as e:
        print(f"🚨 Search-based videos error: {e}")
        return jsonify({"error": "동영상을 가져올 수 없습니다."}), 500

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
    app.run(debug=True)
