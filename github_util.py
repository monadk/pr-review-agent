import re, requests
from typing import Optional

def extract_github_info(pr_url: str) -> Optional[tuple]:
    """
    GitHub Pull Request URL에서 소유자(owner), 저장소(repo), PR 번호(pr_number)를 추출합니다.

    Args:
        url (str): GitHub PR URL.

    Returns:
        Optional[Tuple[str, str, int]]: (소유자, 저장소, PR 번호) 튜플.
                                         매칭 실패 시 None을 반환합니다.
    """
    # 일반적인 GitHub PR URL 패턴 (e.g., https://github.com/owner/repo/pull/123)
    pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    m = re.match(pattern, pr_url)
    if not m: return None
    owner, repo, num = m.groups()
    
    return owner, repo, int(num)

def fetch_pr_diff(owner: str, repo: str, pr_number: int, github_token: str) -> str:
    """
    GitHub API를 사용하여 Pull Request의 diff 내용을 가져옵니다.

    Args:
        owner (str): 저장소 소유자.
        repo (str): 저장소 이름.
        pr_number (int): Pull Request 번호.
        token (str): GitHub 개인 접근 토큰(PAT).

    Returns:
        str: PR의 diff 텍스트.

    Raises:
        requests.exceptions.RequestException: API 요청 실패 시 발생.
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.diff"
    }
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.text
