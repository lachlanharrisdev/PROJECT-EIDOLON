# Overview

Project Eidolon is a modular, enterprise-ready pipeline framework for Open Source Intelligence (OSINT) tools.

In its default configuration, Eidolon provides a flexible, plug-and-play system for data collection, analysis, and reporting across various intelligence domains. The modular architecture allows users to create custom data processing workflows for a wide range of OSINT applications.

> ### **EIDOLON**
> ***Noun*** ● **/ʌɪˈdəʊlɒn/**

> In ancient Greek literature, an eidolon is a spirit-image of a living or dead person; a shade or phantom 'look-alike' of the human form.
> <br/>

<br/>


## Features

- **ENTIRELY MODULE-BASED**
    - Default modules are verified based on a key-pair-based signed hash generator
    - Modules communicate via a universal message bus
    - Modules specify any number of inputs & outputs, and automatically subscribe to matching outputs from other modules
    - Modules each have their own `.yaml` file for configuration
    - All core functionality (beyond module management, security & logging) is stored in modules, making it easy to remove unnecessary functionality
- **VERSATILE PIPELINE SYSTEM**
    - Define complex workflows through simple YAML configuration
    - Connect modules in linear, star, or aggregation patterns
    - Dynamic module execution modes: loop, reactive, once, or on-trigger
    - Robust error handling and recovery mechanisms
- **PRODUCTION-READY LOGGING**
    - Console logging has been standardised across modules
    - Logging has a fully customisable format, including colours, text decoration & variables
    - All logs are saved into a persistent `.logs/` folder
- **WEB CRAWLING AND ANALYSIS**
    - Advanced web crawling capabilities via the Aethon module package
    - URL processing, cleaning, and structured data extraction
    - Configurable crawl depth and focus areas
- **SECURE DATA MANAGEMENT**
    - Secure storage and retrieval of collected intelligence
    - Cryptographically signed modules for security verification
    - Granular access control for sensitive data
- **VISUALIZATION AND REPORTING**
    - Interactive dashboards for intelligence analysis
    - Customizable report generation
    - Real-time monitoring capabilities
 
<br/>

## Default Modules

| Module | Description |
| --- | --- |
| Aethon Crawler | Advanced web crawler for targeted OSINT data collection with configurable parameters |
| Aethon URLClean | URL processing module for sanitizing and normalizing web addresses |
| Aethon URLList | URL management module for handling crawl targets and discovered links |
| Hermes | Communication module for transmitting processed data |
| Osiris | Data archival and retrieval system |
| Scryer | Visualization and reporting module |