# Module System Overview

Project Eidolon is built around a flexible, decentralized module system that enables easy extension and customization. This document provides an overview of how the module system works and how modules interact with each other.

## Core Concepts

### What are Modules?

Modules are self-contained components that perform specific functions within Eidolon. Each module:

- Has a single responsibility (e.g., data collection, analysis, output generation)
- Communicates with other modules via a universal message bus
- Is configured through a standardized YAML file
- Can be easily enabled, disabled, or replaced without affecting the core system

### Module Architecture

To create this system, a sophisticated architecture has been built from the ground up to give developers maximum freedom, while keeping communication & initialization as simple as possible.

Modules inherit a base class called "**ModuleCore**", which must be inhereted to provide module functionality. It provides an extensive set of abstract methods which are all optional to override (these methods can be found in the documentation [here](methods.md))

Communication between modules is done via the "**MessageBus**" core script, which uses a *publish-subscribe* system with type reinforcement. Modules can publish and/or subscribe to inputs/outputs simply by specifiying a name and datatype. [Pipelines](../pipelines/1-overview.md) can also specify the exact module to gather input from.

Coordinating the system is the "**ModuleEngine**", which organises utilities for module management. This includes discovering modules based on a pipeline, loading modules, verifying modules and other management.

## The Module Lifecycle

0. **Pipeline**: The user defines a pipeline.yaml file containing the desired modules & their dependent modules.
1. **Discovery**: The system scans the `/modules` directory for modules defined in the pipeline
2. **Verification**: Each module's integrity is verified using cryptographic signatures
3. **Loading**: Valid modules are instantiated according to the active pipeline
4. **Connection**: Input/output channels are connected via the MessageBus
5. **Execution**: Modules process data and communicate results
6. **Shutdown**: Modules gracefully release resources when the system terminates

## Message Bus Communication

Modules communicate through a type-safe message bus using a publish-subscribe pattern:

1. **Publishers**: Modules publish data to named topics
2. **Subscribers**: Modules subscribe to topics they're interested in
3. **Type Validation**: The system validates that published data matches expected types
4. **Metadata Wrapping**: All data is automatically wrapped in a `CourierEnvelope` which includes metadata like the source module and timestamp.

Note that modules can be both publishers and subscribers, or neither of the two\*

```
Module A                   Message Bus                 Module B
┌─────────────┐               ┌───────────┐               ┌─────────┐
│             │ publish       │           │  subscribe    │         │
│ Processor   ├──────────────►│  keywords ├───────────────► Display │
│             │               │           │               │         │
└─────────────┘               └───────────┘               └─────────┘
```

For detailed information about working with the message bus, see the [Module Methods documentation](methods.md).

\* *While a module can have no inputs/outputs, this goes against some of the best practices.

## Configuration System

Each module is configured through a `module.yaml` file that defines:

- Basic metadata (name, version, creator)
- Input and output specifications
- External dependencies
- Runtime configurations

For complete configuration options, see the [Module Configuration documentation](config.md).

## Default Modules

Project Eidolon comes with the following default modules to support OSINT workflows:

| Module | Description | Key Features |
|--------|-------------|-------------|
| Aethon Crawler | Advanced web crawler for targeted OSINT data collection | - Configurable crawl depth<br>- Rate limiting<br>- Content extraction<br>- Pattern matching |
| Aethon URLClean | URL processing and sanitization module | - URL normalization<br>- Parameter filtering<br>- Domain validation<br>- Duplicate detection |
| Aethon URLList | URL management and targeting module | - Target list management<br>- Discovery tracking<br>- URL prioritization<br>- Crawl frontier management |
| Hermes | Communication module for transmitting processed data | - Secure data transmission<br>- Multiple output formats<br>- Customizable alert thresholds |
| Osiris | Data archival and retrieval system | - Structured data storage<br>- Historical analysis<br>- Efficient retrieval mechanisms |
| Scryer | Visualization and reporting module | - Interactive dashboards<br>- Custom report generation<br>- Data exploration tools |

## Security Model

The module system includes security features to protect data integrity and prevent unauthorized code execution:

- Modules are cryptographically signed
- Module hashes are verified before loading
- A public key infrastructure notifies a user when modules they are loading are unverified

For more information on module security, see the [Security documentation](../security/model.md).

## Next Steps

To create your own module, follow the [Creating a Module guide](2-creating-a-module.md).

To learn about connecting modules together in pipelines, see the [Pipeline Overview](../pipelines/1-overview.md).