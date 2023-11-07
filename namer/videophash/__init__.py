from dataclasses import dataclass
from typing import Union

from namer.videophash.imagehash import hex_to_hash, ImageHash

__all__ = ['PerceptualHash', 'return_perceptual_hash']


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class PerceptualHash:
    duration: int
    phash: ImageHash
    oshash: str

    def to_dict(self):
        return {
            'duration': self.duration,
            'phash': str(self.phash),
            'oshash': self.oshash,
        }


def return_perceptual_hash(duration: Union[float, int], phash: Union[str, ImageHash], file_oshash: str) -> PerceptualHash:
    output = PerceptualHash()
    output.duration = int(duration) if isinstance(duration, float) else duration
    output.phash = hex_to_hash(phash) if isinstance(phash, str) else phash
    output.oshash = file_oshash

    return output
