# Managing Trusted Signers

This guide explains how to manage your trusted signers in Eidolon's security system.

## Understanding Trusted Signers

In Eidolon's security model, trusted signers are individuals or organizations whose public keys you trust to verify modules. Rather than relying on a centralized authority, you decide which module authors you trust.

Trusted signers are stored in `src/settings/trusted_signers.json`.

## Viewing Your Trusted Signers

To see which signers you currently trust:

```bash
eidolon security list-trusted
```

This will display a table of all trusted signers, including:
- **ID**: The unique identifier for the signer
- **Description**: A human-readable description of the signer
- **Key Fingerprint**: A preview of the public key

## Adding a Trusted Signer

When you obtain a public key from a module author you trust, add it to your trusted signers using:

```bash
eidolon security trust --key author_public_key.pem --id "author_name" --comment "Trusted module author"
```

Where:
- `--key`: Path to the author's public key file
- `--id`: A unique identifier for this signer (used in verification reports)
- `--comment`: Optional description or reason for trusting this signer

### Example

```bash
eidolon security trust --key alice_key.pem --id "alice" --comment "Alice from Cybersecurity Inc."
```

## Removing a Trusted Signer

If you no longer wish to trust modules signed by a particular signer:

```bash
eidolon security untrust author_name
```

For example:
```bash
eidolon security untrust alice
```

## Trust Considerations

When deciding whether to trust a signer, consider:

1. **Source Verification**: Did you obtain the public key directly from the author through a secure channel?
2. **Reputation**: Does the module author have a good reputation in the community?
3. **Purpose**: What kind of modules will you be running from this signer?

## The Official Eidolon Signer

By default, Eidolon includes a trusted signer entry for the official Eidolon project, which signs the core modules. It's recommended to keep this trusted signer unless you have specific reasons to remove it.

## Verifying Modules After Adding Signers

After adding a new trusted signer, you can verify modules signed by them:

```bash
eidolon security verify /path/to/module
```

If the module was signed by one of your trusted signers, you'll see:
```
✓ Module 'module_name' VERIFIED
  Signed by: signer_id
```

## Understanding the Trusted Signers File

The `trusted_signers.json` file uses the following format:

```json
{
  "signer_id": {
    "pubkey": "-----BEGIN PUBLIC KEY-----\n...public key in PEM format...\n-----END PUBLIC KEY-----",
    "comment": "Description of the signer"
  }
}
```

You can manually edit this file if necessary, but it's recommended to use the provided CLI commands instead.