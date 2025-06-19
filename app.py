import streamlit as st
import concurrent.futures
import traceback

# 모듈화된 파일에서 필요한 함수와 객체 임포트
from github_util import extract_github_info, fetch_pr_diff
from utils import parse_diff, get_copy_button_html
from review_generator import generate_review_for_file, generate_final_summary
from config import GITHUB_TOKEN

def main():
    """
    Streamlit 애플리케이션의 메인 함수
    """
    st.set_page_config(page_title="PR AI 리뷰어 v1.0", layout="wide")
    st.title("🤖 GitHub PR AI 리뷰어 v1.0")

    diff_text = ""
    # GitHub PR URL 입력 필드
    pr_url = st.text_input("🔗 GitHub Pull Request URL을 입력해주세요")

    if pr_url:
        # GitHub URL에서 소유자, 저장소, PR 번호 추출
        parsed_info = extract_github_info(pr_url)
        if not parsed_info:
            st.error("❌ 유효하지 않은 GitHub Pull Request URL입니다.")
        else:
            owner, repo, pr_num = parsed_info
            try:
                with st.spinner("GitHub에서 PR 정보를 가져오는 중..."):
                    # GitHub API를 통해 PR diff 내용 가져오기
                    diff_text = fetch_pr_diff(owner, repo, pr_num, GITHUB_TOKEN)
            except Exception as e:
                st.error(f"GitHub PR 정보를 가져오는 중 오류 발생: {e}")
                st.stop() # 오류 발생 시 실행 중단

    # diff 내용이 있고 '리뷰 생성' 버튼이 눌렸을 때
    if diff_text and st.button("✨ 리뷰 생성", type="primary"):
        # diff 텍스트를 파일별로 분리
        file_diffs = parse_diff(diff_text)

        if not file_diffs:
            st.warning("분석할 코드 변경사항을 찾지 못했습니다. diff 형식이 올바른지 확인해주세요.")
        else:
            run_review_process(file_diffs)

    # --- 복사 버튼 표시 ---
    # 이전에 생성된 리뷰 결과가 있을 경우에만 복사 버튼 표시
    if "last_review" in st.session_state and st.session_state["last_review"]:
        st.markdown("---")
        # 유틸리티 함수를 사용하여 복사 버튼 HTML 생성 및 표시
        copy_html = get_copy_button_html(st.session_state["last_review"])
        st.components.v1.html(copy_html, height=50)

def run_review_process(file_diffs: list[dict]):
    """
    파일별 코드 리뷰 및 최종 요약 생성 프로세스를 실행합니다.

    Args:
        file_diffs (list[dict]): 파일별 diff 정보를 담은 리스트
    """
    with st.spinner("🧠 Azure AI가 코드를 분석하고 리뷰를 생성하는 중입니다... 잠시만 기다려주세요."):
        review_results = []
        placeholders = {file_info['filename']: st.empty() for file_info in file_diffs}

        # 파일별 분석 상태를 초기에 '분석 중'으로 표시
        for filename, placeholder in placeholders.items():
            with placeholder.container():
                st.expander(f"**📄 파일: {filename}** - ⏳ 분석 중...", expanded=True)

        # ThreadPoolExecutor를 사용하여 파일 리뷰를 병렬로 처리
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_file = {executor.submit(generate_review_for_file, file_info): file_info for file_info in file_diffs}

            for future in concurrent.futures.as_completed(future_to_file):
                file_info = future_to_file[future]
                filename = file_info['filename']
                placeholder = placeholders[filename]

                try:
                    result = future.result()
                    review_results.append(result)
                    # 완료된 파일의 UI를 업데이트하여 결과 표시
                    with placeholder.container():
                        with st.expander(f"**📄 파일: {result['filename']}** ({result['language']}) - ✅ 분석 완료", expanded=False):
                            st.markdown(result['review'])
                except Exception as exc:
                    error_message = f"리뷰 생성 중 에러 발생: {exc}"
                    traceback.print_exc()
                    # 에러 발생 시 UI에 에러 메시지 표시
                    with placeholder.container():
                        st.expander(f"**📄 파일: {filename}** - ❌ 분석 실패", expanded=True).error(error_message)

    st.success("✅ 모든 파일 분석이 완료되었습니다! 최종 보고서를 생성합니다...")

    # 모든 개별 리뷰가 완료된 후 최종 요약 생성
    with st.spinner("📜 최종 보고서 작성 중..."):
        # 결과를 파일명 순으로 정렬하여 일관성 유지
        review_results.sort(key=lambda x: x['filename'])
        final_summary = generate_final_summary(review_results)

    st.success("✨ 최종 리뷰가 생성되었습니다!")
    st.markdown("---")

    # 최종 응답 템플릿 적용 및 결과 표시
    st.markdown("## 🚀 PR 리뷰 최종 보고서")
    st.markdown(final_summary)

    # 복사 기능을 위해 전체 내용을 Streamlit session_state에 저장
    st.session_state["last_review"] = f"## 🚀 PR 리뷰 최종 보고서\n\n{final_summary}"


if __name__ == "__main__":
    main()
