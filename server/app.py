from flask import Flask, request, jsonify
from flask_cors import CORS
from hikerapi import Client
import os
from dotenv import load_dotenv
import traceback
from cachetools import TTLCache, cached
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time

load_dotenv()

app = Flask(__name__)
CORS(app)

# 리미터 설정
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2 per hour"],
    storage_uri="memory://"
)

HIKERAPI_KEY = os.environ.get('HIKERAPI_KEY')
cl = Client(token=HIKERAPI_KEY)

# 캐시 설정 (최대 100개 항목, 30분 유효)
cache = TTLCache(maxsize=100, ttl=1800)

# IP별 마지막 요청 시간을 저장할 딕셔너리
last_request_time = {}

@cached(cache)
def fetch_hashtag_info(query):
    hashtag_info = cl.hashtag_by_name_v1(query)
    related_hashtags = cl.search_hashtags_v1(query)
    
    media_count = hashtag_info.get('media_count', 0)
    
    if isinstance(related_hashtags, list):
        related_hashtags_list = [tag.get('name') for tag in related_hashtags if isinstance(tag, dict)]
    elif isinstance(related_hashtags, dict):
        related_hashtags_list = [tag.get('name') for tag in related_hashtags.get('hashtags', []) if isinstance(tag, dict)]
    else:
        related_hashtags_list = []
    
    app.logger.info(f"Fetched Hashtag Info: {hashtag_info}")
    app.logger.info(f"Related Hashtags: {related_hashtags_list}")
    app.logger.info(f"Media Count: {media_count}")
    
    return {
        "media_count": media_count,
        "related_hashtags": related_hashtags_list
    }

@app.route('/api/search', methods=['GET'])
@limiter.limit("2 per hour")  # 항상 리미터 적용
def search_hashtag():
    ip = get_remote_address()
    current_time = time.time()
    
    # 3초 딜레이 체크
    if ip in last_request_time and current_time - last_request_time[ip] < 3:
        return jsonify({"error": "Please wait 3 seconds between requests"}), 429
    
    last_request_time[ip] = current_time
    
    query = request.args.get('query', '')
    debug_mode = request.args.get('debugMode', 'false').lower() == 'true'
    
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    
    try:
        if debug_mode:
            # 디버그 모드일 때 3초 지연 추가
            time.sleep(3)
            # 디버그 모드일 때는 하드코딩된 값 반환
            result = {
                "media_count": 12345,
                "related_hashtags": [f"example{i+1}" for i in range(20)]
            }
        else:
            # 실제 모드에서만 API 키 확인 및 API 호출
            if not HIKERAPI_KEY:
                raise ValueError("HIKERAPI_KEY is not set in environment variables")
            result = fetch_hashtag_info(query)
        
        app.logger.info(f"Search Result for '{query}': {result}")
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f"An error occurred: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

def handler(event, context):
    return app(event, context)

if __name__ == '__main__':
    app.run(debug=True)