# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
[markdownlint](https://dlaa.me/markdownlint/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2019-11-05

### Added in 1.4.0

- Add support for MSSQL database.
- Update to senzing/senzing-base:1.3.0

## [1.3.3] - 2019-11-06

### Fixed in 1.3.3

- Support non-root commandline invocation.

## [1.3.2] - 2019-11-02

### Fixed in 1.3.2

- Cast string as int in `os.chown()` call.

## [1.3.1] - 2019-10-22

### Changed in 1.3.1

- Incorporate changes for Senzing 1.12.0

## [1.3.0] - 2019-08-31

### Changed in 1.3.0

- Is now a `non-root`, immutable container.

## [1.2.1] - 2019-08-19

### Changed in 1.2.1

- Adapted to new Senzing API server initialization

## [1.2.0] - 2019-08-05

### Changed in 1.2.0

- RPM based installation

## [1.1.0] - 2019-07-23

### Added in 1.1.0

- Database support
  - PostgreSQL
  - MySQL
  - Db2
  - SQLite
