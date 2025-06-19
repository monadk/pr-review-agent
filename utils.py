import re

def parse_diff(diff_text: str) -> list[dict]:
    """
    Git diff 텍스트를 파일별로 분리합니다.

    Args:
        diff_text (str): 전체 Git diff 텍스트.

    Returns:
        list[dict]: 각 파일의 'filename'과 'diff_content'를 포함하는 딕셔너리 리스트.
    """
    # diff --git으로 시작하는 패턴을 기준으로 diff 텍스트를 분할
    # (?=...)는 lookahead assertion으로, 구분자(diff --git)를 결과에 포함시킵니다.
    file_chunks = re.split(r'(?=diff --git a/.*? b/.*?)', diff_text)
    
    files = []
    # 첫 번째 청크는 보통 비어 있으므로, 비어있지 않은 청크만 처리
    for chunk in filter(None, file_chunks):
        # 파일명 추출 (+++ b/ 이후의 경로)
        filename_match = re.search(r'\+\+\+ b/(.*?)\n', chunk)
        if filename_match:
            filename = filename_match.group(1)
            files.append({
                "filename": filename,
                "diff_content": chunk.strip()
            })
            
    return files

def get_copy_button_html(markdown_to_copy: str) -> str:
    """
    마크다운 텍스트를 클립보드에 복사하는 버튼의 HTML과 JavaScript 코드를 생성합니다.

    Args:
        markdown_to_copy (str): 복사할 마크다운 텍스트.

    Returns:
        str: 버튼을 렌더링하기 위한 HTML 문자열.
    """
    # HTML, CSS, JavaScript 코드
    # JavaScript 내에서 백틱(`) 문자가 문제를 일으키지 않도록 \\`로 이스케이프 처리
    escaped_markdown = markdown_to_copy.replace("`", "\\`")

    return f"""
    <style>
        .copy-button {{
            display: inline-block;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: 500;
            color: #0F1116; /* 텍스트 색상 */
            background-color: #FFFFFF; /* 배경 색상 */
            border: 1px solid rgba(49, 51, 63, 0.2); /* 테두리 */
            border-radius: 0.5rem; /* 둥근 모서리 */
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: center;
        }}
        .copy-button:hover {{
            color: #F83A3D; /* 호버 시 텍스트 색상 */
            border-color: #F83A3D; /* 호버 시 테두리 색상 */
        }}
        .copy-button:active {{
            background-color: #F0F2F6; /* 클릭 시 배경 색상 */
        }}
        #copyMessage {{
            margin-left: 10px;
            color: green;
            font-weight: 500;
            transition: opacity 0.5s;
        }}
    </style>
    <textarea id="markdownToCopy" style="display:none;">{escaped_markdown}</textarea>
    <button class="copy-button" onclick="copyToClipboard()">📋 최종 보고서 복사</button>
    <span id="copyMessage"></span>
    <script>
        function copyToClipboard() {{
            var textArea = document.getElementById("markdownToCopy");
            
            // Clipboard API가 보안 컨텍스트(https, localhost)에서만 작동하므로,
            // 실패할 경우를 대비하여 기존 execCommand 방식도 고려할 수 있으나,
            // 최신 브라우저에서는 navigator.clipboard를 우선 사용합니다.
            navigator.clipboard.writeText(textArea.value).then(function() {{
                var msgElement = document.getElementById("copyMessage");
                msgElement.innerText = "복사했어요!";
                // 3초 후 메시지 서서히 사라지게 함
                setTimeout(function() {{ msgElement.style.opacity = 0; }}, 2500);
                setTimeout(function() {{ 
                    msgElement.innerText = "";
                    msgElement.style.opacity = 1;
                }}, 3000);
            }}, function(err) {{
                console.error('클립보드 복사 실패: ', err);
                var msgElement = document.getElementById("copyMessage");
                msgElement.innerText = "복사 실패!";
                msgElement.style.color = "red";
            }});
        }}
    </script>
    """
