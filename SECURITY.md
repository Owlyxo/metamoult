# Security Policy

## What counts as a security problem here

- **Metadata that survives `clean`** when metamoult says the copy is clean.
  For a privacy tool this is a security bug.
- **Network access or data leaving your computer.** metamoult must work fully
  offline.
- **Malicious files** that crash the program, use huge amounts of memory or disk
  (for example decompression bombs), or write outside the intended folder.
- The original file being modified or overwritten.

Not security problems (see "Limits" in the README): content visible in a
picture, file names, or formats that are not supported.

## How to report

Please do **not** open a public issue for a security problem. Use GitHub's
private reporting instead: open the **Security** tab of this repository and
choose **Report a vulnerability**. If that is not available, contact the
maintainer through their GitHub profile ([@Owlyxo](https://github.com/Owlyxo))
and ask for a private channel.

Please include the file type, the steps to reproduce and, if possible, a small
**artificial** sample file. Do not send real private files.

## Supported versions

Only the latest release is maintained. This is a small project run by one
person in their spare time, so replies are best-effort and no response time is
promised.
