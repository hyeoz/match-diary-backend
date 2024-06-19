#!/usr/bin/env python
# coding: utf-8

# KBO 일정 크롤링 - KBO 홈페이지
## 1.1 2024 UPDATE - 기존에 사용하던 requests 방식 사용

### 1. 패키지 세팅 
from bs4 import BeautifulSoup as bs
import json
from dotenv import load_dotenv
import os
import httpx
import asyncio
from datetime import date

load_dotenv()
api_key = os.getenv("API_KEY")
webhook_url = os.getenv("WEBHOOK_URL")

# heroku 서버 키
headers = {
    'Authorization': ' '.join(['Bearer', api_key]),
    "Content-Type": "application/json",
}
year = date.today().year;
print(year)
# 스케쥴러 작동 시 데이터 모두 날리고 다시 넣어야 함
async def clear_schema():
    print("CLEAR SCHEMA START")
    async with httpx.AsyncClient() as client:
        page = 1
        page_size = 50
        
        all_data = []
        
        while True:
            url = f"https://match-diary-backend-79e304d3a79e.herokuapp.com/api/schedule-{year}s?pagination[page]={page}&pagination[pageSize]={page_size}"
            response = await client.get(url, headers=headers)
            data = response.json()

            if not data['data']:
                break

            all_data.extend(data['data'])
            page += 1
        
        # if response.status_code == 200:
        #     items = response.json()
        # else:
        #     await client.post(webhook_url, headers={"Content-type": "application/json"}, data=json.dumps({
        #         "text": "GET 요청이 실패했어요!"
        #     }))
        #     items = {'data': []}

        for item in all_data:
            id = item['id']
            delete_url = f"https://match-diary-backend-79e304d3a79e.herokuapp.com/api/schedule-{year}s/{id}"
            delete_response = await client.delete(delete_url, headers=headers)

            if delete_response.status_code != 200:
                await client.post(webhook_url, headers={"Content-type": "application/json"}, data=json.dumps({
                    "text": "데이터 삭제 중 문제 발생! 주인님 여기에요!"
                }))
                return
        
        await client.post(webhook_url, headers={"Content-type": "application/json"}, data=json.dumps({
            "text": f"{len(all_data)}데이터 삭제 완료! 크롤링 시작!"
        }))

# KOB 홈페이지 기준, 현재 ~0829 일정까지 공개
async def run_crawler(): 
    print("RUN CRAWLER START")

    async with httpx.AsyncClient() as client:
        for month in ['03', '04', '05', '06', '07', '08']:
            data = {
                "leId": '1',
                "srIdList": '0,9,6',
                "seasonId": year,
                "gameMonth": month,
                "teamId": ""
            }
            r = await client.post("https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList", data=data)
            root = json.loads(r.content.decode("utf-8"))
            
            # 크롤링한 데이터 전처리
            # 0~1 -> 날짜
            # 2 -> 경기 정보 (홈팀 / 홈팀점수 / 원정팀 점수 / 원정팀)
            # 7 -> 경기장
            # 8 -> 비고 (특수경기)
            formedData = []

            for row in root['rows']:
                data = {}
                if row['row'][0]['Class'] == 'day':
                    # 날짜
                    data['date'] = f"{year}.{row['row'][0]['Text']}"
                    data['time'] = bs(row['row'][1]['Text']).get_text()

                    # 경기정보
                    info = bs(row['row'][2]['Text']).find_all('span')
                    if len(info) > 3:  
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
                    data['date'] = f"{year}.{formedData[-1]['date']}"
                    data['time'] = bs(row['row'][0]['Text']).get_text()

                    # 경기정보
                    info = bs(row['row'][1]['Text']).find_all('span')
                    if len(info) > 3:  
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
                await client.post(f"https://match-diary-backend-79e304d3a79e.herokuapp.com/api/schedule-{year}s", 
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
        await client.post(webhook_url, headers={"Content-type": "application/json"}, data=json.dumps(webhook_data))

async def main():
    await clear_schema()
    await run_crawler()

if __name__ == "__main__":
    asyncio.run(main())
