# Change Log
All notable changes to this project will be documented in this file.


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
