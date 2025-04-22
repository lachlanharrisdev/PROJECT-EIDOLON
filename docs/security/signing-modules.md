# Module Signing Guide

This guide explains how module authors can sign their modules to distribute them securely.

## Prerequisites

To sign a module, you need:

1. A private/public key pair for signing
2. Your module's code finalized and ready for distribution

## Generating a Key Pair

If you don't already have a key pair, you can generate one using Eidolon's built-in key generation tool:

```bash
eidolon security generate-keypair --output-dir ~/.eidolon/keys --prefix my_signing
```

This will create two files:
- `my_signing_private_key.pem`: Your private signing key (keep secure)
- `my_signing_public_key.pem`: Your public key (can be shared)

By default, your private key will be password-protected. You'll be prompted to enter a password during generation.

### Key Protection

Your private key should be protected:

- Store it in a secure location
- Use a strong password
- Never share it with others
- Back it up securely

## Signing a Module

Once your module is ready for distribution, sign it using:

```bash
eidolon security sign --key ~/.eidolon/keys/my_signing_private_key.pem /path/to/your/module
```

This creates a detached signature file (`module.sig`) in your module directory. The signature file contains a cryptographic signature of the content hash of your module.

### Options for the Sign Command

```
--key, -k TEXT                 Path to the private key file  [required]
--output, -o PATH              Path to save the signature (default: module_path/module.sig)
--extract-pubkey, -p PATH      Path to save the extracted public key
--id, -i TEXT                  Suggested signer ID to use when importing the public key
--prompt-password/--no-prompt-password
                               Whether to prompt for a private key password  [default: True]
```

## Extracting Your Public Key

If you want to share your public key with users so they can verify your modules, you can extract it during the signing process:

```bash
eidolon security sign --key my_private_key.pem --extract-pubkey my_public_key.pem --id "your_name" /path/to/module
```

The `--id` parameter suggests an identifier users can use when adding your key to their trusted signers list.

## Distributing Your Module

When distributing your module:

1. Include the `module.sig` file with your module
2. Share your public key with users who will run your module
3. Provide instructions for users to add your key to their trusted signers (see below)

## Instructions for Users

Include these instructions for your users:

1. Save the public key to a file (e.g., `your_name_pubkey.pem`)
2. Add it to their trusted signers:

```bash
eidolon security trust --key your_name_pubkey.pem --id "your_name" --comment "Your description"
```

## Verifying Your Signature

To verify that your signature works correctly:

```bash
eidolon security verify /path/to/your/module
```

If you haven't added your own key to your trusted signers, it will show as "SIGNED (by untrusted signer)".

## Best Practices

1. **Version-Specific Signatures**: Sign each release of your module separately
2. **Clear Documentation**: Document your signing ID for consistent trust establishment
3. **Key Rotation**: Periodically update your signing keys (yearly is a common practice)
4. **Transparency**: Publish your public key fingerprint on your website or repository