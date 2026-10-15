---
name: arch-packager
description: >-
  Use this skill when the user asks to install a third-party binary, script, or GitHub release on Omarchy or Arch Linux, especially when they provide a URL or ask to bypass the package manager.
---

# Arch Packager Skill (Extreme Security Edition)

This skill teaches the agent how to natively package third-party software for Arch Linux while strictly enforcing **Human-in-the-Loop** verification and **Extreme Security** integrity checks. 

## The Core Philosophy
Never blindly trust downloads. Never use `updpkgsums` to generate hashes from unverified payloads (which introduces a Trust-on-First-Use vulnerability). Always explicitly present URLs, signatures, and scripts to the human system administrator for authorization.

## Process

1. **Upstream Discovery & Heuristic Security Scan**: 
   - Identify the official download URL, release notes URL, and any cryptographic signatures (`.sig`, `.asc`, Sigstore, SLSA provenance).
   - Search the upstream repository's issue tracker for reports of "malware" or "compromised" releases.
   - Fetch the **official checksums** directly from the upstream API or release notes. **DO NOT locally compute the hash yet.**

2. **Draft the `PKGBUILD`**:
   - Write a `PKGBUILD` file in `~/builds/<pkgname>-bin`.
   - **Checksums**: Hardcode the officially published upstream checksums into the `sha256sums` array.
   - **Signatures**: If a PGP signature exists, add it to the `source` array and populate `validpgpkeys=('FINGERPRINT')`.
   - *Note*: If the binary is precompiled and bundled, add `options=('!strip')` to prevent corruption.

3. **CRITICAL JUNCTURE 1: Security Approval Pause**:
   - **HALT EXECUTION.** Do not download files or run `makepkg`.
   - Present the user with a **Security Approval Summary** containing:
     - The official Update/Release Link.
     - The direct Download Links (including signature files).
     - The Upstream Checksums you extracted.
     - A diff/preview of the `PKGBUILD`, especially highlighting shell commands in `prepare()`, `build()`, or `package()`.
   - **Ask the user**: *"Please review the download links, upstream checksums, and scripts. Do you approve proceeding with the build?"* Wait for their explicit authorization.

4. **Rigorous Checksum Validation**:
   - Only after human approval, allow the system to download the files.
   - The user or the AI runs `makepkg` (or `makepkg -g` / `updpkgsums` ONLY IF cross-referencing against the already-approved upstream hashes). 
   - If the downloaded file's hash does not perfectly match the upstream hash approved by the human, **ABORT** and warn of a supply-chain attack.

5. **CRITICAL JUNCTURE 2: Payload Inspection & Handoff**:
   - Once `makepkg` successfully generates the `.pkg.tar.zst` file, **HALT EXECUTION**.
   - Do NOT run `pacman -U` automatically.
   - Advise the user to inspect the package payload structure: `pacman -Qlp <package.pkg.tar.zst>` to ensure no files overwrite system directories (`/usr/bin`, `/etc`).
   - Hand over the final installation command to the user: `sudo pacman -U <path-to-pkg.tar.zst>`.

## Handling Updates
1. Extract the new version's official upstream checksums and release URL.
2. Update the `pkgver` and `sha256sums` arrays in the `PKGBUILD` with the trusted upstream values.
3. Pause for **Juncture 1** human authorization.
4. Build and hand off at **Juncture 2**.
