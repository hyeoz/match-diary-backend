#!/usr/bin/env python
# coding: utf-8

# KBO 일정 크롤링 - KBO 홈페이지
## 1.1 2024 UPDATE - 기존에 사용하던 requests 방식 사용

### 1. 패키지 세팅 
from bs4 import BeautifulSoup as bs
import json
from dotenv import load_dotenv
import os
import requests

load_dotenv()
api_key = os.getenv("API_KEY")
webhook_url = os.getenv("WEBHOOK_URL")
# heroku 서버 키
headers={
    'Authorization': ' '.join(['Bearer', api_key]),
    "Content-Type": "application/json",
}

# 스케쥴러 작동 시 데이터 모두 날리고 다시 넣어야 함
def clear_schema():
    print("CLEAR SCHEMA START")
    response = requests.get("https://match-diary-backend-79e304d3a79e.herokuapp.com/api/schedule-2024s", headers=headers)
    if response.status_code == 200:
        items = response.json()
    else:
        requests.post(webhook_url, headers={"Content-type": "application/json"}, data=json.dumps({
            "text": "GET 요청이 실패했어요!"
        }))
        items = {'data': []}

    for item in items['data']:
        id = item['id']
        delete_url = f"https://match-diary-backend-79e304d3a79e.herokuapp.com/api/schedule-2024s/{id}"
        delete_response = requests.delete(delete_url, headers=headers)

        if delete_response.status_code != 200:
            requests.post(webhook_url, headers={"Content-type": "application/json"}, data=json.dump({
                "text": "데이터 삭제 중 문제 발생! 주인님 여기에요!"
            }))
            return;
        
        requests.post(webhook_url, headers={"Content-type": "application/json"}, data=json.dump({
            "text": "데이터 삭제 완료! 크롤링 시작!"
        }))

# KOB 홈페이지 기준, 현재 ~0829 일정까지 공개
def run_crawler(): 
    print("RUN CRAWLER START")

    for month in ['03', '04', '05', '06', '07', '08']:
        data = {
            "leId": '1',
            "srIdList": '0,9,6',
            "seasonId": '2024',
            "gameMonth": month,
            "teamId": ""
        }
        r = requests.post("https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList", data=data)
        root = json.loads(r.content.decode("utf-8"))
        
        # 크롤링한 데이터 전처리
        # 0~1 -> 날짜
        # 2 -> 경기 정보 (홈팀 / 홈팀점수 / 원정팀 점수 / 원정팀)
        # 7 -> 경기장
        # 8 -> 비고 (특수경기)
        formedData = [];

        for row in root['rows']:
            data = {}
            if row['row'][0]['Class'] == 'day':
        # 날짜
                data['date'] = row['row'][0]['Text']
                data['time'] = bs(row['row'][1]['Text']).get_text()

        # 경기정보
                info = bs(row['row'][2]['Text']).find_all('span')
                if (len(info) > 3):  
                    data['away'] = info[0].get_text()
                    data['awayScore'] = int(info[1].get_text())
                    data['homeScore'] = int(info[3].get_text())
                    data['home'] = info[4].get_text()
                else:
                    data['away'] = info[0].get_text()
                    data['awayScore'] = -1
                    data['homeScore'] = -1
                    data['home'] = info[2].get_text()

        # 경기장 정보
                data['stadium'] = row['row'][7]['Text']

        # 비고
                data['memo'] = row['row'][8]['Text']
                formedData.append(data)
            else:
        # 날짜
                data['date'] = formedData[-1]['date']
                data['time'] = bs(row['row'][0]['Text']).get_text()

        # 경기정보
                info = bs(row['row'][1]['Text']).find_all('span')
                if (len(info) > 3):  
                    data['away'] = info[0].get_text()
                    data['awayScore'] = int(info[1].get_text())
                    data['homeScore'] = int(info[3].get_text())
                    data['home'] = info[4].get_text()
                else:
                    data['away'] = info[0].get_text()
                    data['awayScore'] = -1
                    data['homeScore'] = -1
                    data['home'] = info[2].get_text()

        # 경기장 정보
                data['stadium'] = row['row'][6]['Text']

        # 비고
                data['memo'] = row['row'][7]['Text']
                formedData.append(data)        

        for match in formedData:
            res = requests.post("https://match-diary-backend-79e304d3a79e.herokuapp.com/api/schedule-2024s", 
                headers=headers,
                data=json.dumps(
                    {
                        "data": match
                    }
                ),
            )
    # 크롤링 완료 시 슬랙 메세지 보내기
    webhook_data = {
        "text": "으쌰으쌰 KBO 경기 일정 크롤링 완료!"
    }
    requests.post(webhook_url, headers={"Content-type": "application/json"}, data=json.dumps(webhook_data))



if __name__ == "__main__":
    clear_schema()
    run_crawler()