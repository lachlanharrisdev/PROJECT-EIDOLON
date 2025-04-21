# Module Verification and Security

This document explains the security mechanisms in Project Eidolon's module system, including the verification process, cryptographic signing, and best practices for securing modules.

## Security Model

Project Eidolon uses a security model based on cryptographic signatures to ensure users are aware when they are running unverified modules (that is, modules not officially a part of the project eidolon repository). This security model is crucial for OSINT workflows where data integrity and protection against malicious code are paramount concerns.

### Key Components

1. **Public/Private Key Infrastructure**: A keypair-based signing system for modules
2. **Module Hash Generation**: Automatic hashing of module code files
3. **Verification System**: Pre-execution validation of module hashes
4. **Verified Module Registry**: A record of modules that have passed verification

## Creating Signed Modules

Modules can only be signed by the CI workflow on the [official github repository](https://github.com/lachlanharrisdev/PROJECT-EIDOLON), and the only modules that will be accepted into this repo are ones that provide benefit to a broad range of potential users, which are built following coding standards outlined in this documentation & the repository.

If you'd like to contribute a module to the repository:

1. **Develop your module** following the [module development guidelines](2-creating-a-module.md)
2. **Request signing** by creating a PR from the module request template
3. **Wait** for the maintainers to merge your PR and have the workflow generate a hash for it

## Verified Modules Registry

The system maintains a registry of verified modules in `src/settings/verified_modules.json`:

```json
{
  "example_module": {
    "hash": "e7a5d6c8f3b2a1...",
    "signature": "a1b2c3d4e5f6...",
    "version": "1.0.0",
    "date_verified": "2025-03-15T12:00:00Z",
    "repo": "https://github.com/lachlanharrisdev/PROJECT-EIDOLON"
  }
}
```

## Manually Verifying a Module

You can manually verify a module's integrity:

```python
from core.security.utils import verify_module, get_public_key

public_key = get_public_key()
is_verified = verify_module("your_module_name", public_key)

if is_verified:
    print("Module verified successfully")
else:
    print("Module verification failed")
```

## Reporting Security Issues

If you discover a security vulnerability in Project Eidolon:

1. **Do not disclose publicly**: Don't create a public issue
2. **Contact maintainers directly**: Join the [discord server](https://discord.gg/wDcxk4pCs5)
3. **Provide details**: Include steps to reproduce and potential impact
4. **Allow time for fixes**: Follow responsible disclosure practices

Please read the [security policy](https://github.com/lachlanharrisdev/PROJECT-EIDOLON/security/policy) on the repository for more information about vulnerability reporting

For information about implementing module methods securely, see the [module methods documentation](methods.md).