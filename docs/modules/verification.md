# Module Verification and Security

This document explains the security mechanisms in Project Eidolon's module system, including the verification process, cryptographic signing, and best practices for securing modules.

## Security Model

Project Eidolon uses a security model based on cryptographic signatures to ensure users are aware when they are running unverified modules (that is, modules not officially a part of the project eidolon repository). This can help reduce the chance of malicious attacks based on phishing.

### Key Components

1. **Public/Private Key Infrastructure**: A keypair-based signing system for modules
2. **Module Hash Generation**: Automatic hashing of module code files
3. **Verification System**: Pre-execution validation of module hashes
4. **Verified Module Registry**: A record of modules that have passed verification

## Module Verification Process

The verification process occurs automatically when modules are loaded:

```
┌─────────────┐     ┌────────────────┐     ┌──────────────────┐
│ Module Code │────►│ Hash Generator │────►│ Signature Check  │
└─────────────┘     └────────────────┘     └──────────┬───────┘
                                                      │
                                                      ▼
┌─────────────┐     ┌────────────────┐     ┌──────────────────┐
│Module Loaded│◄────│ Verified List  │◄────│ Verification OK? │
└─────────────┘     │ Management     │     └──────────┬───────┘
                    └────────────────┘                │
                           ▲                          │  
                           │                          │  
                    ┌──────┴───────┐                  │  
                    │  Skip if in  │◄─────────────────┘
                    │ Verified List│      
                    └──────────────┘
```

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

## Security Best Practices

When developing modules for Project Eidolon:

### Code Security

1. **Validate all inputs**: Never trust data from external sources
2. **Sanitize output**: Prevent injection attacks in logs or display output
3. **Use secure defaults**: Always initialize with secure configuration
4. **Limit permissions**: Only request the minimum necessary permissions
5. **Keep dependencies updated**: Regularly update external libraries

### Data Processing

1. **Validate before processing**: Check data types and format before processing
2. **Handle parsing errors**: Gracefully handle malformed data
3. **Limit resource usage**: Prevent memory/CPU abuse from large inputs

```python
def handle_input(self, data: Any) -> None:
    if not isinstance(data, dict):
        self._logger.warning(f"Invalid data type: {type(data)}")
        return
        
    if "text" not in data:
        self._logger.warning("Required field missing")
        return
        
    if len(data["text"]) > self.MAX_TEXT_LENGTH:
        data["text"] = data["text"][:self.MAX_TEXT_LENGTH]
        
    self._process_text(data["text"])
```

## Handling Sensitive Data

When your module processes sensitive data:

1. **Minimize storage**: Only store what's absolutely necessary
2. **Implement timeouts**: Automatically clear sensitive data after use
3. **Log carefully**: Avoid logging sensitive information
4. **Clear memory**: Explicitly clear sensitive data from memory when done

```python
def process_sensitive_data(self, data: Dict[str, Any]) -> None:
    try:
        api_key = data.get("credentials", {}).get("api_key")
        if not api_key:
            self._logger.error("Required API credentials missing")
            return
            
        result = self._call_external_api(api_key, data["query"])
        self._process_result(result)
        
    finally:
        # Clear sensitive data
        if "api_key" in locals():
            del api_key
```

## Runtime Security Checks

Modules can implement runtime security checks:

```python
def run(self, messagebus: MessageBus) -> None:
    if not self._verify_environment():
        self._logger.error("Insecure environment detected")
        return
        
    self._process_data()
    messagebus.publish("results", self.results)
    
def _verify_environment(self) -> bool:
    if not hasattr(ssl, "PROTOCOL_TLS_CLIENT"):
        return False
        
    config_path = os.path.join(self._get_module_path(), "config")
    if os.path.exists(config_path):
        permissions = oct(os.stat(config_path).st_mode & 0o777)
        if permissions != "0o600":
            return False
            
    return True
```

## Securely Connecting to External Services

When connecting to external services:

1. **Use HTTPS**: Always use encrypted connections
2. **Verify certificates**: Validate SSL/TLS certificates
3. **Implement timeouts**: Prevent hanging on unresponsive services
4. **Handle connection errors**: Gracefully handle service outages

```python
def _make_api_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    import requests
    from requests.exceptions import RequestException, Timeout, SSLError
    
    try:
        response = requests.post(
            f"https://api.example.com/{endpoint}",
            json=data,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=(3, 27),
            verify=True
        )
        
        response.raise_for_status()
        return response.json()
        
    except Timeout:
        self._logger.error("Timeout connecting to API")
        return {"error": "connection_timeout"}
        
    except SSLError:
        self._logger.error("SSL certificate verification failed")
        return {"error": "ssl_verification_failed"}
        
    except RequestException as e:
        self._logger.error(f"API request failed: {str(e)}")
        return {"error": "request_failed"}
```

## Security Testing

Include security tests in your module tests as described in the [testing documentation](tests.md):

```python
def test_input_validation(test_module):
    malicious_input = {"__proto__": {"polluted": True}}
    test_module.handle_input(malicious_input)
    
    assert not hasattr(test_module, "polluted")

def test_large_input_handling(test_module):
    large_text = "A" * (10 * 1024 * 1024)  # 10 MB string
    large_input = {"text": large_text}
    
    test_module.handle_input(large_input)
    
    assert len(test_module.input_data.get("text", "")) <= test_module.MAX_TEXT_LENGTH
```

## Reporting Security Issues

If you discover a security vulnerability in Project Eidolon:

1. **Do not disclose publicly**: Don't create a public issue
2. **Contact maintainers directly**: Join the [discord server](https://discord.gg/wDcxk4pCs5)
3. **Provide details**: Include steps to reproduce and potential impact
4. **Allow time for fixes**: Follow responsible disclosure practices

Please read the [security policy](https://github.com/lachlanharrisdev/PROJECT-EIDOLON/security/policy) on the repository for more information about vulnerability reporting

For information about implementing module methods securely, see the [module methods documentation](methods.md).