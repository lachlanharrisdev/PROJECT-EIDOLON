# PROJECT EIDOLON

Project Eidolon is a decentralised suite of OSINT tools built to analyze the evolution of political disinformation on social media. 

In it's default configuration, Eidolon uses clever keyword rotation to scrape popular social media networks (primarily Twitter/X) 
for posts about major political entities, identifies opinionated posts coming from potential bot accounts, and tracks these accounts towards botnets to identify organisations running unethical political propaganda schemes. 

> ### **EIDOLON**
> ***Noun*** ● **/ʌɪˈdəʊlɒn/**

> In ancient Greek literature, an eidolon is a spirit-image of a living or dead person; a shade or phantom 'look-alike' of the human form.
> <br/>

<br/>


## FEATURES

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

## DEFAULT MODULES

| Module | Description |
| --- | --- |
| Keyword Monitor | Scrapes RSS feeds for popular political news articles, then uses NLP to identify political entities |