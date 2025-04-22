# Security Configuration

This guide explains how to configure security settings in Eidolon to match your security needs.

## Security Modes

Eidolon supports three security modes that control how the system handles module verification:

| Mode | Description | Use Case |
|------|-------------|----------|
| `default` | Prompts for unverified modules | General use in most scenarios |
| `paranoid` | Only allows verified modules from trusted signers | High-security environments or production |
| `permissive` | Allows all modules with appropriate warnings | Development or testing environments |

## Setting the Security Mode

You can configure the security mode via the command line when running Eidolon:

```bash
eidolon run --security-mode=paranoid my_pipeline
```

Available modes:
- `default`: The standard security setting
- `paranoid`: Maximum security
- `permissive`: Minimal security checks

## Allowing Unverified Modules

To bypass security prompts for unverified modules:

```bash
eidolon run --allow-unverified my_pipeline
```

This flag is useful for batch processing or scripted environments where interactive prompts are not desirable.

## Understanding Security Prompts

In the default security mode, you'll be prompted when Eidolon encounters an unsigned or untrusted module:

```
⚠️  SECURITY WARNING: Module 'example_module' is unsigned
This module has not been verified by any trusted signer.
Running unverified modules can be a security risk.

Do you want to proceed with this module? (yes/no/always): 
```

Options:
- `yes`: Allow the module for this run only
- `no`: Block the module from running
- `always`: Allow this and future unverified modules for this session

## Security Mode Behavior Reference

| Module Status | Paranoid Mode | Default Mode | Permissive Mode |
|---------------|---------------|--------------|-----------------|
| Verified | Allowed automatically | Allowed automatically | Allowed automatically |
| Signed by untrusted signer | Blocked | User prompt | Allowed with warning |
| Unsigned | Blocked | User prompt | Allowed with warning |
| Invalid signature | Blocked | User prompt | Allowed with warning |

## Recommended Practices

1. **Development**: Use `permissive` mode for rapid development
2. **Testing**: Use `default` mode when testing modules
3. **Production**: Use `paranoid` mode to ensure maximum safety

## Combining with Other Security Measures

For improved security, consider:

1. **Regular Key Rotation**: Update and rotate trusted signing keys periodically
2. **System User Restrictions**: Run Eidolon under a restricted user account
3. **Network Controls**: Use firewall rules to restrict module network access
4. **Pipeline Review**: Carefully review pipelines before execution

## Using Security Verification in Scripts

When using Eidolon in scripts or automated workflows, include the appropriate security flags:

```bash
# For maximum security in production
eidolon run --security-mode=paranoid production_pipeline

# For unattended operation (security warnings are logged but won't block execution)
eidolon run --security-mode=permissive --allow-unverified batch_pipeline
```