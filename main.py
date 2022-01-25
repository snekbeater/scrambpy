from print_func import *
from scramb import *

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
