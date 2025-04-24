# Overview

Project Eidolon is a modular, enterprise-ready pipeline framework for Open Source Intelligence (OSINT) tools.

In its default configuration, Eidolon provides a flexible, plug-and-play system for data collection, analysis, and reporting across various intelligence domains. The modular architecture allows users to create custom data processing workflows for a wide range of OSINT applications.

> ### **EIDOLON**
> ***Noun*** ● **/ʌɪˈdəʊlɒn/**

> In ancient Greek literature, an eidolon is a spirit-image of a living or dead person; a shade or phantom 'look-alike' of the human form.
> <br/>

<br/>


# // FEATURES

## MODULAR

Every pipeline, every module & every command is configurable down to the core. Your `pipeline.yaml` file can store all of your perfect settings, but if you need to overwrite the maximum threads in the web crawler, you can do that with a single extra argument.

* Workflows are stored in reusable `.yaml` files, each containing execution configuration, per-module configuration, module I/O & more
* The CLI has a powerful array of commands & arguments to make every run feel special
* Every module is swappable & removable
* A sophisticated translation layer converts datatypes automatically, so everything **just works**
```python
eidolon run -s crawler.timeout=10 scryer.phones=false
```
```yaml
modules:
- name: aethon_crawler
  id: crawler
  config: [concurrency: 300, timeout: 8, verify_ssl: true]
  input: [urls: cleaner.cleaned_urls]
  output: [crawled_data: "crawled_data", crawled_count: "url_count"]

- name: scryer
  config: [phones: true, emails: true]
  input: [data: crawler.crawled_data]
```

<br/>

## SECURE

Anything that has the slightest chance of exposing your device you aren't told about.

* Every module is checked for verification before its name is even loaded
* Add or delete any trusted module authors to allow their verified modules
* Self-sign modules you create & share them with the world
* Many configurable arguments to automate module permission

```bash
2025-01-01 12:00:00,000 INFO     [module_security.py:317]     Module 'aethon_urllist' verified by John Doe (Project Eidolon Owner)
2025-01-01 12:00:00,000 INFO     [engine_core.py:274]         Module 'aethon_urllist' verification successful

⚠️  SECURITY WARNING: Module 'example_malicious_module' is unsigned
This module has not been verified by any trusted signer.
Running unverified modules can be a security risk.

Do you want to proceed with this module? (yes/no/always): n
2025-01-01 12:00:05,000 INFO     [module_security.py:290]     User declined to run untrusted module 'example_malicious_module'
2025-01-01 12:00:05,000 WARNING  [engine_core.py:277]         Module 'example_malicious_module' verification failed - will be excluded from execution
```

<br/>

## PERFORMANT

Modules have virtually no overhead, with an I/O system & translation layer so light you won't believe it exists.

* Modules have access to a shared threadpool & can create their own
* Modules run fully asynchronously from one-another
* As long as it can be called from python, your CPU-bound logic can be written in **any** language
* Default modules are designed with flexibility, extensive features & raw power in mind

```python
2025-04-23 14:44:24,232 INFO     [aethon_crawler] Crawl finished. URLs added to queue: 1274. Unique URLs visited (approx): 1274
2025-04-23 14:44:24,233 INFO     [aethon_crawler] Crawl execution finished in 29.47 seconds.
...
2025-04-23 14:44:24,233 INFO     [osiris] Received 1274 items for filtering
2025-04-23 14:44:24,235 INFO     [osiris] ==================================================
2025-04-23 14:44:24,236 INFO     [osiris] OSIRIS FILTER REPORT
2025-04-23 14:44:24,237 INFO     [osiris] ==================================================
2025-04-23 14:44:24,237 INFO     [osiris] Items processed: 1274
2025-04-23 14:44:24,237 INFO     [osiris] Items passed: 894 (70.2%)
2025-04-23 14:44:24,237 INFO     [osiris] Items rejected: 380 (29.8%)
2025-04-23 14:44:24,237 INFO     [osiris] ==================================================
...
2025-04-23 14:44:24,338 INFO     [scryer] Processing 894 pages of crawled data
2025-04-23 14:44:24,348 INFO     [scryer] ==================================================
2025-04-23 14:44:24,348 INFO     [scryer] SCRYER EXTRACTION REPORT
2025-04-23 14:44:24,348 INFO     [scryer] ==================================================
2025-04-23 14:44:24,351 INFO     [scryer] Total pages processed: 894
...
```
**Crawl -> Filter -> Scrape**, all in under **30 seconds**
<br/>

## RELIABLE

Gone are the days of a single error throwing out your two-hour-long python script. Errors are isolated, logged, and life just continues without them.

* Custom translation layer automatically converts mismatching datatypes between modules
* Errors don't stop your script from running (Unless you want them to)
* Logs are safely stored for easy reporting
* A custom shutdown coordinator ensures your files & data are safe
 
<br/>

## Default Modules

| Module | Description |
| --- | --- |
| Aethon | An ultra-high performance web crawler inspired by the architecture of [Photon](https://github.com/s0md3v/Photon). <br/> Comes with three modules: `Aethon_Crawler`, `Aethon_URLList` (parses various formats of URL Lists into List[str], w/ example link generation) & `Aethon_URLClean` (Filters out & cleans URL Lists, based on unnecessary URL extensions, file extensions, duplicates & more) |
| Scryer | An offline web-scraper that takes raw HTML data and searches for metadata, headers, URLs, phone numbers, emails & more |
| Osiris | A maximally-configurable data filter that takes in huge lists / dictionaries & rapidly translates the output |
| Hermes | An ultra-lightweight report generator that takes in any raw data and parses it to a (mostly) human-readable format |
