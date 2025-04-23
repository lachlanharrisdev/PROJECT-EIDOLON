# Module Verification and Security

> **Note:** The security verification system has been updated. Please see the [Security Documentation](../security/model.md) for the latest information.

This document provides an overview of Eidolon's security mechanisms for module verification.

## Security Model

Project Eidolon uses a multi-signer trust model to ensure users are aware when they are running unverified modules. This security model is crucial for OSINT workflows where data integrity and protection against malicious code are paramount concerns.

### Key Components

1. **Public/Private Key Infrastructure**: A distributed cryptographic signing system for modules
2. **Module Signature Files**: Detached signatures stored as `module.sig` files
3. **Trusted Signers**: A registry of trusted public keys that verify module authenticity
4. **Security Modes**: Configurable security levels (paranoid, default, permissive)

## Creating Signed Modules

Module authors can sign their modules using their private keys:

```bash
eidolon security sign --key your_private_key.pem /path/to/your/module
```

For detailed instructions on signing modules, see the [Module Signing Guide](/docs/security/signing-modules.md).

## Verifying Modules

To manually verify a module's authenticity:

```bash
eidolon security verify /path/to/module
```

This will check if the module's signature is valid and was created by a trusted signer.

## Managing Trusted Signers

Users can manage which module authors they trust:

```bash
# List trusted signers
eidolon security list-trusted

# Add a trusted signer
eidolon security trust --key author_public_key.pem --id "author_name" --comment "Description"

# Remove a trusted signer
eidolon security untrust author_name
```

For complete details on managing trusted signers, see [Managing Trusted Signers](/docs/security/trusted-signers.md).

## Security Configuration

Eidolon provides three security modes:

1. **Paranoid**: Only verified modules from trusted signers are allowed
2. **Default**: Prompts for untrusted modules, allows verified modules automatically
3. **Permissive**: Allows all modules with appropriate warnings

Configure the security mode when running Eidolon:

```bash
eidolon run --security-mode=paranoid my_pipeline
```

For full security configuration options, see [Security Configuration](/docs/security/configuration.md).

## Reporting Security Issues

If you discover a security vulnerability in Project Eidolon:

1. **Do not disclose publicly**: Don't create a public issue
2. **Contact maintainers directly**: Join the [discord server](https://discord.gg/wDcxk4pCs5)
3. **Provide details**: Include steps to reproduce and potential impact
4. **Allow time for fixes**: Follow responsible disclosure practices

Please read the [security policy](https://github.com/lachlanharrisdev/PROJECT-EIDOLON/security/policy) on the repository for more information about vulnerability reporting.