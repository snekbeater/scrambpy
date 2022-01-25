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

# Configuration
HEADER_VERSION_MAGIC_NUMBER = 42
# Type IDs:
CHUNK_TYPE_RAW = 0  # raw data, not more specified
CHUNK_TYPE_TEXT = 1  # text
CHUNK_TYPE_PNG = 2  # png
CHUNK_TYPE_IMAGE_INFO = 3  # image info
CHUNK_TYPE_SCRAMBLER_PARAMETERS = 4  # scrambler parameters
#      ...
CHUNK_TYPE_EXTENDED_HEADER = 64  # extended header (more bytes follow e.g. bigger size, other types, future stuff)

SCRAMBLERPARAMETERSDATAFIELD_BLOWUP = 'b'
SCRAMBLERPARAMETERSDATAFIELD_SCRAMBLER = 'a'  # a like algorithm
SCRAMBLERPARAMETERSDATAFIELD_SEED = 's'
SCRAMBLERPARAMETERSDATAFIELD_ROUNDS = 'r'
SCRAMBLERPARAMETERSDATAFIELD_DISTANCE = 'd'
SCRAMBLERPARAMETERSDATAFIELD_PERCENTAGEOFTURNS = 't'
SCRAMBLERPARAMETERSDATAFIELD_PASSWORDUSED = 'p'
SCRAMBLERPARAMETERSDATAFIELD_PATCHIMAGE = 'i'
#
STANDARD_JPEG_QUALITY = 100  # standard save quality

# the small "Scrambled with scramb.py"-Logo as a png file
# If you do not trust encoded stuff in code you run, you can erase this constant.
# You then just do not get a logo anymore
LOGO = b"\x80\x03C\x92\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00]\x00\x00\x00\x06\x01\x00\x00\x00\x00\x89C\xafZ\x00\x00\x00YIDATx\x9c\x01N\x00\xb1\xff\x00`\x00\x02\x10\x08\x02\x10\x00\x00\x02\x07(\x020\x00\x00\x00\x00\xfe\x80\x00\x00\x00\xfd\x80\x02\xb3l\xf1\x820\xaaH3l\xf1\x80\x00\x04\xe1\xff\xb7\xc3\x10\x00\xbc\x11\xd6\xb7\xc3\x8c\x02p\x08\x00\xff\x00\xa8\x00\xd0\x08\x00\xfd\x00\x02\xcf\xfc\x01?\xf0\x00\xc0O\xfc\x01P\x10S\xe2\x1a'o\x8da/\x00\x00\x00\x00IEND\xaeB`\x82q\x00."
HEADER_VERSION_ENCODER_MIN = 1
HEADER_VERSION_ENCODER = 2
VERSION = "0.3.1"

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


def calculateResidual(img1, img2):
    residue = 0
    pixels = 0
    diff = ImageChops.difference(img1, img2)
    for y in range(diff.height):
        for x in range(diff.width):
            r, g, b = diff.getpixel((x, y))
            residue = residue + r + g + b
            pixels = pixels + 3
    return residue / pixels


def calculateResidualFast(img1, img2):
    residue = 0
    pixels = 0

    diff = ImageChops.difference(img1, img2)

    diff = diff.resize((math.floor(diff.width / 10), math.floor(diff.height / 10)))

    for y in range(diff.height):
        for x in range(diff.width):
            r, g, b = diff.getpixel((x, y))
            residue = residue + r + g + b
            pixels = pixels + 3

    return residue / pixels


def calculateSubMapScramblePercent(submap_first, submap_second):
    same = 0
    for i in range(len(submap_first)):
        if submap_first[i] == submap_second[i]:
            same = same + 1
    return same / len(submap_first)


# draws theByte at pixel x_position, y_position of draw object of an image
def drawByte(draw, theByte, x_position, y_position):
    for y in range(2):
        for x in range(2):
            rectDuo = theByte & 3
            luma = rectDuo * 85  # four possible values between 0 and 255
            draw.rectangle(
                ((x * 4) + x_position, (y * 4) + y_position, (x * 4) + x_position + 3, (y * 4) + y_position + 3),
                fill=(luma, luma, luma), outline=None)
            theByte = theByte >> 2


def readByte(image, x_position, y_position):
    theByte = 0
    for y in (1, 0):
        for x in (1, 0):
            values = []
            for suby in range(4):
                for subx in range(4):
                    r, g, b = image.getpixel((x_position + x * 4 + subx, y_position + y * 4 + suby))
                    values.extend([r, g, b])
            valueSum = 0
            for value in values:
                valueSum = valueSum + value
            valueMedian = valueSum / len(values)
            rectDuo = round(valueMedian / 85)  # four possible values between 0 and 255
            theByte = theByte | rectDuo
            if x + y > 0:  # last round no shift at the end
                theByte = theByte << 2
    return theByte


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


def decodeChunkType(data, seek):
    return data[seek] & 63


def decodeChunkLength(data, seek):
    return (data[seek + 1] << 8) + data[seek + 2]


def decodeImageInfo(data):
    return (data[0] << 8) + data[1], (data[2] << 8) + data[3]


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


def copyBlock(imageSource, imageDest, xposSource, yposSource, xposDest, yposDest):
    block = imageSource.crop((xposSource, yposSource, xposSource + 8, yposSource + 8))
    imageDest.paste(block, (xposDest, yposDest), mask=None)


def createImageInfo(image):
    data = []
    loByte = image.width & 255
    hiByte = image.width >> 8
    data.append(hiByte)
    data.append(loByte)
    loByte = image.height & 255
    hiByte = image.height >> 8
    data.append(hiByte)
    data.append(loByte)
    return data


def switchBlocks(image, xpos1, ypos1, xpos2, ypos2):
    block1 = image.crop((xpos1, ypos1, xpos1 + 8, ypos1 + 8))
    block2 = image.crop((xpos2, ypos2, xpos2 + 8, ypos2 + 8))
    image.paste(block1, (xpos2, ypos2), mask=None)
    image.paste(block2, (xpos1, ypos1), mask=None)


def createSubstitutionMapFromMask(mask_image):
    serialPos = 0
    substitutionMap = []
    for y in range(mask_image.height):
        for x in range(mask_image.width):
            luma = mask_image.getpixel((x, y))
            if luma > 0:
                substitutionMap.append(serialPos)
            serialPos = serialPos + 1
    return substitutionMap


def createSubstitutionMatrixFromMask(mask_image):
    matrix = [None] * mask_image.width
    for y in range(mask_image.width):
        matrix[y] = [None] * mask_image.height
    for y in range(mask_image.height):
        for x in range(mask_image.width):
            luma = mask_image.getpixel((x, y))
            if luma > 0:
                matrix[x][y] = (x, y)
    return matrix


def scrambleBlocksOfImageWithMatrix(matrix, image, reverse=False):
    originalImage = image.copy()

    for y in range(len(matrix[0])):
        for x in range(len(matrix)):
            if matrix[x][y] is not None:
                if not reverse:
                    copyBlock(originalImage, image, x * 8, y * 8, matrix[x][y][0] * 8, matrix[x][y][1] * 8)
                else:
                    copyBlock(originalImage, image, matrix[x][y][0] * 8, matrix[x][y][1] * 8, x * 8, y * 8)

    return image


def scrambleBlocksOfImage(substitutionMapSource, substitutionMap, image, reverse=False):
    # image must have %8=0 pixel width/height at this point!
    # mask and thus subMap must fit to that!
    for ii in range(len(substitutionMap)):
        blocksWidth = math.floor(image.width / 8)
        if reverse:
            i = len(substitutionMap) - 1 - ii
        else:
            i = ii
        x1 = substitutionMapSource[i] % blocksWidth
        y1 = math.floor(substitutionMapSource[i] / blocksWidth)
        x2 = substitutionMap[i] % blocksWidth
        y2 = math.floor(substitutionMap[i] / blocksWidth)
        switchBlocks(image, x1 * 8, y1 * 8, x2 * 8, y2 * 8)
    return image


def countBlocksOfMask(mask_image):
    numberOfBlocks = 0
    for y in range(mask_image.height):
        for x in range(mask_image.width):
            luma = mask_image.getpixel((x, y))
            if luma > 0:
                numberOfBlocks = numberOfBlocks + 1
    return numberOfBlocks


print("scramb.py Image Scrambler in Python")
print("Version ", VERSION, " Copyright (C) 2022 by snekbeater")
print("For updates see git repo at https://github.com/snekbeater/scrambpy")
print("    This program comes with ABSOLUTELY NO WARRANTY.")
print("    This is free software, and you are welcome to redistribute it")
print("    under certain conditions; see code for details.")

input_file_name = ""
mask_file_name = ""
out_put_file_name = ""
scramblerParameters = [0, -1, -1]
scrambler = "medium"
isLogoEnabled = True
blowup = False
password = ""
isPasswordSet = False
passwordSeed = 0
hidePasswordUse = False
embeddedText = ""
isSilent = False
outputQuality = STANDARD_JPEG_QUALITY
isScrambleModeSelected = False
overwrite = False
disguise_filename = ""
isDisguiseEnabled = False


def printHelp():
    print("")
    print("Scramble:")
    print("    scramb.py -i <inputfile> [-m <mask.png/.jpg>] -o <outputfile.jpg>  [OPTIONS]")
    print("        You must use -m and/or -s for scramb.py to detect that you want to scramble")
    print("")
    print("Descramble:")
    print("    scramb.py <inputfile.jpg>                        (also usable for drag & drop)")
    print("    scramb.py -i <inputfile.jpg> -o <outputfile.jpg>")
    print("")
    print("Calculate Residue:")
    print("    scramb.py -r <imagefile1.jpg> <imagefile2.jpg>")
    print("")
    print("Options")
    print("    -x <number>   specific parameter for the chosen scrambler")
    print("    -y <number>   specific parameter for the chosen scrambler")
    print("    -z <number>   specific parameter for the chosen scrambler")
    print("    -s <scrambler>")
    print("                  matrix   x=seed y=turn percentage")
    print("                  medium   x=seed y=rounds z=distance")
    print("                  heavy    x=seed y=rounds")
    print("    -2            blowup image by 2x")
    print("    --quality     JPEG Output Quality 0-100, 100=best, default=100")
    print("    --no-logo     do not include Logo in Image")
    print("    -t \"<text>\"   embed text to show when descrambling (max. 400 chars)")
    print("    --silent      do not pause on descramble for displaying text")
    print("    -p            scramble with password (ask for it)")
    print("    --password=<password>")
    print("                  scramble with <password> (caution: it's then in your console history...)")
    print("    --stealth     hide password use from generated image")
    print("                  You must run descrambling with -p or --password option then!")
    print("    --overwrite   Overwrite output file when it exists")
    print("    -d <disguiseimage.jpg>")
    print("                  Enables patch mode with a disguise image for scramble and descramble")
    print("                  When scrambling: This will output a patch image as -o and this -d image")
    print("                           is used as a thumbnail (the disguise image)")
    print("                  When descrambling: This is the disguise image that is patched with")
    print("                           the patch image provided by -i")


if len(sys.argv) == 1:
    printHelp()
    sys.exit(2)

try:
    # TODO all ops work & present in help?
    opts, args = getopt.getopt(sys.argv[1:], "?h2i:s:m:o:d:r:x:y:z:t:p",
                               ["no-logo", "password=", "stealth", "silent", "quality=", "overwrite"])
except getopt.GetoptError:
    printHelp()
    sys.exit(2)

for opt, arg in opts:
    if (opt == '-h') or (opt == '-?'):
        printHelp()
        sys.exit(2)
    elif opt == '-t':
        embeddedText = str(arg)
    elif opt == '-x':
        scramblerParameters[0] = int(arg)
    elif opt == '-y':
        scramblerParameters[1] = int(arg)
    elif opt == '-z':
        scramblerParameters[2] = int(arg)
    elif opt == '-s':
        scrambler = arg
        isScrambleModeSelected = True
    elif opt == '-2':
        blowup = True
    elif opt == '--overwrite':
        overwrite = True
    elif opt == '--silent':
        isSilent = True
    elif opt == '--quality':
        outputQuality = int(arg)
    elif opt == '-m':
        mask_file_name = arg
        isScrambleModeSelected = True
    elif opt in "-i":
        input_file_name = arg
    elif opt in "-o":
        out_put_file_name = arg
    elif opt in "-d":
        disguise_filename = arg
        isDisguiseEnabled = True
    elif opt in "-p":
        isPasswordSet = True
    elif opt in "--password":
        password = arg
        isPasswordSet = True
    elif opt in "--stealth":
        hidePasswordUse = True
    elif opt in "--no-logo":
        isLogoEnabled = False
    elif opt in "-r":
        filename1 = arg
        filename2 = args[0]
        img1 = Image.open(filename1)
        img2 = Image.open(filename2)
        # finding difference
        diff = ImageChops.difference(img1, img2)
        # showing the difference
        residue = calculateResidual(img1, img2)
        print("Residual: ", residue)
        diff.show()
        sys.exit()

if (isScrambleModeSelected and (len(args) > 0)) or ((not isScrambleModeSelected) and (len(args) > 1)):
    printHelp()
    sys.exit(2)

if (not isScrambleModeSelected) and (len(args) == 1):
    # descramble mode with just filename as parameter (=e.g. by drag & drop an image)
    input_file_name = args[0]
    out_put_file_name = os.path.splitext(input_file_name)[0] + '_descrambled.jpg'

print("Input   : ", input_file_name)
if isDisguiseEnabled:
    print("Disguise: ", disguise_filename)
print("Output  : ", out_put_file_name)

if overwrite:
    print("Overwrite enabled")

elif (not overwrite) and os.path.exists(out_put_file_name):
    answer = input("Overwrite existing output file ?[y/n]")
elif not answer == "y":
    sys.exit()

if isPasswordSet and (password == ""):
    password = getpass("Enter Password: ")

elif isPasswordSet:
    passwordSeed = calculatePasswordSeed(password)

if isScrambleModeSelected:
    print("Mode: Scramble")

    im = Image.open(input_file_name)

    print("Image size ", im.size)

    if not im.mode == "RGB":
        print("Image mode is", im.mode, ", converting it to RGB")
        im = im.convert("RGB")

    mybytes = []

    # TODO: only do this at one place
    if not isDisguiseEnabled:
        mybytes = mybytes + createChunk(createImageInfo(im), 3)

    maskDimensions = (int(math.ceil(im.width / 8.0)), int(math.ceil(im.height / 8.0)))

    if os.path.exists(mask_file_name):
        pngim = Image.open(mask_file_name)
    else:
        # no png specified, use white image mask (which equals full image will be scrambled)
        mode = '1'
        color = (1)
        pngim = Image.new(mode, maskDimensions, color)

    if not pngim.size == maskDimensions:
        pngim = pngim.resize(maskDimensions, resample=Image.NEAREST)
    print("Mask dimensions", pngim.size)
    # reduce to 1 bpp
    pngim = pngim.convert("1", dither=False)

    memoryFile = BytesIO()
    pngim.save(memoryFile, format='PNG', optimize=True, icc_profile=None)

    chunkbytes = createChunk(list(memoryFile.getvalue()), 2)
    print("Mask size:", memoryFile.getbuffer().nbytes, "bytes")
    mybytes = mybytes + chunkbytes

    # padding for testing
    '''
    myrawdata = []
    for b in range(65000):
        myrawdata.append(random.randint(0,255))
    chunkbytes = createChunk(myrawdata,0)
    mybytes = mybytes + chunkbytes
    myrawdata = []
    for b in range(75000):
        myrawdata.append(random.randint(0,255))
    chunkbytes = createChunk(myrawdata,0)
    mybytes = mybytes + chunkbytes
    '''

    # encode Text
    if not embeddedText == "" and len(embeddedText) < 400:
        print("Encoding user text")
        myrawdata = list(bytearray(embeddedText, "utf-8"))
        chunkbytes = createChunk(myrawdata, CHUNK_TYPE_TEXT)
        mybytes = mybytes + chunkbytes
    else:
        print("Text too long")
        sys.exit(3)

    scramblerParametersForDataField = {SCRAMBLERPARAMETERSDATAFIELD_SCRAMBLER: scrambler}

    if isPasswordSet and not hidePasswordUse:
        scramblerParametersForDataField[SCRAMBLERPARAMETERSDATAFIELD_PASSWORDUSED] = True

    originalWidth, originalHeight = im.size
    if (originalWidth % 8 > 0) or (originalHeight % 8 > 0):
        # correct % 8 > 0 images
        originalIm = im.copy()
        newWidth = int(math.ceil(originalWidth / 8) * 8)
        newHeight = int(math.ceil(originalHeight / 8) * 8)

        im = im.crop((0, 0, newWidth, newHeight))

        overscanColumns = 8 - originalWidth % 8
        if overscanColumns < 8:
            print("Filling right side overscan")
            rightStrip = originalIm.copy().crop((originalIm.width - 1, 0, originalIm.width, originalIm.height))
            for i in range(overscanColumns):
                im.paste(rightStrip, (originalIm.width + i, 0), mask=None)
        overscanLines = 8 - originalIm.height % 8
        if overscanLines < 8:
            print("Filling bottom overscan")
            bottomStrip = originalIm.copy().crop((0, originalIm.height - 1, originalIm.width, originalIm.height))
            for i in range(overscanLines):
                im.paste(bottomStrip, (0, originalIm.height + i), mask=None)

    if isDisguiseEnabled:
        print("Disguise Enabled")
        numberOfBlocksOfMask = countBlocksOfMask(pngim)
        print("Extracting", numberOfBlocksOfMask, " Blocks of input image")

        imDisguise = Image.open(disguise_filename)
        print("Disguise Image size ", imDisguise.size)
        if not imDisguise.mode == "RGB":
            print("Image mode is", imDisguise.mode, ", converting it to RGB")
            imDisguise = imDisguise.convert("RGB")
        THUMB_SIDELENGTH = 200  # must be %8=0 and /2%8=0 for blowup !!

        # portrait or landscape?
        if imDisguise.width < imDisguise.height:
            # portrait
            thumb = imDisguise.resize(
                (int(round((imDisguise.width * THUMB_SIDELENGTH) / imDisguise.height)), THUMB_SIDELENGTH),
                resample=Image.BICUBIC)
        else:
            # landscape
            thumb = imDisguise.resize(
                (THUMB_SIDELENGTH, int(round((imDisguise.height * THUMB_SIDELENGTH) / imDisguise.width))),
                resample=Image.BICUBIC)

        if blowup:
            THUMB_SIDELENGTH = int(THUMB_SIDELENGTH / 2)

        # print("Thumb space: ",(THUMB_SIDELENGTH + 8) / 8, (THUMB_SIDELENGTH + 8) / 8)
        neededBlocks = math.ceil((THUMB_SIDELENGTH + 8) / 8) * ((THUMB_SIDELENGTH + 8) / 8) + numberOfBlocksOfMask
        print(neededBlocks)
        side = math.ceil(math.sqrt(neededBlocks))
        print(side)
        print("Patch image size:", side * 8, "x", side * 8)
        patchImage = Image.new('RGB', (side * 8, side * 8), (0, 0, 0))

        # patchImage.paste(thumb,(0, 0),mask=None)
        # patchImage.show()
        patchMaskImage = Image.new('1', (side, side), (1))

        patchMaskDraw = ImageDraw.Draw(patchMaskImage)
        # TODO is -1 correct? there was a 16px safe zone and the reason was unclear
        patchMaskDraw.rectangle((0, 0, (THUMB_SIDELENGTH + 8) / 8 - 1, (THUMB_SIDELENGTH + 8) / 8 - 1), fill=(0))
        # patchMaskImage.show()

        memoryFile = BytesIO()
        patchMaskImage.save(memoryFile, format='PNG', optimize=True, icc_profile=None)

        chunkbytes = createChunk(list(memoryFile.getvalue()), 2)
        print("Mask size:", memoryFile.getbuffer().nbytes, "bytes")
        mybytes = mybytes + chunkbytes

    if scrambler == "matrix":
        print("Using scrambler: matrix")

        seed = scramblerParameters[0]
        if scramblerParameters[1] > 0:
            percentOfTurns = scramblerParameters[1]
        else:
            percentOfTurns = 20

        print("Turns: ", percentOfTurns, "%")

        substitutionMatrix = createSubstitutionMatrixFromMask(pngim)

        print("mixing..")
        mixSubstitutionMatrix(substitutionMatrix, seed=seed + passwordSeed, percent_Of_Turns=percentOfTurns)

        print("scrambling image..")
        im = scrambleBlocksOfImageWithMatrix(substitutionMatrix, im, reverse=False)

        scramblerParametersForDataField[SCRAMBLERPARAMETERSDATAFIELD_SEED] = seed
        scramblerParametersForDataField[SCRAMBLERPARAMETERSDATAFIELD_PERCENTAGEOFTURNS] = percentOfTurns


    elif (scrambler == "medium") or (scrambler == "heavy"):

        substitutionMap = createSubstitutionMapFromMask(pngim)
        print("SubMap Size", len(substitutionMap))
        if (len(substitutionMap) > 100000):
            print("SubMap Size might be too big, will probably run a long time")
        substitutionMapSource = substitutionMap.copy()

        seed = scramblerParameters[0]
        if scramblerParameters[1] > 0:
            rou = scramblerParameters[1]
        else:
            rou = 1
        if scramblerParameters[2] > 0:
            dist = scramblerParameters[2]
        else:
            dist = 10

        if scrambler == "medium":
            print("Using scrambler: medium")
            substituationMap = mixSubstitutionMap_medium(substitutionMap, seed=seed + passwordSeed, distance=dist,
                                                         rounds=rou)
        else:
            print("Using scrambler: heavy")
            scrambler = "heavy"
            substituationMap = mixSubstitutionMap_heavy(substitutionMap, seed=seed + passwordSeed, rounds=rou)

        scrambleBlocksOfImage(substitutionMapSource, substitutionMap, im, reverse=False)

        scramblerParametersForDataField[SCRAMBLERPARAMETERSDATAFIELD_SEED] = seed
        scramblerParametersForDataField[SCRAMBLERPARAMETERSDATAFIELD_ROUNDS] = rou
        scramblerParametersForDataField[SCRAMBLERPARAMETERSDATAFIELD_DISTANCE] = dist
    else:
        print("Unknown Scrambler: ", scrambler)
        print("Giving up")
        sys.exit(3)

    if isDisguiseEnabled:
        # TODO: 'Unbound local variables' options
        transferBlocks(im, pngim, patchImage, patchMaskImage)
        im = patchImage
        scramblerParametersForDataField[SCRAMBLERPARAMETERSDATAFIELD_PATCHIMAGE] = True

    # TODO only do this in one place
    if isDisguiseEnabled:
        mybytes = mybytes + createChunk(createImageInfo(im), 3)

    # blowup image
    if blowup:
        im = im.resize((int(im.width * 2), int(im.height * 2)), resample=Image.NEAREST)
        scramblerParametersForDataField[SCRAMBLERPARAMETERSDATAFIELD_BLOWUP] = True

    if isDisguiseEnabled:
        im.paste(thumb, (0, 0), mask=None)

    # serialize parameters
    print("Used scrambling configuration: ", scramblerParametersForDataField)
    serial_params = json.dumps(scramblerParametersForDataField, separators=(',', ':'))
    print("JSON:", serial_params)
    myrawdata = list(bytearray(serial_params, "utf-8"))
    print("JSON bytes:", len(myrawdata))
    chunkbytes = createChunk(myrawdata, 4)
    mybytes = mybytes + chunkbytes

    checksum = calculateChecksum(mybytes)
    print("Checksum: ", checksum)
    mybytes = mybytes + [checksum]

    # finalize, write main header
    mybytes = createChunk(mybytes, HEADER_VERSION_MAGIC_NUMBER + HEADER_VERSION_ENCODER)

    print("Serialize Data...")
    (imageWithMetadata, imagePosX, imagePosY) = serialize(im, mybytes)

    if isLogoEnabled:
        imageWithMetadata = placeLogo(imageWithMetadata, imagePosX, imagePosY - 8)

    print("Writing image to disk")
    imageWithMetadata.save(out_put_file_name, quality=outputQuality)


else:
    print("Mode: Descramble")

    savedim = Image.open(input_file_name)

    print("Decoding Header")

    myRestoredBytes, marginLeft, marginTop = deserialize(savedim, 3)  # decode first 3 bytes (header+length)

    dataHeader = decodeChunkType(myRestoredBytes, 0)
    versionStored = dataHeader - HEADER_VERSION_MAGIC_NUMBER
    print("Encoder Version of scramb.py: ", HEADER_VERSION_ENCODER)
    print("Decode possible down to     : ", HEADER_VERSION_ENCODER_MIN)
    print("Encoder Version of Image    : ", versionStored)
    if (versionStored > HEADER_VERSION_ENCODER) or (versionStored < HEADER_VERSION_ENCODER_MIN):
        print("Encoder Version missmatch or not a scrambled image or image without data")
        print("Giving up")
        sys.exit(3)

    totalBlocks = decodeChunkLength(myRestoredBytes, 0)
    print("Data Blocks: ", totalBlocks)

    print("Decoding All Data Blocks")
    # TODO: 'Unbound local variables' options
    myRestoredBytes, marginLeft, marginTop = deserialize(savedim, totalBlocks + 3)

    checksumCalc = calculateChecksum(myRestoredBytes[3:len(myRestoredBytes) - 1])
    checksumStored = myRestoredBytes[len(myRestoredBytes) - 1]
    print("Checksum stored    : ", checksumStored)
    print("Checksum calculated: ", checksumCalc)

    if checksumStored != checksumCalc:
        print("Checksum Error of encoded Data")
        print("Giving up")
        sys.exit(3)

    offsetY = marginTop * 8

    offsetX = marginLeft * 8

    print("Decoded ", len(myRestoredBytes), " bytes")
    print("Image starts at x=", offsetX, " y=", offsetY)

    pngimageread = []

    seek = 3

    finalImageDimensions = (0, 0)

    while seek < len(myRestoredBytes) - 1:  # -1 because of checksum at the end
        chunkType = decodeChunkType(myRestoredBytes, seek)
        chunkLength = decodeChunkLength(myRestoredBytes, seek)
        if chunkType == 0:  # Raw Data
            print("Chunk: Raw Data")
            print("Length: ", chunkLength)
            chunkData = getChunkData(myRestoredBytes, seek)

            seek = seek + chunkLength + 3
        elif chunkType == 1:  # Output Ascii Text
            print("Chunk: Text")
            print("Length: ", chunkLength)
            chunkData = getChunkData(myRestoredBytes, seek)
            embeddedText = bytearray(chunkData).decode("utf-8")
            print("----- Message from Image ---------------------------------------------------")
            print(embeddedText)
            print("----------------------------------------------------------------------------")
            if not isSilent:
                input("Press Enter to continue with descrambling...")
            seek = seek + chunkLength + 3

        elif chunkType == 2:  # png file
            print("Chunk: PNG File")
            print("Length: ", chunkLength)
            chunkData = getChunkData(myRestoredBytes, seek)

            pngfile = BytesIO(bytearray(chunkData))

            pngimageread.append(Image.open(pngfile))
            print("Images embedded so far:", len(pngimageread))
            seek = seek + chunkLength + 3

        elif chunkType == 3:
            print("Chunk: Image Info")
            print("Length: ", chunkLength)
            chunkData = getChunkData(myRestoredBytes, seek)

            finalImageDimensions = decodeImageInfo(chunkData)
            print("Image Width : ", finalImageDimensions[0])
            print("Image Height: ", finalImageDimensions[1])
            seek = seek + chunkLength + 3

        elif chunkType == 4:
            print("Chunk: Scrambler Parameters")
            print("Length: ", chunkLength)
            chunkData = getChunkData(myRestoredBytes, seek)
            if versionStored == 1:
                received_params = pickle.loads(bytes(chunkData))
            else:
                received_params = json.loads(bytearray(chunkData).decode("utf-8"))
            print("Parameters: ", received_params)
            seek = seek + chunkLength + 3
        else:  # unknown
            print("Chunk: UNKNOWN TYPE", chunkType)
            print("Length: ", chunkLength)
            seek = seek + chunkLength + 3
    # TODO: 'Unbound local variables' options
    scrambler = received_params[SCRAMBLERPARAMETERSDATAFIELD_SCRAMBLER]

    if (SCRAMBLERPARAMETERSDATAFIELD_PATCHIMAGE in received_params) and not isDisguiseEnabled:
        print("This is a patch image. It is used on another image, which is shown as")
        print("a thumbnail in this image. Please provide both images as input.")
        print("See help -? for needed commands.")
        print("Giving up")
        sys.exit(3)

    if SCRAMBLERPARAMETERSDATAFIELD_BLOWUP in received_params:
        blowup = received_params[SCRAMBLERPARAMETERSDATAFIELD_BLOWUP]
    else:
        blowup = False

    if SCRAMBLERPARAMETERSDATAFIELD_PASSWORDUSED in received_params:
        isPasswordSet = True

    if isPasswordSet and (password == ""):
        password = getpass("Enter Password: ")

    if isPasswordSet:
        passwordSeed = calculatePasswordSeed(password)

    intermediateImageDimensions = (
        int(math.ceil(finalImageDimensions[0] / 8.0) * 8), int(math.ceil(finalImageDimensions[1] / 8.0) * 8))

    if blowup:
        savedim = savedim.crop((offsetX, offsetY, offsetX + intermediateImageDimensions[0] * 2,
                                offsetY + intermediateImageDimensions[1] * 2))
        savedim = resizeQuads(savedim)
    else:
        savedim = savedim.crop(
            (offsetX, offsetY, offsetX + intermediateImageDimensions[0], offsetY + intermediateImageDimensions[1]))

    if isDisguiseEnabled:
        print("Disguise Enabled")
        imDisguise = Image.open(disguise_filename)
        print("Disguise Image size ", imDisguise.size)
        if not imDisguise.mode == "RGB":
            print("Image mode is", imDisguise.mode, ", converting it to RGB")
            imDisguise = imDisguise.convert("RGB")
        # imDisguise.show()
        transferBlocks(savedim, pngimageread[1], imDisguise, pngimageread[0])
        savedim = imDisguise

    if scrambler == "matrix":
        print("Using scrambler: matrix")

        seed = received_params[SCRAMBLERPARAMETERSDATAFIELD_SEED]
        percentOfTurns = received_params[SCRAMBLERPARAMETERSDATAFIELD_PERCENTAGEOFTURNS]

        substitutionMatrix = createSubstitutionMatrixFromMask(pngimageread[0])

        print("mixing..")
        mixSubstitutionMatrix(substitutionMatrix, seed=seed + passwordSeed, percent_Of_Turns=percentOfTurns)

        print("descrambling image..")
        savedim = scrambleBlocksOfImageWithMatrix(substitutionMatrix, savedim, reverse=True)





    elif (scrambler == "medium") or (scrambler == "heavy"):

        seed = received_params[SCRAMBLERPARAMETERSDATAFIELD_SEED]
        dist = received_params[SCRAMBLERPARAMETERSDATAFIELD_DISTANCE]
        rou = received_params[SCRAMBLERPARAMETERSDATAFIELD_ROUNDS]

        substitutionMap = createSubstitutionMapFromMask(pngimageread[0])
        if len(substitutionMap) > 100000:
            print("SubMap Size might be too big, will probably run a long time")
        substitutionMapSource = substitutionMap.copy()

        if scrambler == "medium":
            print("Using scrambler: medium")
            substituationMap = mixSubstitutionMap_medium(substitutionMap, seed=seed + passwordSeed, distance=dist,
                                                         rounds=rou)
        else:
            print("Using scrambler: heavy")
            scrambler = "heavy"
            substituationMap = mixSubstitutionMap_heavy(substitutionMap, seed=seed + passwordSeed, rounds=rou)

        print("Descrambling...")

        scrambleBlocksOfImage(substitutionMapSource, substitutionMap, savedim, reverse=True)

    if not intermediateImageDimensions == finalImageDimensions:
        savedim = savedim.crop((0, 0, finalImageDimensions[0], finalImageDimensions[1]))

    print("Writing image to disk")
    savedim.save(out_put_file_name, quality=outputQuality)

print("Done")
