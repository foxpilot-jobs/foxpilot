"""Compatibility command for profile creation."""

from career_agent.config import load_config
from career_agent.llm import LLMError
from career_agent.profile import create_profile, has_current_local_profile


def main() -> int:
    config = load_config()
    if has_current_local_profile(config):
        print(f"Career profile is current: {config.profile_path}")
        print("Skipping profile creation; the resume has not changed.")
        return 0
    print(f"Using LLM provider: {config.llm_provider} ({config.llm_model})")
    print("Reading resume and creating career profile...")
    try:
        create_profile(config)
    except (FileNotFoundError, LLMError, ValueError) as error:
        print(f"Profile creation failed: {error}")
        return 1
    print(f"Career profile created: {config.profile_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
