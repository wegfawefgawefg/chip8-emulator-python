import logging

from .quirks import load_quirks_profile_from_env
from .runtime import run_emulator


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    profile, quirks = load_quirks_profile_from_env()
    logging.getLogger(__name__).info("quirks profile: %s", profile)
    run_emulator(quirks=quirks)


if __name__ == "__main__":
    main()
