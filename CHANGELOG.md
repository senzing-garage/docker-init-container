# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
[markdownlint](https://dlaa.me/markdownlint/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.11] - 2021-07-13

### Added in 1.6.11

- pdated to senzing/senzing-base:1.6.0

## [1.6.10] - 2021-03-31

### Added in 1.6.10

- The `debug-database-url` subcommand for debugging SENZING_DATABASE_URL parsing

## [1.6.9] - 2021-03-25

### Added in 1.6.9

- Better handling of SENZING_ENGINE_CONFIGURATION_JSON when creating G2Module.ini

## [1.6.8] - 2021-03-16

### Added in 1.6.8

- Message when `SENZING_G2CONFIG_GTC` is created.
- Refactored creating /etc/opt/senzing/G2Config.gtc; always produces a file.

## [1.6.7] - 2021-03-16

### Added in 1.6.7

- Support for `SENZING_G2CONFIG_GTC`

### Changed in 1.6.7

- Update to senzing/senzing-base:1.5.5

## [1.6.6] - 2021-02-03

### Added in 1.6.6

- Critical [bug fix](https://github.com/Senzing/docker-init-container/issues/104) for bug introduced in 1.6.5:

## [1.6.5] - 2021-02-01

### Added in 1.6.5

- Using the templates without the '.templates' extension in the resources/templates folders.

## [1.6.4] - 2020-12-17

### Added in 1.6.4

- Calling database specific initialization when specifying `SENZING_ENGINE_CONFIGURATION_JSON`

## [1.6.3] - 2020-11-28

### Added in 1.6.3

- Added initial support for `SENZING_ENGINE_CONFIGURATION_JSON`
- Added initial support for `SENZING_GOVERNOR_URL`

## [1.6.2] - 2020-11-27

### Added in 1.6.2

- Added support for `SENZING_LICENSE_BASE64_ENCODED` so that Senzing `g2.lic` contents can be passed in and an `/etc/opt/senzing/g2.lic` file is created.

### Removed in 1.6.2

- Removed support for `SENZING_GOVERNOR_POSTGRESQL_INSTALL`, as setting `SENZING_ENABLE_POSTGRESQL` is a better approach.

## [1.6.1] - 2020-11-20

### Added in 1.6.1

- Support for `SENZING_GOVERNOR_POSTGRESQL_INSTALL`, a temporary env var only input that will install the Senzing postgresql governor if a governor does not exist. A workaround until issue #89 is fixed.

## [1.6.0] - 2020-11-02

### Added in 1.6.0

- Support for `SENZING_ENGINE_CONFIGURATION_JSON`

## [1.5.11] - 2020-10-30

### Fixed in 1.5.11

- Fixed references to `libmysqlclient.so.21.1.20`

## [1.5.10] - 2020-10-23

### Changed in 1.5.10

- Accommodate changes in Senzing 2.3.0.  Optional processing of `G2Project.ini`

## [1.5.9] - 2020-09-28

### Changed in 1.5.9

- Replacing SENZING_INIT_CONTAINER_SLEEP with SENZING_DELAY_IN_SECONDS to be consistent with other Senzing images
- Automatically downloading and installing Senzing postgresql governor if no governor exists.

## [1.5.8] - 2020-09-15

### Changed in 1.5.8

- Changed permissions on db2dsdriver.cfg to 755 (from 750)

## [1.5.7] - 2020-09-02

### Changed in 1.5.7

- Fixed issue with MS SQL port specification

## [1.5.6] - 2020-07-23

### Changed in 1.5.6

- Update to senzing/senzing-base:1.5.2

## [1.5.5] - 2020-07-07

### Changed in 1.5.5

- Update to senzing/senzing-base:1.5.1
- Add logging information.

## [1.5.4] - 2020-05-11

### Changed in 1.5.4

- Changed the detection of existing paths.

## [1.5.3] - 2020-04-27

### Changed in 1.5.3

- Add support for PostgreSQL ODBC.

## [1.5.2] - 2020-04-22

### Changed in 1.5.2

- Adjust for changes in Senzing SDK.
  - Return codes have been removed in favor of Exceptions.

## [1.5.1] - 2020-04-22

### Changed in 1.5.1

- Improved documentation
- Support for `SENZING_ENGINE_CONFIGURATION_JSON`
- Improved logging

## [1.5.0] - 2020-01-29

### Changed in 1.5.0

- Update to senzing/senzing-base:1.4.0

## [1.4.2] - 2020-01-27

### Added in 1.4.2

- Copy `G2C.db` to `G2C_LIBFEAT.db` and `G2C_RES.db`

## [1.4.1] - 2019-11-27

### Added in 1.4.1

- init-container.py subcommands:  initialize-files, initialize-database
- No change to docker image behavior.

## [1.4.0] - 2019-11-13

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
