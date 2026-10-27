# Responsible and Ethical AI Use

QUILL and several apps in the QuillVille family include optional AI-assisted
features. These features are designed to be user-controlled and review-first.

## Responsible-use policy

1. AI output is advisory, not authoritative.
2. You must review all generated output before applying, publishing, or sharing it.
3. You are fully responsible for downstream use of AI-generated content.
4. Do not use AI features to violate privacy, law, policy, or intellectual-property rights.
5. Avoid sending sensitive, regulated, or confidential data to cloud providers unless you are explicitly authorized.

## Trust controls in QUILL

- explicit user-initiated AI actions
- approval flow before document-changing actions
- plain-language connection and status messaging
- startup trust and consent acknowledgement
- QUILL's free AI service stays off until you agree to what it sends and keeps
- secure key handling: Windows Credential Manager in installed copies, a
  DPAPI-encrypted file in portable copies, never plain text

## Provider boundaries

When a cloud provider is selected, prompts you send are processed under that
provider's terms and retention policy. QUILL cannot override provider-side
policy behavior. QUILL's free AI service passes your request to OpenAI, so
OpenAI's terms apply to it too; the [Privacy Statement](PRIVACY.md) says exactly
what that service keeps.

For highest privacy, prefer local model backends when available.
