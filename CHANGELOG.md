# Change Log
All notable changes to this project will be documented in this file.


## 0.4.0-alpha - 2022-02-06
### Added
- GnuPG PKI public key image "business card" generation
- 'pki' scrambler added for GnuPG PKI public key scrambling and descrambling
- 'ultra' scrambler added (removes deficiencies esp. of 'heavy' scrambler)
- tar and encrypted tar as new chunk types added
### Changed
- 64kB limit of chunks and whole data snake raised to 16MB limit (3 byte length)
### Fixed
- Bug when returning substitution map from medium and heavy scrambler removed
- Bug that auto installer did not exited scramb.py correctly removed
- Bug that command line arguments where mixed / not parsed correctly
### Limitations
- PKI should only work with normal installation under linux up to now

## 0.3.1 - 2022-01-22
### Added

### Changed

### Fixed
- Bug when patching images with portrait aspect ratio removed
- Bug when mask for patching starts with white pixels removed

## 0.3.0 - 2022-01-13
### Added
- Patch Mode
### Changed
- Descrambler can read multiple embedded PNG Files (needed for Patch Mode)
### Fixed

## 0.2.0 - 2022-01-12
- Writes Encoder Version 2
- Reads Encoder Version 1,2
### Added
 
### Changed
- Parameter encoding changed from Pickle to JSON for better compatibility with other languages (esp. JavaScript for possible Greasemonkey integration)

### Fixed
- unknown Chunk Type Handled
