import math


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