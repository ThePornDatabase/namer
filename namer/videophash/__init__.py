from dataclasses import dataclass
from typing import Optional, Union

import imagehash


__all__ = ['PerceptualHash', 'return_perceptual_hash']


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class PerceptualHash:
    duration: int
    phash: imagehash.ImageHash
    oshash: str


def return_perceptual_hash(duration: Union[float, int], phash: Optional[Union[str, imagehash.ImageHash]], file_oshash: str) -> PerceptualHash:
    output = PerceptualHash()
    output.duration = int(duration) if isinstance(duration, float) else duration
    if phash:
        output.phash = imagehash.hex_to_hash(phash) if isinstance(phash, str) else phash
    output.oshash = file_oshash

    return output
