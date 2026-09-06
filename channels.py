from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Channel:
    link: str
    channel_id: int

    @property
    def display_name(self) -> str:
        return self.link.rstrip("/").rsplit("/", 1)[-1]


def load_channels(path: Path) -> list[Channel]:
    result: list[Channel] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            link, channel_id = (part.strip() for part in line.split("|", 1))
            result.append(Channel(link=link, channel_id=int(channel_id)))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid channels.txt line {line_number}: {raw_line}") from exc
    return result
