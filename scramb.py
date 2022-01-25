#!/usr/bin/python3
from PIL import Image, ImageDraw, ImageChops
import os
import math
from io import BytesIO
import getopt
import pickle
import json
import hashlib
from getpass import getpass
import sys
import importlib
import subprocess
from config import *
from decode_func import *
from utils import *
from Image import *

# check if PIL / Pillow is installed
# be helpful and try to install it if it is not present (for our Windows Users out there :-D )
try:
    importlib.import_module("PIL")
except ImportError:
    print("PIL / Pillow module is not installed with your Python installation!")
    print("")
    print("You can install it yourself or scramb.py can do this for you.")
    print("Do it yourself with: pip install Pillow          on Linux")
    print("                     pip.exe install Pillow      on Windows")
    print("")
    answer = input("Do you want scramb.py to install it for you now? [y/n]")
    if answer == "y":
        # from https://pip.pypa.io/en/latest/user_guide/#using-pip-from-your-program
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'Pillow'])
        print("")
        print("Installation code done")
        input("Please press Enter to leave and then restart scramb.py as you just did before ...")
        sys.exit()


def serialize(image, byteArray) -> Image:
    imageSpaceWidth = math.ceil(image.width / 8)
    imageSpaceHeight = math.ceil(image.height / 8)

    # lines on top, bottom ... etc
    top = 1
    bottom = 0
    left = 0
    right = 0

    # direction of space search
    direction = 0

    # space in byte
    freeSpace = 0
    neededSpace = len(byteArray)

    # fullX = no of blocks per line or column
    fullLine = 0
    fullColumn = 0

    while freeSpace < neededSpace:
        if direction == 0:  # right
            top = top + 1
        elif direction == 1:  # down
            if right == 0:
                right = 2
            else:
                right = right + 1
        elif direction == 2:  # left
            if bottom == 0:
                bottom = 2
            else:
                bottom = bottom + 1
        elif direction == 3:  # up
            if left == 0:
                left = 2
            else:
                left = left + 1

        # calculate space
        fullLine = imageSpaceWidth + left + right
        fullColumn = imageSpaceHeight + bottom + top
        freeBlocks = (fullLine * top + fullLine * bottom + imageSpaceHeight * (left + right))

        freeSpace = freeBlocks  # HEADER_VERSION_ENCODER 1: a block equals a byte

        # add safe zone (8 pixel distance between data and image
        freeSpace = freeSpace - imageSpaceWidth
        if right > 0:
            freeSpace = freeSpace - imageSpaceHeight
        elif left > 0:
            freeSpace = freeSpace - imageSpaceHeight
        elif bottom > 0:
            freeSpace = freeSpace - imageSpaceWidth

        direction += 1
        if direction == 4:
            direction = 0

    croppedim = image.crop((-8 * left, -8 * top, imageSpaceWidth * 8 + 8 * right, imageSpaceHeight * 8 + 8 * bottom))

    draw = ImageDraw.Draw(croppedim)

    # positions in blocks
    posX = 0
    posY = 0
    # margin from edge of image in blocks
    marginTop = 0
    marginLeft = 0
    marginBottom = 0
    marginRight = 0
    direction = 0
    # position in byteArray
    i = 0
    while i < len(byteArray):

        drawByte(draw, byteArray[i], posX * 8, posY * 8)
        i += 1

        if direction == 0:
            posX = posX + 1
        elif posX + 1 < fullLine - marginRight:
            direction = 1
            posY = posY + 1
            marginTop = marginTop + 1
        elif direction == 1:
            posY = posY + 1
        elif posY + 1 < fullColumn - marginBottom:
            direction = 2
            posX = posX - 1
            marginRight = marginRight + 1
        elif direction == 2:
            posX = posX - 1
        elif posX > marginLeft:
            direction = 3
            posY = posY - 1
            marginBottom = marginBottom + 1
        elif direction == 3 and posY > marginTop:
            posY = posY - 1
        else:
            direction = 0
            posX = posX + 1
            marginLeft = marginLeft + 1

    return croppedim, left * 8, top * 8


def deserialize(image, length):
    byteArray = []
    posX = 0
    posY = 0
    marginTop = 0
    marginLeft = 0
    marginBottom = 0
    marginRight = 0
    direction = 0
    i = 0
    # TODO %8 images.. no more needed, since scrambled images always are %8=0
    ## coorect /8 images
    fullLine = math.floor(image.width / 8)
    fullColumn = math.floor(image.height / 8)

    # offset in blocks for the image data (image starts at (offsetX*8, offsetY*8) )
    offsetX = 0
    offsetY = 2

    while i < length:

        byte1 = readByte(image, posX * 8, posY * 8)
        byteArray.append(byte1)
        i = i + 1

        if direction == 0:  # right
            if posX + 1 < fullLine - marginRight:
                posX = posX + 1
            else:
                direction = 1
                posY = posY + 1
                marginTop = marginTop + 1
        elif direction == 1:  # down
            if posY + 1 < fullColumn - marginBottom:
                posY = posY + 1
            else:
                direction = 2
                posX = posX - 1
                marginRight = marginRight + 1
        elif direction == 2:  # left
            if posX > marginLeft:
                posX = posX - 1
            else:
                direction = 3
                posY = posY - 1
                marginBottom = marginBottom + 1
                offsetX = offsetX + 1
        elif direction == 3:  # up
            if posY > marginTop:
                posY = posY - 1
            else:
                direction = 0
                posX = posX + 1
                marginLeft = marginLeft + 1
                offsetY = offsetY + 1
    if offsetX > 0:
        offsetX = offsetX + 1
    return byteArray, offsetX, offsetY


def createChunk(data, chunkType, mode=0, eec=0):
    if len(data) > pow(2, 16):
        print("Chunk is bigger than allowed. Panic")
        sys.exit(3)

    loByte = len(data) & 255
    hiByte = len(data) >> 8
    data.insert(0, chunkType)
    data.insert(1, hiByte)
    data.insert(2, loByte)
    return data


def getChunkData(data, seek):
    length = decodeChunkLength(data, seek)
    return data[seek + 3:seek + 3 + length]


# from https://stackoverflow.com/questions/19140589/linear-congruential-generator-in-python

def lcg(x, a, c, m):
    while True:
        x = (a * x + c) % m
        yield x


def random_uniform_sample(n, interval, seed=0):
    a, c, m = 1103515245, 12345, 2 ** 31
    bsdrand = lcg(seed, a, c, m)

    lower, upper = interval[0], interval[1]
    sample = []

    for i in range(n):
        observation = (upper - lower) * (next(bsdrand) / (2 ** 31 - 1)) + lower
        sample.append(round(observation))

    return sample


def turnBlockInMatrix(matrix, x, y, clockwise=True):
    if (x + 1 < len(matrix)) and (y + 1 < len(matrix[x - 1])):
        if (matrix[x][y] is not None) and (matrix[x + 1][y] is not None) and (matrix[x][y + 1] is not None) and (
                matrix[x + 1][y + 1] is not None):
            #    0, 0   +1, 0
            #
            #    0,+1   +1.+1
            if clockwise:
                t = matrix[x][y]
                matrix[x][y] = matrix[x][y + 1]
                matrix[x][y + 1] = matrix[x + 1][y + 1]
                matrix[x + 1][y + 1] = matrix[x + 1][y]
                matrix[x + 1][y] = t
            else:
                t = matrix[x + 1][y]
                matrix[x + 1][y] = matrix[x + 1][y + 1]
                matrix[x + 1][y + 1] = matrix[x][y + 1]
                matrix[x][y + 1] = matrix[x][y]
                matrix[x][y] = t


def mixSubstitutionMatrix(matrix, seed=0, percent_Of_Turns=20):
    print("calculating subseeds...")
    print("seed ", seed)
    subSeeds = random_uniform_sample(3, [0, 1000], seed=seed)

    size = len(matrix) * len(matrix[0])
    print("blocks ", size)

    numberOfTurns = round(size * percent_Of_Turns * 0.01)
    print("number of turns", numberOfTurns)

    xPositions = random_uniform_sample(numberOfTurns, [0, len(matrix) - 1], seed=seed + subSeeds[0])
    yPositions = random_uniform_sample(numberOfTurns, [0, len(matrix[0]) - 1], seed=seed + subSeeds[1])
    reverse = random_uniform_sample(numberOfTurns, [0, 1], seed=seed + subSeeds[2])

    for i in range(numberOfTurns):
        turnBlockInMatrix(matrix, xPositions[i], yPositions[i], clockwise=reverse[i])
    return matrix


def mixSubstitutionMap_heavy(substitutionMap, seed=0, rounds=4):
    # total mixed
    randnumbers = random_uniform_sample(len(substitutionMap) * rounds, [0, len(substitutionMap) - 1], seed=seed)
    for i in range(len(randnumbers)):
        value = substitutionMap.pop(randnumbers[i])
        substitutionMap.append(value)
    return substitutionMap


def mixSubstitutionMap_medium(substitutionMap, seed=0, distance=10, rounds=1):
    # slightly mixed
    # rounds = 1
    randnumbers = random_uniform_sample(len(substitutionMap) * rounds, [distance * -1, distance], seed=seed)
    for r in range(rounds):
        for i in range(len(substitutionMap)):
            value = substitutionMap.pop(i)
            substitutionMap.insert(i + randnumbers[i + len(substitutionMap) * r], value)

    return substitutionMap


def createJPEGSampleInMemory(image, quality=80):
    memoryFile = BytesIO()
    image.save(memoryFile, format='JPEG', quality=quality)

    return Image.open(memoryFile)


def transferBlocks(sourceImage, sourceMaskImage, targetImage, targetMaskImage):
    if countBlocksOfMask(sourceMaskImage) < countBlocksOfMask(targetMaskImage):
        blocksToCopy = countBlocksOfMask(sourceMaskImage)
    else:
        blocksToCopy = countBlocksOfMask(targetMaskImage)
    sx = -1
    sy = 0
    tx = -1
    ty = 0
    copiedBlocks = 0
    while copiedBlocks < blocksToCopy:
        while True:
            sx = sx + 1
            if sx == sourceMaskImage.width:
                sy = sy + 1
                sx = 0
            if sourceMaskImage.getpixel((sx, sy)) > 0:
                break

        while True:
            tx = tx + 1
            if tx == targetMaskImage.width:
                ty = ty + 1
                tx = 0
            if targetMaskImage.getpixel((tx, ty)) > 0:
                break

        copyBlock(sourceImage, targetImage, sx * 8, sy * 8, tx * 8, ty * 8)
        copiedBlocks = copiedBlocks + 1


# check if LOGO constant exists in case the user deletes it for security
def placeLogo(image, xpos, ypos):
    if "LOGO" in globals():
        logoData = pickle.loads(bytes(LOGO))
        logoFile = BytesIO(bytearray(logoData))
        logoImage = Image.open(logoFile)
        print("Placing Logo at ", xpos + 1, ypos + 1)
        image.paste(logoImage, (xpos + 1, ypos + 1), mask=None)
    return image


def resizeQuads(image):
    # shrinks an image to 50% (used for images that where blown up to 200%
    # ignores 50% of pixels in a way that it does not use the outermost pixels of an 16x16 block
    # which mostly will have compression artifacts (~ are darker than their neighbour
    #
    # . . . . . . . . . . . . . . . .
    # . a . a . a . a . a . a . a a .
    # . . . . . . . . . . . . . . . .
    # . a . a . a . a . a . a . a a .
    # . . . . . . . . . . . . . . . .    =>   a a a a a a a a
    # . a . a . a . a . a . a . a a .         a a a a a a a a
    # . . . . . . . . . . . . . . . .         a a a a a a a a
    # . a . a . a . a . a . a . a a .         a a a a a a a a
    # . . . . . . . . . . . . . . . .         a a a a a a a a
    # . a . a . a . a . a . a . a a .         a a a a a a a a
    # . . . . . . . . . . . . . . . .         a a a a a a a a
    # . a . a . a . a . a . a . a a .         a a a a a a a a
    # . . . . . . . . . . . . . . . .
    # . a . a . a . a . a . a . a a .
    # . a . a . a . a . a . a . a a .
    # . . . . . . . . . . . . . . . .

    resultim = image.resize((int(image.width / 2), int(image.height / 2)), resample=Image.NEAREST)

    w = [1, 1, 1, 1, 1, 1, 1, 0]
    v = [1, 1, 1, 1, 1, 1, 1, 0]

    for y in range(resultim.height):
        for x in range(resultim.width):
            r, g, b = image.getpixel((x * 2 + v[x % 8], y * 2 + w[y % 8]))
            resultim.putpixel((x, y), (r, g, b))
    return resultim


def calculateChecksum(data):
    check_sum = 0
    for entry in data:
        check_sum = (check_sum & 255) ^ (entry & 255)
    return check_sum


def calculatePasswordSeed(password):
    pw_bytes = password.encode('utf-8')
    hashed_password = hashlib.sha256(pw_bytes).hexdigest()
    password_Seed = int(hashed_password, 16)
    password_Seed = password_Seed % 100000000000000000
    return password_Seed
