# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 30-09-2025

### Added
- Add links to API docs in the nav bar

### Changed
- Make the sidebar and output area resizable by dragging a divider between them
- Moved all logic for default values into the backend, so it is consistent between the API and the front end.

### Fixed
- Fix nav bar overlapping with content

## [2.0.0] - 25-09-2025

### Changed
- Changed endpoints to be asynchronous. `/thematic-screener` will now return a `request_id` immediately, and progress updated and the result can be fetched later using `/status/{request_id}`.
- Updated document type enum to be consistent with the Bigdata.com SDK
- Updated front end to deal with the async endpoint.
- Improved UX of the front end

## [1.1.0] - 11-09-2025

### Added
- Added optional access token protection for the API endpoints. If the `ACCESS_TOKEN` environment variable is set, all API requests must include a `token` query parameter with the correct value to be authorized.


## [1.0.0] - 29-08-2025

### Added
- Initial release of the thematic screener service by bigdata.com as a Python package and Docker image.
