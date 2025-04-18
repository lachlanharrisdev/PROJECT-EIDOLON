# // PROJECT EIDOLON

![Banner](/.github/images/Banner_2x1.jpg)

<div align='center'>
    
![PYTHON](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue) ![DOCKER](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white) ![GPL-2.0](https://img.shields.io/badge/GPL--2.0-red?style=for-the-badge)

</div>

<br/>

Project Eidolon is a decentralised suite of OSINT tools built to analyze the evolution of political disinformation on social media. 

In it's default configuration, Eidolon uses clever keyword rotation to scrape popular social media networks (primarily Twitter/X) 
for posts about major political entities, identifies opinionated posts coming from potential bot accounts, and tracks these accounts towards botnets to identify organisations running unethical political propaganda schemes. 

<br/>

> ### **EIDOLON**
> #### *Noun* ● /ʌɪˈdəʊlɒn/
> In ancient Greek literature, an eidolon is a spirit-image of a living or dead person; a shade or phantom 'look-alike' of the human form.
> <br/>

<br/>

# // OVERVIEW

Eidolon is completely module-based, meaning all of the actual functionality is easily modifiable, removable & distributable, without causing any errors. The suite comes pre-loaded with modules that cover all of the functionality that most people would need, but for those who need maximum extensibility or connections with other applications, then this has been built for you.

<br/>

## // FEATURES

- **ENTIRELY MODULE-BASED**
    - Default modules are verified based on a key-pair-based signed hash generator
    - Modules communicate via a universal message bus
    - Modules specify any number of inputs & outputs, and automatically subscribe to matching outputs from other modules
    - Modules each have their own `.yaml` file for configuration
    - All core functionality (beyond module management, security & logging) is stored in modules, making it easy to remove unnecessary functionality
- **DYNAMIC KEYWORD GENERATION** *\[via keyword_monitor module\]*
    - Keywords are updated regularly in real-time based on trending political news articles
    - Political entities are identified & classified via NLP
    - Keywords are transmitted on the message bus for any module to subscribe to
- **PRODUCTION-READY LOGGING**
    - Console logging has been standardised across modules
    - Logging has a fully customisable format, including colours, text decoration & variables
    - All logs are saved into a persistent `.logs/` folder
 
<br/>

## // DEFAULT MODULES

| Module | Description |
| --- | --- |
| Keyword Monitor | Scrapes RSS feeds for popular political news articles, then uses NLP to identify political entities |

<br/>

# // GETTING STARTED

To get started with contributing, please read [contributing.md](/CONTRIBUTING.md) & the [code of conduct](/.github/CODE_OF_CONDUCT.md).

## // REQUIREMENTS
- Python 3.12\*
- *\[Optional\]* Docker CLI


\* *specifically tested on `3.12.10`. Other python versions may work but are untested. If you'd like to request full support for a version, please create a github issue, PR, or raise a ticket in [the discord](https://discord.gg/wDcxk4pCs5)*

<br/>

## // INSTALLATION

1. Clone the repo
```bash
git clone https://github.com/lachlanharrisdev/project-eidolon.git
cd project-eidolon
```

2. Install package + dependencies
```bash
pip install -r requirements.txt
```

<br/>

**DEVELOPERS / CONTRIBUTORS:** It is recommended you setup a virtual environment if you plan on creating and/or modifying any code:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

<br/>

## // DOCKER

1. Build the full Docker image

```bash
docker build -f .Dockerfile -t eidolon .
```

2. Run the container

```bash
docker run -it eidolon
```

<br/>

# // USAGE

```bash
Usage:
  eidolon run [<module>] [--log-level=<level> | --verbose] [--output-format=<format>]
  eidolon version
  eidolon (-h | --help)

Options:
  -h --help                 Show this help message.
  --log-level=<level>       Set the logging level [default: INFO].
                            Options: DEBUG, INFO, WARNING, ERROR, CRITICAL.
  --verbose                 Enable verbose output (equivalent to --log-level=DEBUG).
  --output-format=<format>  Set the output format [default: text].
                            Options: text, json.

Commands:
  run       Run the main application or a specific module.
            If <module> is not specified, all modules will be run.
  version   Show the version of the CLI.

Examples:
  eidolon run --log-level=DEBUG
  eidolon run my_module --output-format=json --verbose
  eidolon version
  eidolon -h
```

\* *Usage as of 18/04/2025, v0.3.0. For up-to-date usage and command-specific help, please install the tool and run* `eidolon -h` *or* `eidolon --help`

<br/>

# // DEVELOPMENT && CONTRIBUTING

To see more about how to contribute, please refer to [contributing.md](/CONTRIBUTING.md). We welcome more than just developers - documentation writers, researchers / journalists, funders, bug hunters etc.

<br/>

## // MODULES

Modules are the core functionality behind Eidolon. Each module is self-contained and communicates with other modules via the message bus.

<br/>

### // ADDING NEW MODULES

Please refer to the full documentation for instructions on creating modules

1. Create a new directory under `src/modules`
2. Add a `module.yaml` file with the module's configuration, and a `main.py` file that inherents the `ModuleCore` class
3. Incorporate your functionality based off the abstract functions inherited from `ModuleCore`

If built correctly, the module should be loaded when running `eidolon run`, `eidolon run <module_name>` or its otherwise loaded as a dependency to another module.

<br/>

### // SUBMITTING MODULES

Currently, we only accept modules in PRs which either directly affect core functionality with a (mostly) universal benefit to users. No modules will be accepted into this repository as verified modules if they are for a niche usecase, connect with other non-open-source tools, or they do not inherit the core values behind the project.

If you believe your module is ready to become a default module, please open a pull request detailing everything about your module, and we will review it carefully.

For more information on module security, please read [security.md](/.github/SECURITY.md)

<br/>

## // RUNNING TESTS

This project uses `pytest` for testing. Major modules & every individual module uses tests to ensure code quality. All test files begin with the prefix `test_`, as per the [pytest documentation](https://docs.pytest.org/en/stable/getting-started.html).

To run all the tests in the project locally before creating a pull request, run the following in the project directory:

```
pytest
```

You can run all tests within a specific directory using:
```
pytest <dir>/

# e.g. Run all of the tests for loaded modules
pytest modules/
```

For more info, refer to the [pytest documentation](https://docs.pytest.org/en/stable/getting-started.html)

<br/>

# // THE MISSION

This is just the beginning. Eidolon will evolve — as propaganda does. The methods will change, but our values will stay the same.

Help us build a system that resists the spread of disinformation. Contribute code. Fork the project. Share the mission. Start discussions.

