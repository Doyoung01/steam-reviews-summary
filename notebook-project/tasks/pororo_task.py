import sys
from contextlib import redirect_stdout
from io import StringIO
from pororo import Pororo
import warnings
import logging
import os

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Logging 레벨 설정
logging.basicConfig(level=logging.ERROR)

def reduce_repeated_pattern(text):
    text_length = len(text)
    for i in range(1, text_length // 2 + 1):  # 가능한 패턴 길이 탐색
        pattern = text[:i]  # 패턴 추출
        repeated = pattern * (text_length // len(pattern))  # 패턴 반복
        if repeated.startswith(text):  # 텍스트가 패턴으로 시작하는지 확인
            return pattern
    return text  # 반복 패턴이 없을 경우 원본 텍스트 반환

def summarize_in_chunks(text, chunk_size=1024, final_length=300):
    text = reduce_repeated_pattern(text)
    
    if len(text) < final_length:
        return text
    
    # 모든 출력 무시를 위한 임시 stdout 설정
    with open(os.devnull, "w") as fnull, redirect_stdout(fnull):
        summarizer = Pororo(task="summarization", lang="ko")

    # 텍스트를 청크로 나누고 요약
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    partial_summaries = [summarizer(chunk) for chunk in chunks]
    combined_summary = " ".join(partial_summaries)

    # 최종 요약 반복 압축
    final_summary = summarizer(combined_summary[:chunk_size])
    while len(final_summary) > final_length:
        final_summary = summarizer(final_summary[:chunk_size])

    final_summary = reduce_repeated_pattern(final_summary)
    
    return final_summary

if __name__ == "__main__":
    text = sys.argv[1]
    chunk_size = int(sys.argv[2])
    final_length = int(sys.argv[3])
    summary = summarize_in_chunks(text, chunk_size, final_length)
    print(summary)

