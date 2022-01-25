import math

from PIL import ImageChops


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
                    values.append(r)
                    values.append(g)
                    values.append(b)
            valueSum = 0
            for value in values:
                valueSum = valueSum + value
            valueMedian = valueSum / len(values)
            rectDuo = round(valueMedian / 85)  # four possible values between 0 and 255
            theByte = theByte | rectDuo
            if x + y > 0:  # last round no shift at the end
                theByte = theByte << 2
    return theByte
