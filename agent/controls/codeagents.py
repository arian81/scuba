from typing import Dict, Any, Union, Optional, Tuple
import requests
from dotenv import dotenv_values

config = dotenv_values(".env")
GITHUB_TOKEN = config["GITHUB"]  # Or directly set the token: 'your_personal_access_token'


def create_issue(repo_owner, repo_name, issue_title, issue_body):
    # Replace these variables with your details
    GITHUB_TOKEN = config["GITHUB"]
    REPO_OWNER = repo_owner
    REPO_NAME = repo_name
    ISSUE_TITLE = issue_title
    ISSUE_BODY = issue_body

    # GitHub API URL to create an issue
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues'

    # Headers with authentication
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Payload with issue details
    payload = {
        'title': ISSUE_TITLE,
        'body': ISSUE_BODY
    }

    # Make the request to create the issue
    response = requests.post(url, headers=headers, json=payload)

    # Check if the request was successful
    if response.status_code == 201:
        print('Issue created successfully:', response.json())
    else:
        print('Failed to create issue:', response.status_code, response.json())


def read_pull(url: str) -> str:
    """
        Retrieves data from a specific pull request in the given repository.
    """

    # Set headers for authorization
    headers_pr = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    # Set up headers with authorization
    headers_df = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.diff",
    }
    # Send the GET request to GitHub API
    response_pr = requests.get(url, headers=headers_pr)
    response_df = requests.get(url + ".diff", headers=headers_df)

    # Check for request errors
    if response_df.status_code != 200:
        raise Exception(f"Error fetching diff: {response_df.status_code} - {response_df.text}")
    if response_pr.status_code != 200:
        raise Exception(f"Error fetching PR: {response_pr.status_code} - {response_pr.text}")

    diff = response_df.text
    # pull_request_data = response_pr.json()
    # print("Pull Request Data:")
    # print(pull_request_data)
    # pull_request_data['difftext'] = diff
    print(diff)
    return diff


def post_comment_to_pr(owner: str, repo: str, pull_number: int, comment: str, commit_id: str, path: str,
                       start_line: int, start_side: str, line: int, side: str) -> None:
    """Posts a PR comment to github. Body parameters
Name, Type, Description
body string Required
The text of the review comment.

commit_id string Required
The SHA of the commit needing a comment. Not using the latest commit SHA may render your comment outdated if a subsequent commit modifies the line you specify as the position.

path string Required
The relative path to the file that necessitates a comment.

side string
In a split diff view, the side of the diff that the pull request's changes appear on. Can be LEFT or RIGHT. Use LEFT for deletions that appear in red. Use RIGHT for additions that appear in green or unchanged lines that appear in white and are shown for context. For a multi-line comment, side represents whether the last line of the comment range is a deletion or addition. For more information, see "Diff view options" in the GitHub Help documentation.

Can be one of: LEFT, RIGHT

line integer
Required unless using subject_type:file. The line of the blob in the pull request diff that the comment applies to. For a multi-line comment, the last line of the range that your comment applies to.

start_line integer
Required when using multi-line comments unless using in_reply_to. The start_line is the first line in the pull request diff that your multi-line comment applies to. To learn more about multi-line comments, see "Commenting on a pull request" in the GitHub Help documentation.

start_side string
Required when using multi-line comments unless using in_reply_to. The start_side is the starting side of the diff that the comment applies to. Can be LEFT or RIGHT. To learn more about multi-line comments, see "Commenting on a pull request" in the GitHub Help documentation. See side in this table for additional context.

Can be one of: LEFT, RIGHT, side

in_reply_to integer
The ID of the review comment to reply to. To find the ID of a review comment with "List review comments on a pull request". When specified, all parameters other than body in the request body are ignored.

subject_type string
The level at which the comment is targeted.

Can be one of: line, file
"""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_id}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    payload = {
        "owner": owner,
        "repo": repo,
        "commit_id": commit_id,
        "body": comment,
        "path": path,
        "position": line
    }

    response = requests.post(url, headers=headers, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")

    if response.status_code == 201:
        print("Comment posted successfully.")
    else:
        print(f"Error posting comment: {response.status_code} - {response.text}")


# Function to find the commit SHA based on code segment
def find_commit_sha_by_code_segment(owner: str, repo: str, pull_number: int, code_segment: str) -> Optional[
    tuple[str, int]]:
    """Finds the commit sha and line number associated with a code segment from diff.
    This can be used before post_comment_to_pr to identify the commit_id. """
    lines = code_segment.split('\n')
    for commit in get_pr_commits(owner, repo, pull_number):
        commit_sha = commit['sha']
        commit_files = get_commit_files(owner, repo, commit_sha)
        for file in commit_files['files']:
            if 'patch' not in file:
                continue
            patch = file['patch']
            lines_in_patch = patch.split('\n')
            for i, line in enumerate(lines_in_patch):
                if any(segment in line for segment in lines):
                    # Calculate the line number in the file
                    line_number = i + 1  # Line number in diff starts from 1
                    return commit_sha, line_number
    return None


# Function to get commits for a PR
def get_pr_commits(owner: str, repo: str, pull_number: int):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/commits"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error fetching commits: {response.status_code} - {response.text}")
    return response.json()


# Function to get the code of a commit
def get_commit_files(owner: str, repo: str, commit_sha: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error fetching commit details: {response.status_code} - {response.text}")
    return response.json()
