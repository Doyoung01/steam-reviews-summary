from pydantic import BaseModel
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import requests
import time
import pandas as pd
import re
import paramiko 
import json
from dotenv import load_dotenv
import os

# .env 파일 경로
load_dotenv()

app = FastAPI()

# SSH 설정
client = OpenAI(
    api_key=os.getenv("API_KEY"),  # This is the default and can be omitted
)
SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = os.getenv("SSH_PORT")
SSH_USER = os.getenv("SSH_USER")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
REMOTE_SCRIPT_PATH = os.getenv("REMOTE_SCRIPT_PATH")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프론트엔드에서의 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PororoRequest(BaseModel):
    text: str
    chunk_size: int = 1024
    final_length: int = 300

def execute_script(script_name: str, *args):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD)
        
        # 명령어 구성 및 실행
        command = f"python3 {REMOTE_SCRIPT_PATH}{script_name} {' '.join(map(str, args))}"
        if script_name == "pororo_task.py":
            command = f"python3 {REMOTE_SCRIPT_PATH}{script_name} '{args[0]}' {args[1]} {args[2]}"
        stdin, stdout, stderr = ssh.exec_command(command)
        
        # 결과 읽기
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        ssh.close()
        
        if error:
            return {"success": False, "error": error}
        return {"success": True, "output": output}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/run-pororo/")
async def run_pororo(request: PororoRequest):
    text = request.text
    chunk_size = request.chunk_size
    final_length = request.final_length

    result = execute_script("pororo_task.py", text, chunk_size, final_length)
    print(result)
    if not result:
        print("Error: Output is empty")
        raise HTTPException(status_code=500, detail="Output is empty")

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"summary": result["output"]}

@app.post("/run-torch/")
async def run_torch(texts: list[str]):
    result = execute_script("torch_task.py", *texts)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    try:
        return json.loads(result['output'].replace("'", '"'))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON output")


# 게임 검색 API
def search_game_on_steamspy(query: str):
    # SteamSpy API 호출
    url = "https://steamspy.com/api.php?request=all"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed to fetch data from SteamSpy")

    data = response.json()

    # 검색어와 일치하는 게임 필터링
    results = []
    for appid, game_data in data.items():
        if query.lower() in game_data['name'].lower():
            results.append({"appid": appid, "name": game_data['name']})

    return results

@app.get("/search_game")
def search_game(query: str = Query(..., description="Name of the game to search")):
    try:
        results = search_game_on_steamspy(query)
        if not results:
            raise HTTPException(status_code=404, detail="No games found.")
        return {"query": query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_game_app_id(game_url):
    app_id = game_url.split('/')[-3]

    return app_id

def get_game_name(app_id):
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data[str(app_id)]['success']:
            return data[str(app_id)]['data']['name']
    return None

@app.get("/search_game_by_link")
def search_game_by_link(game_url: str = Query(..., description="Steam game URL")):
    try:
        app_id = get_game_app_id(game_url)
        results = get_game_name(app_id)
        if not results:
            raise HTTPException(status_code=404, detail="No games found.")
        return {"query": app_id, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 리뷰 크롤링 API
def get_steam_reviews(app_id, num_per_page=100, delay=1.0):
    cursor = '*'  # 첫 요청에서는 '*'를 사용하거나 생략 가능
    reviews = []

    while True:
        url = f"https://store.steampowered.com/appreviews/{app_id}?json=1"
        params = {
            'num_per_page': num_per_page,  # 한 번의 요청으로 가져올 수 있는 리뷰의 최대 개수
            'cursor': cursor,  # 페이지 네이션 처리를 위함
            'filter': 'all',
            'language': 'koreana',  # 한국어 리뷰만 가져옴
            'review_type': 'all',
            'purchase_type': 'all',
        }

        try:
            response = requests.get(url, params=params, timeout=10)  # 타임아웃 10초 설정
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            break

        if data.get('success') != 1:
            print("API 호출 실패")
            break

        new_reviews = data.get('reviews', [])
        reviews.extend(new_reviews)  # 리뷰 데이터 추가

        # 다음 페이지로 이동하기 위한 cursor 업데이트
        cursor = data.get('cursor')

        if not cursor or len(new_reviews) < num_per_page:
            break

        time.sleep(delay)

    return reviews

def get_torch_result(texts):
    url = "http://127.0.0.1:8000/run-torch/"

    try:
        response = requests.post(url, json=texts, timeout=None)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error during the request: {str(e)}")
    
def get_pororo_result(texts, chunk_size=1024, final_length=300):
    url = "http://127.0.0.1:8000/run-pororo/"

    data = {
        "text": texts,
        "chunk_size": chunk_size,
        "final_length": final_length
    }

    try:
        response = requests.post(url, json=data, timeout=None)  # timeout=None은 무한 대기
        # 결과 출력
        if response.status_code == 200:
            return response.json()['summary']
        else:
            print("Failed:", response.status_code, response.text)
    except requests.exceptions.RequestException as e:
        print("Error during the request:", str(e))


# 리뷰 전처리 함수
def df_reviews(reviews):
    df = pd.DataFrame(reviews)
    df = df[['review', 'voted_up']]
    df['review'] = df['review'].apply(detect_all_eng)   # 영어 리뷰 제거
    df['review'] = df['review'].apply(preprocess_text)  # 특수문자 제거, 중국어 및 일본어 제거 등 텍스트 전처리
    
    print("Preprocessed reviews:", df['review'].head())

    df['review'] = df['review'].apply(remove_stopwords_from_text)   # 불용어 제거
    df['review'] = df['review'].apply(filtering_with_csv) # 사전을 이용한 욕설 제거
    df['review'] = df['review'].apply(filtering_with_re_ex) # 정규식을 이용한 욕설 제거
    
    torch_result = get_torch_result(df['review'].tolist())  # 토치 모델을 이용한 욕설 제거

    if not isinstance(torch_result, list) or not all(isinstance(item, dict) for item in torch_result):
        raise ValueError("Invalid API response format. Expected a list of dictionaries.")

    result_df = pd.DataFrame(torch_result)
    df['label'] = result_df['label']
    df['probability'] = result_df['probability']
    df = df[df['label'] == 8]

    print("Filtered reviews:", df['review'].head())

    df = remove_invalid_reviews(df, 'review')   # 리뷰가 없는 경우 제거

    if df.empty:
        raise ValueError("All reviews are filtered out during preprocessing.")
    
    return df

def detect_all_eng(text):
    if not isinstance(text, str):
        return ''
    
    _text = re.sub(r'[0-9]', '', text)

    if re.fullmatch(r"[A-Za-z\s]*", _text):
        return ''
    else:
        return text

def preprocess_text(text):
    if not isinstance(text, str):
        return ''
    
    # URL 제거 (http 또는 www로 시작하는 URL 제거)
    text = re.sub(r'(http\S+|www\.\S+)', '', text) 

    # 특정 이모지와 한글, 숫자, 공백, 밑줄 이외의 문자 제거
    text = re.sub(r'[^\w\s\u2705\u2611\u2714\u26D4\u1F6AB\u2716\u274C\u274E\u1F534\u1F7E2가-힣]', '', text)

    # 한글 자음, 모음 제거
    text = re.sub(r'[\u3131-\u318E\u1100-\u11FF]', '', text)

    # 중국어 및 일본어 문자 제거
    text = re.sub(r'[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u31F0-\u31FF\u3000-\u303F]', '', text)

    # 불필요한 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def remove_stopwords_from_text(text):
    # 불용어 파일 로드
    with open('./import_files/stopwords.word.txt', 'r', encoding='utf-8') as file:
        stopwords = file.read().splitlines()
    stopwords_set = set.union(set(stopwords)    )
    
    words = text.split()
    # 불용어가 아닌 단어만 선택
    filtered_words = [word for word in words if word not in stopwords_set]
    
    return ' '.join(filtered_words)

def remove_invalid_reviews(df, column_name):
    try:
        filtered_df = df[df[column_name].apply(lambda text: isinstance(text, str) and text.strip() != '')]
        return filtered_df
    except Exception as e:
        print(f"Error: {e}")
        return df

badwords = pd.read_csv('./import_files/badwords.csv')['badwords'].dropna().tolist()

def filtering_with_csv(text):
    if not isinstance(text, str):
        return ''
    
    badwords_pattern = re.compile(r'\b(' + '|'.join(map(re.escape, badwords)) + r')\b')
    filtered_text = badwords_pattern.sub('', text)

    return filtered_text

CURSEWORD_PATTERN = re.compile(r'[시씨씪슈쓔쉬쉽쒸쓉](?:[0-9]*|[0-9]+ *)[바발벌빠빡빨뻘파팔펄]|[섊좆좇졷좄좃좉졽썅춍봊]|[ㅈ조][0-9]*까|ㅅㅣㅂㅏㄹ?|ㅂ[0-9]*ㅅ|[ㅄᄲᇪᄺᄡᄣᄦᇠ]|[ㅅㅆᄴ][0-9]*[ㄲㅅㅆᄴㅂ]|[존좉좇][0-9 ]*나|[자보][0-9]+지|보빨|[봊봋봇봈볻봁봍] *[빨이]|[후훚훐훛훋훗훘훟훝훑][장앙]|[엠앰]창|애[미비]|애자|[가-탏탑-힣]색기|(?:[샊샛세쉐쉑쉨쉒객갞갟갯갰갴겍겎겏겤곅곆곇곗곘곜걕걖걗걧걨걬] *[끼키퀴])|새 *[기키퀴]|[병븅][0-9]*[신딱딲]|미친[가-닣닥-힣]|[믿밑]힌|[염옘][0-9]*병|[샊샛샜샠섹섺셋셌셐셱솃솄솈섁섂섓섔섘]기|[섹섺섻쎅쎆쎇쎽쎾쎿섁섂섃썍썎썏][스쓰]|[지야][0-9]*랄|니[애에]미|갈[0-9]*보[^가-힣]|[뻐뻑뻒뻙뻨][0-9]*[뀨큐킹낑)|꼬[0-9]*추|곧[0-9]*휴|[가-힣]슬아치|자[0-9]*박꼼|빨통|[사싸](?:이코|가지|[0-9]*까시)|육[0-9]*시[랄럴]|육[0-9]*실[알얼할헐]|즐[^가-힣]|찌[0-9]*(?:질이|랭이)|찐[0-9]*따|찐[0-9]*찌버거|창[녀놈]|[가-힣]{2,}충[^가-힣]|[가-힣]{2,}츙|부녀자|화냥년|환[양향]년|호[0-9]*[구모]|조[선센][징]|조센|[쪼쪽쪾](?:[발빨]이|[바빠]리)|盧|무현|찌끄[레래]기|(?:하악){2,}|하[앍앜]|[낭당랑앙항남담람암함][ ]?[가-힣]+[띠찌]|느[금급]마|文在|在寅|(?<=[^\n])[家哥]|속냐|[tT]l[qQ]kf|Wls|[ㅂ]신|[ㅅ]발|[ㅈ]밥|장애인|쓰레기')

def filtering_with_re_ex(text):
    if not isinstance(text, str):
        return ''
    
    filtered_text = CURSEWORD_PATTERN.sub('', text)
    return filtered_text

@app.get("/reviews")
def fetch_reviews(app_id: int = Query(..., description="Steam App ID"), num_reviews: int = Query(100, description="Number of reviews to fetch")):
    try:
        reviews = get_steam_reviews(app_id, num_per_page=num_reviews)
        
        if not reviews:
            raise HTTPException(status_code=404, detail="No reviews found.")
        
        print("Length of the fetched reviews:", len(reviews))
        
        df = df_reviews(reviews)

        print("Length of the filtered DataFrame:", len(df))

        if df.empty:
            raise HTTPException(status_code=404, detail="No valid reviews after processing.")

        pos_text = df[df['voted_up'] == True]['review'].tolist()
        neg_text = df[df['voted_up'] == False]['review'].tolist()

        pos_summary = get_pororo_result(" ".join(pos_text), "1024", "300")
        neg_summary = get_pororo_result(" ".join(neg_text), "1024", "300")

        refined_pos_summary = refine_summary_with_chatgpt(pos_summary)
        refined_neg_summary = refine_summary_with_chatgpt(neg_summary)

        return {
            "positive_summary": refined_pos_summary,
            "negative_summary": refined_neg_summary
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    
def refine_summary_with_chatgpt(summary_text: str):
    try:
        # OpenAI Chat API 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            #  model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": (
                    f"다음 리뷰 텍스트에서 중복된 내용을 제거하고, 맞춤법과 문장을 자연스럽게 다듬어 주시기 바랍니다. "
                    f"문장의 어미는 반드시 '~다' 형태로 통일해 주세요.\n"
                    f"'리뷰 내용 요약:', '리뷰를 요약하면 다음과 같습니다.' 같은 문구 없이, 핵심 내용을 간결하고 명확하게 작성해주세요.\n"
                    f"내용: {summary_text if summary_text else '요약 내용이 없습니다.'}"
                )}
            ],
            max_tokens=150
        )

        # 결과 메시지 반환
        return response.choices[0].message.content
    except Exception as e:  # 일반적인 예외 처리로 변경
        print(f"Error with OpenAI API: {e}")
        raise ValueError("Error processing summary with ChatGPT API")
