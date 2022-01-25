def decodeChunkType(data, seek):
    return data[seek] & 63


def decodeChunkLength(data, seek):
    return (data[seek + 1] << 8) + data[seek + 2]


def decodeImageInfo(data):
    return (data[0] << 8) + data[1], (data[2] << 8) + data[3]
