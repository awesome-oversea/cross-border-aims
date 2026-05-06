import json
import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download


def parse_env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def safe_repo_dir(root: Path, repo_id: str) -> Path:
    return root / repo_id.replace("/", "__")


def download_repo(repo_id: str, *, cache_dir: Path | None = None, local_dir: Path | None = None) -> dict[str, str]:
    kwargs: dict[str, object] = {"repo_id": repo_id}
    if cache_dir is not None:
        kwargs["cache_dir"] = str(cache_dir)
    if local_dir is not None:
        local_dir.mkdir(parents=True, exist_ok=True)
        kwargs["local_dir"] = str(local_dir)
        kwargs["local_dir_use_symlinks"] = False

    resolved_path = snapshot_download(**kwargs)
    return {
        "repo": repo_id,
        "path": str(local_dir if local_dir is not None else Path(resolved_path)),
    }


def main() -> int:
    hf_home = Path(os.getenv("HF_HOME", "/cache/huggingface"))
    whisper_root = Path(os.getenv("WHISPER_CACHE_DIR", "/cache/whisper"))
    rerank_repos = parse_env_list("AIMS_LOCAL_RERANK_REPO")
    whisper_repos = parse_env_list("AIMS_LOCAL_WHISPER_REPO")

    hf_home.mkdir(parents=True, exist_ok=True)
    whisper_root.mkdir(parents=True, exist_ok=True)

    downloaded: list[dict[str, str]] = []

    for repo_id in rerank_repos:
        downloaded.append(download_repo(repo_id, cache_dir=hf_home))

    for repo_id in whisper_repos:
        downloaded.append(
            download_repo(
                repo_id,
                cache_dir=hf_home,
                local_dir=safe_repo_dir(whisper_root, repo_id),
            )
        )

    payload = {
        "hf_home": str(hf_home),
        "whisper_root": str(whisper_root),
        "downloaded": downloaded,
    }
    json.dump(payload, sys.stdout, ensure_ascii=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
