# Scramb.py
Scramb.py is a region based JPEG Image Scrambler written in Python.

![](img/overview.png)

## Main features
- Scramb.py can scramble images *regions*. So you can e.g. scramble only the face of a person.
- All you need to descramble the image is encoded in a data „snake“ around the image. The scrambled image is thus a bit wider as the original.
- You can select different scramble modes.
  - When you slightly scramble a region, a thumbnail of the image can still be recognized.
  - If you use the heavy scrambler, you cannot guess the content.
- You can set a password
- You can include short text messages that will show up upon descramble
- Easy to use: Windows Drag & Drop descramble
- Survives multiple re-encodings of an image down to JPEG quality around 30 something, when the image gets ugly and blocky still chances that they decode
- Does not depend on any meta data within the JPEG file, as these are normally completly stripped by all major social media sites.

![](img/Lenna_heavy_pw.jpg)

*In this example, only Lenna's face was scrambled and the scrambled image is password protected. You can actually try the example images in this repo with scramb.py yourself!*
*Also, people get offended when Lenna is used (although, now we also have Fabio, which I use as a Black/White Test Image!... so, Lenna is scrambled here in this repo :-)*

## Use cases
- Offend the easily offended *less*: Upload pictures to sites like Twitter, Facebook, DeviantArt etc. (esp. Social Media) that normally trigger people to report these *despite* being okay and according to TOS of the site.
- Upload a pic as a teaser but give away the password only to a small section of people

# Usage

## Scramble
`scramb.py -i <inputfile> [-m <mask.png/.jpg>] -o <outputfile.jpg>  [OPTIONS]`

You must use `-m` and/or `-s` for scramb.py to detect that you want to scramble.

## Descramble
`scramb.py <inputfile.jpg>` also usable for drag & drop

`scramb.py -i <inputfile.jpg> -o <outputfile.jpg>`

## Calculate Residue
`scramb.py -r <imagefile1.jpg> <imagefile2.jpg>`

## Options
### -x <number> -y <number> -z <number>
Specific parameter for the chosen scrambler, see table below.

### -s <scrambler>
The scrambler to be used

scrambler | x | y | z | What it does
--- | --- | --- | --- | ---
`matrix` | seed | turn percentage (10=10%, 100=100%, 170=170%) | - | turns a group of 2x2 blocks clockwise. Does not work on lonely pixels.
`medium` | seed | rounds | distance | moves a block a maximum of *distance* left or right. Runs over all blocks *rounds* times.
`heavy` | seed | rounds | - | moves every block somewhere else *rounds* times

### -2
Blowup image by 2x
### --quality=
`--quality=10..100`

JPEG Output Quality 0-100, 100=best, default=100
### --no-logo
do not include Logo in Image
### -t
`-t "<Text>"`

Embed text to show when descrambling (max. 400 chars)
### --silent
Do not pause on descramble for displaying text
### -p
Scramble with password (ask for it)
### --password=
`--password=<password>`

Scramble with `<password>`

Caution: it's then in your console history! Use `-p` instead!
### --stealth
Hide password use from generated image. You must run descrambling with `-p` or `--password` option then! Descrambling without these options will otherwise not promt for a password and the descrambled image is still scrambled (in a different way).
### --overwrite
Overwrite output file when it exists


# Details

## Image quality
Slight scramble will produce a near identical descrambler image.
Scramb.py scrambles 8x8 blocks to best encounter effects of jpeg artifacts.
Nevertheless the heavy scrambler will produce a grid like structure in bright (esp. red/blue) regions of the descrambled image. This happens because of color subsampling in JPEG by the factor 2 and in a scrambled image, blocks of brigthness and darkness now lie next to each other when in the original image they do not.

You can circumvent that with the `-2` option, blowing up the image by 2x. While descrambling, it will automatically be reduced to the original size.

## Regional scrambling
The main advantage of this scrambler in comparison to other image scrambles is that it can scramble only parts of an image.
For that you provide the scrambler also a black and white image where you marked the regions you want to scramble in white.
You can easily create such an image with Photoshop, GIMP or even Windows Paint. Just be carefull not to overwrite your original image with Paint ;-D

## Seed based scrambling
All of Scramb.py's Scrambling Algorithms use a Seed to generate pseudo random numbers. This is essential so that when descrambling, Scramb.py can create the substitution map that was used for scrambling.  

## Password protection
You can set a password. Be aware that the password system and the used Random Number Generator are nowhere near security and not tested for that application.
Consider the password system to be like a cheap padlock.

## Text
You can add a short text to be shown while descramble
This text is *not* password protected

## Scramb.py - Logo
A small logo is added to help people find this descrambler „scrambled by Scramb.py“
You can of course switch that off if you wish

## Drag & Drop
Windows use is easy for descramble
(Scramble needs commandline;-)

## Backdoor Free Code
Code is easy to follow so feel free to check it for backdoors. You can even delete the encoded logo

## Full resolution examples

### Image region
#### Original
![](img/kodim04.png)
#### Scramble mask
![](img/kodim04_mask.png)
#### Output, slightly scrambled
![](img/kodim04_scrambled.jpg)

### Full image
#### Original
![](img/kodim23.png)
#### Output, heavy scramble
![](img/kodim23_scrambled.jpg)


# Notes
Sample Images from
  
http://r0k.us/graphics/kodak/index.html
  
https://en.wikipedia.org/wiki/Lenna

