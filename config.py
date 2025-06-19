import os
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- 환경 변수 로드 및 검증 ---
def get_env_variable(name: str) -> str:
    """환경 변수를 가져오고, 없으면 예외를 발생시킵니다."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"'{name}' 환경 변수가 설정되지 않았습니다.")
    return value

try:
    # GitHub 환경 변수
    GITHUB_TOKEN = get_env_variable("GITHUB_TOKEN")

    # Azure OpenAI 환경 변수
    AZ_OPENAI_ENDPOINT = get_env_variable("AZ_OPENAI_ENDPOINT")
    AZ_OPENAI_KEY = get_env_variable("AZ_OPENAI_KEY")
    AZ_OPENAI_ENGINE = get_env_variable("AZ_OPENAI_ENGINE")
    AZ_OPENAI_VERSION = get_env_variable("AZ_OPENAI_VERSION")

    # Azure AI Search 환경 변수
    AZ_SEARCH_ENDPOINT = get_env_variable("AZ_SEARCH_ENDPOINT")
    AZ_SEARCH_KEY = get_env_variable("AZ_SEARCH_KEY")
    AZ_INDEX = get_env_variable("AZ_INDEX")

except ValueError as e:
    # 환경 변수 설정에 문제가 있을 경우, 사용자에게 명확한 에러 메시지를 보여주고 실행 중단
    import streamlit as st
    st.error(f"환경 변수 설정 오류: {e}")
    st.info("애플리케이션을 실행하기 전에 .env 파일을 올바르게 설정했는지 확인해주세요.")
    st.stop()


# --- Azure 클라이언트 초기화 ---
# Azure OpenAI 클라이언트 초기화
llm = AzureOpenAI(
    api_version=AZ_OPENAI_VERSION,
    azure_endpoint=AZ_OPENAI_ENDPOINT,
    api_key=AZ_OPENAI_KEY
)

# Azure AI Search 클라이언트 초기화
search_client = SearchClient(
    AZ_SEARCH_ENDPOINT,
    AZ_INDEX,
    AzureKeyCredential(AZ_SEARCH_KEY)
)
