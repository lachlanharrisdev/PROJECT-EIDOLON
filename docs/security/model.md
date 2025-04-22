# Security Model

This document explains the security model and verification architecture used in Project Eidolon.

## Multi-Signer Trust Model

Eidolon implements a distributed trust model that allows modules to be signed and verified by multiple trusted entities, rather than relying on a single central authority.

### Key Concepts

- **Trusted Signers**: Public keys from entities you trust to sign modules
- **Module Signatures**: Detached cryptographic signatures (`module.sig` files)
- **Verification Status**: Levels including Verified, Signed-Untrusted, Unsigned, or Invalid

### Trust Architecture

Unlike the traditional central verification model, Eidolon uses a web of trust approach:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Module Author  │     │  Module Author  │     │  Module Author  │
│   (Trusted)     │     │  (Untrusted)    │     │   (Trusted)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│ Signed Module  │      │ Signed Module  │      │ Signed Module  │
└────────┬───────┘      └────────┬───────┘      └────────┬───────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Trusted Signers Registry                    │
│              (User's personal list of trusted keys)             │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Eidolon Security Verification                  │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Module Verification Decision                   │
│                                                                 │
│  ┌─────────────┐    ┌───────────────┐    ┌────────────────────┐ │
│  │   Verified  │    │    Signed     │    │      Unsigned      │ │
│  │ (Automatic  │    │  (Untrusted)  │    │ (Requires explicit │ │
│  │  approval)  │    │ (User prompt) │    │     approval)      │ │
│  └─────────────┘    └───────────────┘    └────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Module Hash Generation

When a module is signed, the system computes a deterministic hash of its contents:

1. The entire module directory tree is scanned (excluding `.sig` files and cache files)
2. All files are hashed in a deterministic order
3. A combined SHA-256 hash is generated representing the entire module content

This hash ensures that any modification to the module's code will invalidate the signature.

## Signature Verification

When Eidolon loads a module:

1. It checks for the presence of a `module.sig` file
2. It computes the module's hash using the same deterministic algorithm
3. It verifies the signature against the hash using trusted public keys
4. It determines the verification status:
   - **Verified**: Signature is valid and matches a trusted signer
   - **Signed-Untrusted**: Signature is valid but from an unknown signer
   - **Unsigned**: No signature file found
   - **Invalid**: Signature is invalid or corrupted

## Security Modes

Eidolon supports three security modes:

1. **Paranoid**: Only verified modules from trusted signers are allowed
2. **Default**: Prompts for untrusted modules, allows verified modules automatically
3. **Permissive**: Allows all modules with appropriate warnings for unsigned ones

## Command-Line Security Options

Security modes and behaviors can be configured via command-line flags:

```bash
eidolon run --security-mode=paranoid pipeline_name
eidolon run --allow-unverified pipeline_name
```

## Signature File Format

A module signature is a detached binary file containing:

- The raw signature bytes produced by signing the module hash
- Using PSS padding and SHA-256 hashing algorithm

The signature file is named `module.sig` and is placed in the module's root directory.