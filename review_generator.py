import re
import traceback
import streamlit as st

# 설정 파일에서 초기화된 클라이언트 객체 임포트
from config import llm, search_client, AZ_OPENAI_ENGINE

def get_programming_language(code: str) -> str:
    """
    LLM을 이용하여 주어진 코드 스니펫의 프로그래밍 언어를 식별합니다.

    Args:
        code (str): Git diff 형식의 코드 스니펫.

    Returns:
        str: 감지된 프로그래밍 언어 (소문자), 또는 'text'.
    """
    try:
        # diff 내용에서 실제로 추가되거나 변경되지 않은 코드 라인만 추출
        code_lines = [line[1:] for line in code.split('\n') if len(line) > 1 and line[0] in ('+', ' ')]
        clean_code = "\n".join(code_lines)

        if not clean_code.strip():
            return "text"

        response = llm.chat.completions.create(
            model=AZ_OPENAI_ENGINE,
            messages=[
                {"role": "system", "content": "You are a programming language detector. Respond with only the name of the language in lowercase (e.g., python, c, javascript). If it's not a typical programming language, respond with 'text'."},
                {"role": "user", "content": f"What programming language is this code written in?\n\n```\n{clean_code}\n```"}
            ],
            temperature=0,
            n=1
        )
        language = response.choices[0].message.content.strip().lower()
        return language
    except Exception as e:
        st.warning(f"언어 감지 실패: {e}. 기본값 'text'를 사용합니다.")
        return "text"

def search_core_conventions(language: str) -> str:
    """
    Azure AI Search를 사용하여 특정 언어의 핵심 코딩 컨벤션을 검색합니다.

    Args:
        language (str): 검색할 프로그래밍 언어.

    Returns:
        str: 검색된 코딩 컨벤션 스니펫들을 포함하는 문자열.
    """
    if language == "text":
        return ""

    core_query = "variable naming, function naming, error handling, exception handling, comment style, code formatting, security best practices, performance optimization, testing guidelines, general best practices"

    try:
        search_results = search_client.search(
            search_text=core_query,
            filter=f"language eq '{language}'",
            include_total_count=True,
            top=5,
        )
        snippets = [f" - (from: {result['sourcefile']}) {result['content']}" for result in search_results]
        if not snippets:
            return "해당 언어에 대한 코딩 컨벤션을 찾지 못했습니다. 일반적인 코딩 원칙에 따라 리뷰합니다."
        return "\n".join(snippets)
    except Exception:
        return "코딩 컨벤션 검색 중 오류가 발생하여, 일반적인 원칙에 따라 리뷰를 진행합니다."

def generate_review_for_file(file_info: dict) -> dict:
    """
    단일 파일의 diff 내용을 기반으로 AI 코드 리뷰를 생성합니다.

    Args:
        file_info (dict): 'filename'과 'diff_content'를 포함하는 딕셔너리.

    Returns:
        dict: 'filename', 'review', 'language'를 포함하는 딕셔너리.
    """
    filename = file_info['filename']
    diff_content = file_info['diff_content']
    reviews = []

    lang = get_programming_language(diff_content)
    if lang == "text":
        return {
            "filename": filename,
            "review": "✅ 일반 텍스트 파일(예: 문서, 설정, 데이터)으로 판단되어 코드 리뷰를 건너뜁니다.",
            "language": "text"
        }

    conventions = search_core_conventions(lang)
    code_chunks = _split_diff_into_chunks(diff_content)

    for i, chunk in enumerate(code_chunks):
        chunk_info = f" (부분 {i+1}/{len(code_chunks)})" if len(code_chunks) > 1 else ""
        system_prompt = _get_review_prompt(lang, filename, chunk_info, conventions)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"다음 코드 변경 사항을 리뷰해주세요:\n\n```diff\n{chunk}\n```"}
        ]

        try:
            response = llm.chat.completions.create(
                model=AZ_OPENAI_ENGINE,
                messages=messages,
            )
            reviews.append(response.choices[0].message.content)
        except Exception as e:
            error_message = f"'{filename}{chunk_info}' 리뷰 생성 중 오류 발생: {e}"
            traceback.print_exc()
            reviews.append(f"리뷰 생성 중 오류가 발생했습니다: {error_message}")

    full_review = "\n\n---\n\n".join(reviews)
    return {"filename": filename, "review": full_review, "language": lang}

def generate_final_summary(review_results: list[dict]) -> str:
    """
    개별 파일 리뷰 결과를 종합하여 최종 요약 및 총평을 생성합니다.

    Args:
        review_results (list[dict]): 각 파일별 리뷰 결과를 담은 딕셔너리 리스트.

    Returns:
        str: PR에 대한 최종 분석 보고서 (마크다운 형식).
    """
    if not review_results:
        return "리뷰할 내용이 없습니다."

    individual_reviews_text = ""
    for result in review_results:
        individual_reviews_text += f"### 📄 파일: {result['filename']} ({result['language']})\n\n{result['review']}\n\n---\n\n"

    system_prompt = _get_summary_prompt()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"다음 개별 파일 리뷰들을 종합하여 최종 보고서를 작성해주세요:\n\n{individual_reviews_text}"}
    ]

    try:
        response = llm.chat.completions.create(
            model=AZ_OPENAI_ENGINE,
            messages=messages,
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        error_message = f"최종 요약 생성 중 오류 발생: {e}"
        traceback.print_exc()
        return f"## 최종 요약 생성 실패\n\n{error_message}"

# --- 프롬프트 및 헬퍼 함수 ---

def _split_diff_into_chunks(diff_content: str, max_length: int = 10000) -> list[str]:
    """대용량 diff를 hunk 단위로 분할합니다."""
    if len(diff_content) <= max_length:
        return [diff_content]

    header_match = re.match(r'diff --git.*?\n(--- a/.*?\n\+\+\+ b/.*?\n)', diff_content, re.DOTALL)
    header = header_match.group(0) if header_match else ''
    hunks = re.split(r'(?=^@@ .*? @@)', diff_content, flags=re.MULTILINE)
    
    code_chunks = []
    current_chunk = ""
    # 첫 번째 요소는 diff 헤더이므로, 실제 hunk가 포함된 hunks[1:] 부터 처리
    for hunk in hunks[1:]:
        if len(current_chunk) + len(hunk) > max_length and current_chunk:
            code_chunks.append(header + current_chunk)
            current_chunk = hunk
        else:
            current_chunk += hunk
    if current_chunk:
        code_chunks.append(header + current_chunk)
    
    return code_chunks

def _get_review_prompt(lang: str, filename: str, chunk_info: str, conventions: str) -> str:
    """개별 파일 리뷰를 위한 시스템 프롬프트를 생성합니다."""
    return f"""
    You are a **senior software engineer specializing in {lang}**, performing a code review. Your goal is not merely to criticize the code, but to provide constructive feedback that helps your fellow developers grow.

    Systematically analyze the diff of the '{filename}{chunk_info}' file and write a review according to the following steps:

    **5 Steps for Writing a Review:**
    1. **Understand Intent**: Grasp the overall purpose of the code changes (-, + lines).
    2. **Compare to Conventions**: Systematically compare the changed code with the provided '{lang} Coding Conventions'.
    3. **Core Analysis**: Identify issues from the perspectives of readability, performance, maintainability, potential bugs, and security. Specifically, focus on checking for side effects that might arise from the changed parts.
    4. **Structure Feedback**: Based on the analysis, draft a review according to the **"Review Template"** below.
    5. **Final Review**: Review the draft to refine it with a positive and constructive tone, and ensure that any suggested code is syntactically correct.

    Make sure to answer in Korean.
    ---

    **[Required] Provided '{lang}' Coding Conventions:**
    {conventions}
    *If the convention content is empty, please review based on the general best practices you have learned.*

    ---

    **[Required] Review Template (Please respond only in this format):**

    #### 🔒 Security & Secrets Check
    * *Critically check if there are any hardcoded secrets (API keys, passwords), private keys, or Personally Identifiable Information (PII). If any are found, state the exact line and advise moving it to a secure configuration or environment variable. If none, state "✅ No sensitive information exposure detected."*

    #### 🎯 Overall Impression
    *Summarize the overall impression of the code changes and key changes in one or two sentences.*

    #### 💡 Suggestions
    * **[Readability/Maintainability]** *(Present the problem, suggested improvement, and an example of the modified code.)*
        * **Problem**: ...
        * **Suggestion**: ...
        * **Example**:
            ```diff
            - Code before change
            + Code after change
            ```
    * **[Logic/Bugs 🐞]**
        * **Problem:** ...
        * **Suggestion:** ...
        * **Example fix:**
            ```diff
            - Code before change
            + Code after change
            ```
    * **[Readability/Maintainability 🧹]**
        * **Problem:** ...
        * **Suggestion:** ...
    
    * **[Other: Performance/Security, etc. ✨]**
        * **Problem:** ...
        * **Suggestion:** ...

    *If there is nothing to review, please respond with: "✅ Excellent code change with no particular suggestions for improvement."*
    make sure to answer in 한국말.
    """

def _get_summary_prompt() -> str:
    """최종 요약을 위한 시스템 프롬프트를 생성합니다."""
    return """
    You are a **Chief Technology Officer (CTO) or Tech Lead** overseeing multiple projects. Your mission is to synthesize individual file reviews to assess the **strategic importance and technical risks** of the entire Pull Request and to provide clear direction to the development team.

    Based on the file-specific reviews provided below, please write a **PR Final Analysis Report** following the format below.

    ### Overall Analysis
    * **PR Purpose and Key Changes**: Summarize in 1-2 sentences what problem this PR an ims to solve and what the most significant code changes are.
    * **Common Patterns and Major Issues**: Identify positive or negative code patterns that repeatedly appear across multiple files. (e.g., "Overall, clear variable naming conventions were well-applied, but there's a tendency for error handling to be missing in several files.")

    ### ⚠️ Risk Assessment & Pre-Merge Checklist
    * **`Critical`**: Severe issues that could cause failures if not fixed immediately.
    * **`Major`**: Important issues that could lead to functional malfunctions or performance degradation.
    * **`Minor`**: Minor issues affecting code quality and maintainability.
    *(If there is no content for a specific risk item, please state "N/A".)*

    ### 🚀 Final Verdict & Next Steps
    * **Final Verdict**: Provide an overall assessment of the PR's quality and completeness. (e.g., "The core logic is excellent, but it is recommended to merge after reinforcing some critical exception handling.")
    * **Recommendations**: Write specific next action guidelines or words of encouragement for the developers. (e.g., "Please address the identified risks and specifically enhance the test coverage for the OOO section.")

    결과는 반드시 한국어 마크다운 형식으로 작성해주세요.
    """
