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