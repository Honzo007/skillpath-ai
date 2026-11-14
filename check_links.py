"""Check every learning-resource URL listed in data/roles.json."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROLES_FILE = Path(__file__).parent / "data" / "roles.json"
TIMEOUT_SECONDS = 8


def check_url(resource):
    request = Request(
        resource["url"],
        headers={"User-Agent": "SkillForgeLinkChecker/1.0"},
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
    except (TimeoutError, URLError, OSError) as error:
        return resource, f"error: {error}"

    return resource, None if status == 200 else f"HTTP {status}"


def main():
    with ROLES_FILE.open("r", encoding="utf-8") as roles_file:
        roles = json.load(roles_file)

    resources = [
        {"role": role_name, "skill": skill_name, **resource}
        for role_name, role in roles.items()
        for skill_name, skill in role.get("skills", {}).items()
        for resource in skill.get("resources", [])
        if resource.get("url")
    ]

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(check_url, resources))

    dead_links = [(resource, problem) for resource, problem in results if problem]
    print(f"Checked {len(resources)} resource URLs.")
    if not dead_links:
        print("No dead links found.")
        return

    print(f"Dead links ({len(dead_links)}):")
    for resource, problem in dead_links:
        print(
            f"- {resource['role']} / {resource['skill']} / "
            f"{resource.get('title', 'Untitled')}: {resource['url']} ({problem})"
        )


if __name__ == "__main__":
    main()