# Module Signing Guide

To allow module creators to create verified modules without having to make them come default with Eidolon, creators can sign their own modules & allow users to trust any modules built by that creator.

## Prerequisites

To sign a module, you need:

1. A private/public key pair for signing
  
2. Your module's code finalized and ready for distribution
  

!!! note "Why does it need to be ready?"

```
The signing algorithm takes all of the source code for your module & 
encodes it using the keypair. When it's decoded, if any of the decoded
content doesn't match the current version, then the module can't be
trusted
```

## Generating a Key Pair

If you don't already have a key pair, you can generate one using Eidolon's built-in key generation tool:

```bash
eidolon security generate-keypair --output-dir ~/.eidolon/keys --prefix my_signing
```

Where:

| Argument | Description | Default |
| --- | --- | --- |
| --output-dir \<dir\>, | The directory to save your keys to | .   |
| --prefix \<prefix\> | The text within each file name before `_private_key` and `_public_key` | eidolon |
| --size \<integer\> | Key size in bits (2048, 3072 or 4096) | 2048 |
| --with-password, --no-password | Whether to password-protect the private key | --with-password |
| --help | Display help for this command |     |

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
  

Giving away access to your private key allows attackers to create modules & verify them under your name.

## Signing a Module

Once your module is ready for distribution, sign it using:

```bash
eidolon security sign --key ~/.eidolon/keys/my_signing_private_key.pem /path/to/your/module
```

Where:

| Argument | Description | Default / Required |
| --- | --- | --- |
| --key, -k | Path to the private key file | [Required] |
| --output, -o | Path to save the signature | module_path/module.sig |
| --extract-pubkey, -p | Path to save the extracted public key | .   |
| --id, -i | Suggested signer ID to use when importing the public key |     |
| --prompt-password/--no-prompt-password | Whether to prompt for a private key password | True |

This creates a detached signature file (`module.sig`) in your module directory. The signature file contains a cryptographic signature of the content hash of your module.

## Extracting Your Public Key

If you want to share your public key with users so they can verify your modules, you can extract it during the signing process:

```bash
eidolon security sign --key my_private_key.pem --extract-pubkey my_public_key.pem --id "your_name" /path/to/module
```

The `--id` parameter suggests an identifier users can use when adding your key to their trusted signers list.

Otherwise, your public key is stored wherever you set the file path to when you ran the `eidolon security generate-keypair` command at the start of this document.

## Distributing Your Module

Currently, there is no module registry out there, so users will have to manually trust you. The only way they can do this is by providing them with your public key.

When distributing your module:

1. Include the `module.sig` file with your module
  
2. Optionally include a `public_key.pem` file within your module
  
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