# Security in Eidolon

This section explains the security mechanisms in Project Eidolon, focusing on module verification and cryptographic signing.

## Overview

Eidolon uses a robust security model to ensure code integrity and user safety. Since Eidolon can run third-party code through its module system, security verification is essential to protect users from potentially malicious modules.

### Core Security Principles

1. **Trust Management**: Users decide which module authors they trust
2. **Transparency**: Clear indication of module verification status
3. **User Control**: Configurable security levels based on individual needs
4. **Cryptographic Verification**: Strong signature-based verification

## Key Components

- **Trusted Signers**: A registry of trusted public keys (`trusted_signers.json`)
- **Module Signatures**: Detached cryptographic signatures for each module (`module.sig`)
- **Security Modes**: Configurable security levels (paranoid, default, permissive)
- **User Prompts**: Interactive security decision system

## How It Works

At a high level, Eidolon's security system works like this:

1. **Module Signing**: Module authors sign their modules with their private key
2. **Trust Establishment**: Users add trusted authors' public keys to their system
3. **Verification**: Eidolon verifies module signatures against trusted keys before running
4. **User Decision**: For untrusted modules, users are prompted based on security settings

## Security Guide Sections

- [Security Model](model.md): Detailed explanation of the verification architecture
- [Module Signing Guide](signing-modules.md): How module authors can sign their modules
- [Managing Trusted Signers](trusted-signers.md): How to add, remove, and manage trusted signers
- [Security Configuration](configuration.md): Setting up your security preferences