from typing import Literal, Optional

import numpy
import scipy.fft
import scipy.fftpack
from PIL import Image

try:
    # enable numpy array typing (py3.7+)
    import numpy.typing

    NDArray = numpy.typing.NDArray[numpy.bool_]
except (AttributeError, ImportError):
    NDArray = list  # type: ignore


class ImageHash:
    """
    Hash encapsulation. Can be used for dictionary keys and comparisons.
    """

    def __init__(self, binary_array: NDArray) -> None:
        self.hash = binary_array

    def __str__(self) -> str:
        return _binary_array_to_hex(self.hash.flatten())

    def __repr__(self) -> str:
        return repr(self.hash)

    def __sub__(self, other: 'ImageHash') -> int:
        if other is None:
            raise TypeError('Other hash must not be None.')

        if self.hash.size != other.hash.size:
            raise TypeError('ImageHashes must be of the same shape.', self.hash.shape, other.hash.shape)

        return numpy.count_nonzero(self.hash.flatten() != other.hash.flatten())

    def __eq__(self, other: object) -> bool:
        if other is None:
            return False

        return numpy.array_equal(self.hash.flatten(), other.hash.flatten())  # type: ignore

    def __ne__(self, other: object) -> bool:
        if other is None:
            return False

        return not numpy.array_equal(self.hash.flatten(), other.hash.flatten())  # type: ignore

    def __hash__(self) -> int:
        # this returns an 8-bit integer, intentionally shortening the information
        return sum([2 ** (i % 8) for i, v in enumerate(self.hash.flatten()) if v])

    def __len__(self) -> int:
        # Returns the bit length of the hash
        return self.hash.size


def _binary_array_to_hex(arr):
    """
    internal function to make a hex string out of a binary array.
    """
    bit_string = ''.join(str(b) for b in 1 * arr.flatten())
    width = int(numpy.ceil(len(bit_string) / 4))
    return '{:0>{width}x}'.format(int(bit_string, 2), width=width)


def hex_to_hash(hex_str: str) -> ImageHash:
    """
    Convert a stored hash (hex, as retrieved from str(Imagehash))
    back to an Imagehash object.

    Notes:
    1. This algorithm assumes all hashes are either
            bidimensional arrays with dimensions hash_size * hash_size,
            or one-dimensional arrays with dimensions binbits * 14.
    2. This algorithm does not work for hash_size < 2.
    """
    hash_size = int(numpy.sqrt(len(hex_str) * 4))
    # assert hash_size == numpy.sqrt(len(hex_str)*4)
    binary_array = '{:0>{width}b}'.format(int(hex_str, 16), width=hash_size * hash_size)
    bit_rows = [binary_array[i : i + hash_size] for i in range(0, len(binary_array), hash_size)]
    hash_array = numpy.array([[bool(int(d)) for d in row] for row in bit_rows])
    return ImageHash(hash_array)


def phash(image: Image.Image, hash_size=8, high_freq_factor=4, resample: Literal[0, 1, 2, 3, 4, 5] = Image.Resampling.LANCZOS) -> Optional[ImageHash]:  # type: ignore
    if hash_size < 2:
        raise ValueError('Hash size must be greater than or equal to 2')

    img_size = hash_size * high_freq_factor
    image = image.resize((img_size, img_size), resample).convert('L')
    pixels = numpy.asarray(image)

    dct = scipy.fft.dct(scipy.fft.dct(pixels, axis=0), axis=1)
    dct_low_freq = dct[:hash_size, :hash_size]  # type: ignore
    med = numpy.median(dct_low_freq)
    diff = dct_low_freq > med

    return ImageHash(diff)
