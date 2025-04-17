# // SECURITY POLICY

![Banner](/.github/images/Banner_security_2x1.jpg)

## REPORTING

**DO NOT REPORT VULNERABILITIES IN ANY PUBLIC LOCATIONS, THIS INCLUDES GITHUB DISCUSSIONS & ISSUES**

Instead, please raise a ticket in `#ticket-tool` in [the discord](https://discord.gg/wDcxk4pCs5).

Please include as much of the following information as possible to help us better understand the possible issue:

* Type of issue (e.g. exposing private information to public internet)
* Full paths of source file(s) related to the manifestation of the issue
* The location of the affected source code (tag/branch/commit)
* Any special configuration required to reproduce the issue
* Step-by-step instructions to reproduce the issue
* Proof-of-concept or exploit code
* Impact of the issue, including how an attacker might exploit the issue

This information will help us triage your report more quickly.

<br/>

## MODULES

Modules are isolated folders containing code for separate pieces of functionality. Modules can specify multiple different
inputs & outputs (identified by a name) which it will subscribe to via a central message bus.

To allow module creators ultimate flexibility, their contents is unrestricted & unfiltered, with the only requirement to
run within the application is a `module.yaml` file and any `.py` file referenced by said `module.yaml` file.
This means that attackers or users with malicious intent could coerce you into downloading & running their modules,
which contain malicious code that could pose a critical security threat to you & your machine.

To combat this, we've implemented a signed hash system integrated with the github CI/CD pipeline to verify any modules
created within this repository. Any modules that are maintained by this repository will be verified, and it will be shown
in the logs when running the application:
```
2025-01-01 13:00:00,500: INFO @__name__ - Module default_module VERIFIED [engine_core.py:87]
```

Any modules loaded that are NOT verified will appear with an UNVERIFIED tag shown in the CLI, including the reason for it not being verified:
```
2025-01-01 13:00:00,500: INFO @__name__ - Module third_party_module UNVERIFIED (directory name not found in self.verified_modules) [engine_core.py:87]
```

> *CLI output structure subject to change, these are examples that match as of 17/04/25*

<br/>


## VULNERABILITIES VS BUGS

We classify vulnerabilities as a type of bug which pose a security threat to the device or device owner running
or storing this program. Vulnerabilities can lead to individuals with malicious intent being able to exploit
a part of this program, and cause various types of damage, including but not limited to:
- Privelege escalation within the users device
- Exposing of sensitive information (passwords, address, contact details etc.)
- Corruption or destruction of data
- Unauthorised access to computer hardware (camera, microphone, GPS etc.)

Bugs should be reported via the issues tab, while vulnerabilities should be reported privately to an administrator,
repository owner or trusted contributor. The best way to do this is via [the discord](https://discord.gg/wDcxk4pCs5),
where you should navigate to `#ticket-tool` and raise a ticket.

---

Thank you in advance for taking the time to submit a report.
