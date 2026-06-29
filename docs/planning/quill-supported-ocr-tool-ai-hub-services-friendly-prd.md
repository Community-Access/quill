# PRD: QUILL Supported OCR Tool, AI Hub Services Tab, and Datalab Chandra OCR Integration

**Product:** QUILL  
**Feature area:** Supported OCR tool, AI Hub, document import, accessible document conversion  
**Status:** Draft for implementation planning  
**Owner:** Jeff Bishop / QUILL project  
**Last researched:** 2026-06-29  
**Primary audience:** QUILL maintainers, implementation agents, accessibility reviewers, release manager

---

## 1. Executive Summary

QUILL should ship a **first-class, supported OCR and document conversion tool**. This should not feel like a hidden AI experiment, a plugin-only feature, or an advanced developer service. It should be a real QUILL tool that users can rely on from the main application.

The AI Hub should add a **Services** tab that configures the providers behind this supported OCR tool. This tab must be customer-facing, friendly, and informative — not a sparse technical settings page. It should explain what each service does, why a user might choose it, what files it supports, what privacy tradeoffs exist, how billing works, and provide direct buttons to the provider’s website, documentation, pricing, API key page, and privacy/security information.

The first provider should be **Datalab Document Conversion / Chandra OCR**, exposed in configuration as **Datalab Chandra OCR Service**.

The user-facing feature should be named something like **QUILL OCR and Document Conversion** or **Import with OCR / Convert Document**. It should let a user open a scanned PDF, image, Office document, spreadsheet, presentation, HTML file, or EPUB; send it to Datalab with explicit consent; receive structured Markdown, HTML, JSON, or chunks; and open the result directly in QUILL as an editable, screen-reader-friendly document.

The experience should be magical for blind and keyboard-only users:

- A simple, friendly import flow: **File → Import with OCR / Convert Document**.
- Sensible defaults: **Balanced mode**, **editable Markdown**, page delimiters enabled for multi-page documents.
- Rich advanced controls for power users.
- A provider-agnostic architecture so QUILL can later support Azure Document Intelligence, Mistral OCR, AWS Textract, Google Document AI, local Tesseract, local Marker, or an institutional on-prem endpoint.
- An accessible **OCR Review Mode** that turns noisy OCR output into a guided correction and verification workflow.

This is not just “OCR.” It is a full document rescue and conversion pipeline for making inaccessible, scanned, or structurally messy documents editable and understandable.

---

## 2. Source Research Summary

### 2.1 Datalab and Chandra facts relevant to implementation

Datalab’s Convert API converts documents to **Markdown, HTML, JSON, or chunks** and supports `fast`, `balanced`, and `accurate` processing modes. Datalab recommends `balanced` for most use cases, `fast` for simple/high-throughput documents, and `accurate` for scanned documents, complex tables, or dense layouts.

Sources:

- [Datalab Convert API overview](https://documentation.datalab.to/docs/recipes/conversion/conversion-api-overview)
- [Datalab SDK document conversion](https://documentation.datalab.to/docs/welcome/sdk/conversion)
- [Datalab API overview](https://documentation.datalab.to/docs/welcome/api)

The Python SDK supports:

```python
from datalab_sdk import DatalabClient, ConvertOptions

client = DatalabClient()
options = ConvertOptions(
    output_format="markdown",
    mode="balanced",
    paginate=True,
)
result = client.convert("document.pdf", options=options)
print(result.markdown)
```

The SDK requires Python 3.10+ and is installed with:

```bash
pip install datalab-python-sdk
```

Sources:

- [Datalab Python SDK docs](https://documentation.datalab.to/docs/welcome/sdk)
- [Datalab Python SDK on PyPI](https://pypi.org/project/datalab-python-sdk/)

Datalab’s REST API uses:

```http
POST https://www.datalab.to/api/v1/convert
X-API-Key: YOUR_API_KEY
```

The API returns a `request_id` and `request_check_url`; clients poll until processing is complete. Datalab says results are deleted from its servers one hour after processing completes, so QUILL must retrieve promptly and store only what the user asks to keep.

Source:

- [Datalab API overview](https://documentation.datalab.to/docs/welcome/api)

Supported file types include:

- PDF: `.pdf`
- Spreadsheets: `.xls`, `.xlsx`, `.xlsm`, `.xltx`, `.csv`, `.ods`
- Word documents: `.doc`, `.docx`, `.odt`
- Presentations: `.ppt`, `.pptx`, `.odp`
- HTML: `.html`
- EPUB: `.epub`
- Images: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.tiff`

Source:

- [Datalab supported file types](https://documentation.datalab.to/docs/common/supportedfiletypes)

Current documented limits:

- 200 MB maximum file size for PDFs, images, and Office documents.
- 7,000 pages maximum per request.
- Free tier: 10 requests per minute and 5 concurrent requests.
- Team plan: 200 requests per minute and 400 concurrent requests.
- Concurrent pages in flight: 5,000.

Source:

- [Datalab API limits and rate limiting](https://documentation.datalab.to/docs/common/limits)

Security and data-handling guidance:

- Store API keys in environment variables or secure storage; never hardcode or commit them.
- Use per-key spend limits.
- Rotate keys if compromised.
- Do not log webhook secrets or sensitive document payloads.
- Results are automatically deleted from Datalab servers one hour after processing completes.
- Datalab has an opt-in setting for using documents to improve models.
- For on-prem deployments, the container should be placed behind TLS, protected by network controls, and authenticated externally.

Source:

- [Datalab security best practices](https://documentation.datalab.to/platform/security)

Pricing and billing notes:

- Datalab uses per-page pricing; add-ons such as word bounding boxes and table/list bounding boxes are additive.
- New accounts receive a monthly free allowance: $20/month for work email accounts and $10/month for personal email accounts.
- Pay-as-you-go has no subscription or minimum spend after adding a payment method.
- Team plan is documented at $400/month and includes $400 of monthly usage, production rate limits, clickthrough BAA/DPA, SOC 2 report access, and additional custom processor capacity.
- Current public search results for the Datalab pricing page list Convert `fast` / `balanced` at **$4 per 1,000 pages**. Treat this as volatile and always link to Datalab’s pricing page rather than hard-coding rates in QUILL UI.

Sources:

- [Datalab billing docs](https://documentation.datalab.to/platform/billing)
- [Datalab pricing page](https://www.datalab.to/pricing)

Chandra OCR 2 specifics:

- Chandra OCR 2 outputs Markdown, HTML, and JSON while preserving layout.
- It supports 90+ languages.
- It has strong support for handwriting, tables, math, forms, checkboxes, images, diagrams, captions, and structured data.
- The open-source package supports vLLM and Hugging Face inference modes.
- The Datalab managed platform states it runs an improved Chandra with higher accuracy than open weights, zero data retention by default, SOC 2 Type 2, and custom BAAs.
- The Chandra repository says commercial self-hosting requires a license.

Sources:

- [Chandra OCR 2 GitHub repository](https://github.com/datalab-to/chandra)
- [Chandra OCR 2 model card on Hugging Face](https://huggingface.co/datalab-to/chandra-ocr-2)
- [Datalab Chandra 2 announcement](https://www.datalab.to/blog/chandra-2)

On-prem / enterprise option:

- Datalab offers paid on-prem options for teams with data privacy, regulated-environment, high-volume, customization, or SLA needs.
- Datalab says its container image mimics the cloud-hosted API for a simpler transition.

Source:

- [Datalab on-prem overview](https://documentation.datalab.to/docs/on-prem/overview)

---

## 3. Product Positioning: OCR Is a Supported QUILL Tool

This PRD must treat OCR as a **supported QUILL tool**, not just a service connector.

The Datalab Chandra integration is the first provider implementation, but the product feature is:

> **QUILL OCR and Document Conversion**

This tool should appear in normal QUILL workflows, have help documentation, have stable menu placement, have accessible status and error handling, and be included in release notes as a supported feature.

### 4.1 User-facing promise

QUILL should be able to say:

> QUILL includes a supported OCR and document conversion tool for turning scanned, image-based, and poorly structured documents into editable, accessible content.

### 4.2 Required product surfaces

OCR must be available from the main app, not only from AI Hub settings.

Required surfaces:

```text
File
  Import with OCR / Convert Document...

Tools
  OCR and Document Conversion
    Import with OCR...
    Review Last OCR Result...
    OCR Service Settings...
    Delete OCR Temporary Files...

AI Hub
  Services
    Datalab Chandra OCR Service
```

Recommended Help menu entries:

```text
Help
  QUILL Help
    OCR and Document Conversion
    OCR Privacy and Cloud Services
    Supported OCR File Types
    Troubleshooting OCR
```

### 4.3 What “supported” means

For this PRD, **supported** means:

1. The OCR tool is part of QUILL’s documented feature set.
2. It is reachable from standard menus.
3. It has user-facing help.
4. It has clear error messages.
5. It has privacy and upload consent UX.
6. It has regression tests.
7. It has screen-reader testing requirements.
8. It has release-note coverage.
9. It has diagnostic logging that does not expose secrets or document content.
10. It can be disabled or left unconfigured without breaking QUILL.
11. It is not labeled “experimental” once MVP acceptance criteria are met.
12. Provider-specific failures are handled as service failures, not as QUILL crashes.

### 4.4 Supported feature boundary

QUILL supports the OCR workflow and user experience. Datalab provides the first OCR backend.

QUILL should support:

- Opening the import tool.
- Selecting supported files.
- Explaining cloud upload.
- Submitting the file to the configured OCR provider.
- Tracking progress.
- Cancelling the job.
- Retrieving results.
- Opening editable Markdown/HTML/text output.
- Preserving useful structure.
- Guiding review of tables, forms, images, captions, low-confidence text, and page boundaries.
- Saving, exporting, or discarding the converted result.
- Reporting actionable errors.

QUILL should not promise:

- Perfect OCR.
- Perfect reconstruction of every table or form.
- That cloud providers are always available.
- That provider pricing will remain fixed.
- That cloud processing is appropriate for every sensitive document.

### 4.5 Release positioning

Release notes should describe this as a supported QUILL feature:

> QUILL now includes a supported OCR and document conversion tool. You can import scanned PDFs, images, Office files, and other documents, convert them to editable Markdown or HTML, and review the result in an accessible workflow. The first supported provider is Datalab Chandra OCR Service, configurable from AI Hub → Services.

---

### 2.2 Comparable services to plan for later

QUILL should not be locked into one OCR provider. The Services tab should support future provider adapters.

| Provider | Why it matters | Source |
|---|---|---|
| Datalab / Chandra | Best initial fit for QUILL because it directly returns Markdown, HTML, JSON, and chunks; strong complex-layout OCR; service and on-prem paths. | [Datalab Convert API](https://documentation.datalab.to/docs/recipes/conversion/conversion-api-overview) |
| Azure AI Document Intelligence | Layout model can output Markdown; tables changed to HTML table representation in v4.0 GA; strong enterprise story. | [Azure layout model docs](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/layout?view=doc-intel-4.0.0) |
| Mistral OCR | Returns Markdown, document structure metadata, images, tables, hyperlinks, confidence scores, optional block extraction; supports PDFs and images. | [Mistral OCR docs](https://docs.mistral.ai/studio-api/document-processing/basic_ocr) |
| AWS Textract | Strong forms/tables/query/signature extraction and AWS enterprise availability. More JSON-structure oriented than Markdown-first. | [Amazon Textract analyzing documents](https://docs.aws.amazon.com/textract/latest/dg/how-it-works-analyzing.html) |
| Google Document AI | Enterprise Document OCR supports printed and handwritten text in 200+ languages; Form Parser handles key-value pairs, checkboxes, and tables. | [Google Document AI processor list](https://docs.cloud.google.com/document-ai/docs/processors-list) |
| Local Tesseract | Free/offline fallback for plain OCR; supports 100+ languages but weaker on complex layout and modern document understanding. | [Tesseract GitHub repository](https://github.com/tesseract-ocr/tesseract) |

---

## 4. Problem Statement

Many users receive inaccessible or semi-accessible documents:

- Scanned PDFs with no text layer.
- PDFs with bad reading order.
- Images of letters, forms, receipts, or print handouts.
- Word/PDF files where tables are inaccessible.
- Multi-column documents where screen readers read content in the wrong order.
- Forms with checkboxes, signatures, and labels.
- Documents with math, diagrams, captions, handwriting, or low-quality scans.

Current “OCR” workflows often dump unstructured text into the editor and leave the user to clean up the mess. That fails QUILL’s promise to meet people where they are.

QUILL should provide a first-class, accessible, service-backed document conversion workflow that gives users structure, review tools, and confidence.

---

## 5. Product Vision

Add an **AI Hub → Services** tab where users can configure and test document-intelligence services. Then add a **File → Import with OCR / Convert Document** command powered by those services.

The result should feel like this:

> “I opened a PDF that used to be locked away from me. QUILL asked how I wanted it converted, told me clearly that it would be sent to Datalab, gave me a progress update, then opened a clean Markdown document with headings, tables, lists, image captions, and page breaks. When something looked uncertain, QUILL guided me through it.”

---

## 6. Goals

### 6.1 User goals

1. Convert inaccessible PDFs and images into editable Markdown.
2. Preserve document structure whenever possible: headings, lists, tables, forms, checkboxes, images, captions, and page boundaries.
3. Provide a simple default path for nontechnical users.
4. Provide rich advanced settings for power users and institutions.
5. Make cloud upload explicit, understandable, and optional.
6. Allow BYOK API key usage.
7. Support institutional on-prem endpoints.
8. Provide accessible correction/review workflows.

### 6.2 Product goals

1. Establish a reusable **Services** architecture inside AI Hub.
3. Implement Datalab / Chandra as the first document service.
4. Avoid vendor lock-in through a provider adapter abstraction.
5. Make the import pipeline asynchronous, cancellable, recoverable, and screen-reader friendly.
6. Build the foundation for future services: Mistral OCR, Azure Document Intelligence, AWS Textract, Google Document AI, local Tesseract, local Marker, local Chandra, or QUILL-hosted endpoints.

### 6.3 Accessibility goals

1. Every feature must be keyboard accessible.
2. All controls must have meaningful accessible names, roles, states, and descriptions.
3. Progress updates must be announced politely and not spam screen readers.
4. Results must open in controls that support caret navigation and screen-reader reading.
5. Tables must have a guided accessible review path.
6. OCR confidence and warnings must be conveyed textually, not only visually.
7. Avoid emoji or decorative Unicode in status messages by default.

---

## 7. Non-Goals for Initial Release

1. Do not bundle local Chandra OCR 2 in the QUILL installer.
2. Do not require a GPU for the user-facing supported OCR tool when cloud/service-backed OCR is configured.
3. Do not build a full PDF editor.
4. Do not promise perfect reconstruction of every document.
5. Do not silently upload files to any cloud service.
6. Do not make Datalab the only possible service in the architecture.
7. Do not build enterprise billing management in QUILL beyond usage warnings and links.
8. Do not implement automatic remediation of every OCR error in v1.

---

## 8. User Personas

### 8.1 Blind everyday user

Needs to convert a scanned letter, handout, form, or PDF into readable text quickly. They may not understand OCR jargon. They want a safe default and a clear warning before cloud upload.

### 8.2 Blind power user / document fixer

Wants control over page ranges, output type, OCR mode, table handling, image captions, block IDs, word confidence, and correction workflows.

### 8.3 Institutional accessibility worker

Needs to process many documents, may need BAA/DPA, SOC 2, on-prem, auditability, and predictable costs.

### 8.4 Developer / contributor

Needs provider adapters, testable job orchestration, stable service interfaces, and simulated/mock responses for CI.

---

## 9. Proposed Information Architecture

### 9.1 AI Hub

Add a new top-level tab:

```text
AI Hub
  General
  Models
  Prompts
  Agents
  Services    ← new
  Privacy
  Diagnostics
```

The **Services** tab manages external and local services QUILL can call.

### 9.2 Services tab layout

Use an accessible list or tree with detail pane.

```text
Services
  Document Conversion and OCR
    Datalab Chandra OCR Service
    Azure Document Intelligence
    Mistral OCR
    AWS Textract
    Google Document AI
    Local Tesseract
    Local Marker
  Speech and Transcription
    Whisper / Faster Whisper
    Cloud transcription providers
  AI Assistants and Coding Services
    GitHub Copilot
    Claude
    OpenAI-compatible endpoints
```

For v1, only **Datalab Chandra OCR Service** must be fully implemented. Others may appear as disabled “coming later” entries only if this does not clutter or confuse the UI.

### 8.3 Services tab must be friendly and customer-facing

The Services tab must feel like a helpful product page inside QUILL, not a developer settings dialog. Many users will not know what an OCR service, API key, endpoint, or provider means. The UI should explain those concepts in plain language and guide the user toward a successful setup.

The Services tab should answer these questions without requiring the user to leave QUILL:

- What does this service do?
- Why would I use it?
- What kinds of documents can it help with?
- Is it local or cloud-based?
- Will my document be uploaded?
- What output can QUILL create from it?
- Does it cost money?
- Where do I get an API key?
- Where can I read the provider’s privacy, security, and pricing information?
- What should I do if I am part of a school, company, legal office, medical office, or other organization with privacy rules?

Required tone:

- Friendly.
- Plain language.
- Confidence-building.
- Honest about cloud upload and cost.
- Not scary, but not vague.
- Helpful for nontechnical users.
- Detailed enough for power users and institutional users.

### 8.4 Services tab page model

Each service should use a rich detail page with these sections:

```text
Service name
Short plain-language description
Status and setup summary
What this service can do
Best for
Supported file types
Output options
Privacy and data handling
Pricing and account notes
Setup steps
Buttons and links
Advanced technical settings
Diagnostics and troubleshooting
```

### 8.5 Required buttons and links

Each configured cloud service page should include customer-facing buttons. For Datalab, include:

| Button | Purpose |
|---|---|
| Visit Datalab Website | Opens the provider’s main website. |
| Get or Manage API Key | Opens the provider’s API key/account page when known; otherwise opens documentation. |
| View Pricing | Opens the provider’s pricing page. |
| Read Privacy and Security Information | Opens provider security/privacy docs. |
| Read API Documentation | Opens provider API docs. |
| Read Supported File Types | Opens provider supported file types documentation. |
| Test Connection | Verifies whether QUILL can reach the service. |
| Configure This Service | Moves focus to setup fields. |
| Use This Service for OCR | Sets this provider as the default OCR provider. |
| Open QUILL OCR Help | Opens QUILL’s help page for OCR and document conversion. |

Buttons must have clear accessible names. Avoid vague names like “Learn More” when a precise button label is possible.

### 8.6 Datalab Chandra OCR customer-facing description

The Datalab service page should include a friendly description like this:

```text
Datalab Chandra OCR Service helps QUILL turn scanned PDFs, images, forms, tables, and complex documents into editable content. It can return Markdown, HTML, JSON, or structured chunks. For most QUILL users, Markdown is the recommended output because it opens directly in the editor and is easy to read, search, edit, and save.

This is a cloud service. When you convert a document with this provider, QUILL sends the selected file to Datalab, waits for processing, retrieves the result, and opens the converted document for you. QUILL will always ask before uploading a document.
```

### 8.7 Service status summary

At the top of each service page, show a concise status summary:

```text
Status: Ready
Default OCR provider: Yes
Account/API key: Configured
Endpoint: Datalab cloud
Default mode: Balanced
Default output: Markdown
Cloud upload required: Yes
```

Possible status values:

- Ready
- Not configured
- Needs API key
- Disabled
- Connection failed
- Provider unavailable
- Local provider not installed
- Enterprise/on-prem endpoint configured

### 8.8 Plain-language setup steps

Datalab setup should be presented as a numbered checklist:

```text
1. Create or sign in to your Datalab account.
2. Get an API key from Datalab.
3. Paste the API key into QUILL.
4. Choose your default conversion mode.
5. Press Test Connection.
6. Use File → Import with OCR / Convert Document.
```

Add a short explanation of API keys:

```text
An API key is like a password that lets QUILL use your Datalab account. Keep it private. QUILL stores it securely and will not show it in logs.
```

### 8.9 Friendly provider comparison

The Services tab should eventually include a provider comparison view. For v1, it can be a simple informational table with Datalab active and others marked future/planned.

Example:

| Service | Best for | Local or cloud | Status |
|---|---|---|---|
| Datalab Chandra OCR Service | Scanned PDFs, complex layouts, Markdown/HTML conversion | Cloud or enterprise on-prem | Supported |
| Local Tesseract | Basic offline OCR | Local | Planned |
| Azure Document Intelligence | Enterprise Azure environments | Cloud | Planned |
| Mistral OCR | Markdown-first OCR workflows | Cloud | Planned |
| Google Document AI | Google Cloud document processing | Cloud | Planned |
| AWS Textract | AWS forms, tables, and document extraction | Cloud | Planned |

### 8.10 Services tab accessibility requirements

The rich information must remain accessible:

- Use real headings so screen reader users can jump by heading.
- Use normal text controls, tables, lists, buttons, and links.
- Do not rely on icons or color alone.
- Every external link button must say where it goes.
- If a link opens a browser, announce that it opens in the browser.
- Keep provider descriptions readable and concise.
- Put technical settings after friendly overview content.
- Provide a “Copy service summary” button for support requests.
- Provide a “Copy diagnostics without secrets” button.
- Make every section reachable by keyboard.

### 8.11 Customer-facing service summary copy

Add a button named **Copy Service Summary**. It should copy a safe summary like:

```text
QUILL OCR service summary
Provider: Datalab Chandra OCR Service
Status: Ready
Endpoint type: Cloud
Default mode: Balanced
Default output: Markdown
Cloud upload required: Yes
API key present: Yes
API key value: Not included
Last connection test: Successful
```

This helps users ask for support without exposing secrets.

---

## 10. Datalab Chandra OCR Service Configuration UX

### 10.1 Service card

Accessible name:

> Datalab Chandra OCR Service

Description:

> Converts PDFs, images, Office documents, spreadsheets, presentations, HTML, and EPUB files into Markdown, HTML, JSON, or chunks using Datalab’s document conversion service and Chandra OCR.

Fields:

| Field | Control | Default | Notes |
|---|---|---:|---|
| Enable service | Checkbox | Off | User must opt in. |
| API key | Password edit | Empty | Stored in secure credential storage, not plain config. |
| Endpoint | Edit | `https://www.datalab.to` | Allows on-prem or enterprise endpoint later. |
| Default mode | Combo box | Balanced | Fast, Balanced, Accurate. |
| Default output | Combo box | Markdown | Markdown, HTML, JSON, Chunks. |
| Add page delimiters | Checkbox | On | Recommended for screen reader navigation. |
| Extract images | Checkbox | On | Maps extracted images to document output. |
| Generate image captions | Checkbox | On | Valuable for screen-reader users. |
| Default processing region | Combo box | Account default | Account default, US, EU. |
| Confirm before upload | Checkbox | On and locked for v1 | Never silently upload. |
| Save converted copy automatically | Checkbox | Off | User chooses where to save. |
| Show advanced options on import | Checkbox | Off | Simple by default. |
| Monthly usage warning | Number/edit | Optional | Local soft warning only. |

Buttons:

- **Visit Datalab Website**
- **Get or Manage API Key**
- **View Datalab Pricing**
- **Read Datalab Privacy and Security Information**
- **Read Datalab API Documentation**
- **Read Supported File Types**
- **Test Connection**
- **Use This Service for OCR**
- **Open QUILL OCR Help**
- **Copy Service Summary**
- **Copy Diagnostics Without Secrets**
- **Reset Service Settings**

These buttons should appear near the friendly overview and setup checklist, not hidden only in advanced settings.

### 10.2 Test Connection behavior

When the user presses **Test Connection**:

1. Validate that an API key exists.
2. Make a minimal authenticated request if Datalab exposes a suitable account/status endpoint.
3. If no lightweight endpoint is available, perform a safe SDK initialization and show “API key present; full validation will occur on first conversion.”
4. Never upload a user document for testing unless the user explicitly chooses a sample test file.
5. Announce success or failure to the screen reader and place focus on the result message.

Example success message:

> Datalab service is configured. QUILL can use this service when you choose Import with OCR.

Example failure message:

> Datalab service could not be verified. Check your API key, internet connection, and endpoint URL.

---

## 11. File Import and Conversion UX

### 11.1 Menu entry

Add:

```text
File
  Import with OCR / Convert Document...
```

Optional later shortcut:

```text
Ctrl+Shift+O
```

Only assign the shortcut if it does not conflict with existing QUILL or expected Windows conventions.

### 11.2 Import wizard: simple path

Step 1: Choose file.

Supported types should be read from the selected provider’s capability descriptor.

Step 2: Choose output.

Default choices:

1. **Open as editable Markdown** — recommended.
2. **Open as accessible HTML preview and Markdown source**.
3. **Open plain text only**.
4. **Open OCR Review Mode**.
5. **Advanced: save JSON or chunks for automation.**

Step 3: Consent and cost note.

Required cloud notice:

> This document will be sent to Datalab for processing. Do not continue unless you are allowed to upload this document to that service. Datalab says conversion results are deleted from its servers one hour after processing completes. QUILL will retrieve the result promptly and will not send documents automatically.

Buttons:

- **Convert**
- **Cancel**
- **Service Settings**

### 11.3 Import wizard: advanced options

Advanced options should be collapsible and fully keyboard accessible.

Provider-specific Datalab options:

| Option | QUILL label | Datalab parameter |
|---|---|---|
| Output format | Output format | `output_format` |
| Processing mode | Processing mode | `mode` |
| Page delimiters | Add page delimiters | `paginate` |
| Maximum pages | Maximum pages | `max_pages` |
| Page range | Page range | `page_range` |
| Skip cached results | Force fresh conversion | `skip_cache` |
| Extract images | Extract images | inverse of `disable_image_extraction` |
| Generate image captions | Generate image captions | inverse of `disable_image_captions` |
| Include Markdown in chunks | Include Markdown in chunks/JSON | `include_markdown_in_chunks` |
| Token-efficient Markdown | Optimize Markdown for AI token usage | `token_efficient_markdown` |
| Add block IDs | Add block IDs to HTML | `add_block_ids` |
| Word bounding boxes | Include word boxes and confidence | `word_bboxes` |
| Track changes | Extract tracked changes | `extras=track_changes` |
| Chart understanding | Understand charts and diagrams | `extras=chart_understanding` |
| Extract links | Extract links | `extras=extract_links` |
| Table cell boxes | Include table cell boxes | `extras=table_cell_bboxes` |
| List item boxes | Include list item boxes | `extras=list_item_bboxes` |
| Infographic mode | Infographic understanding | `extras=infographic` |
| New block types | Use expanded block detection | `extras=new_block_types` |
| Region | Processing region | `processing_location` |

Default advanced setting recommendations:

```yaml
output_format: markdown
mode: balanced
paginate: true
disable_image_extraction: false
disable_image_captions: false
token_efficient_markdown: false
add_block_ids: false
word_bboxes: false
extras: ""
```

For “OCR Review Mode,” use:

```yaml
output_format: html,json
mode: accurate
paginate: true
word_bboxes: true
add_block_ids: true
include_markdown_in_chunks: true
extras: "table_cell_bboxes,list_item_bboxes,extract_links,chart_understanding,new_block_types"
```

Because this costs more, QUILL must warn the user before enabling expensive add-ons.

---

## 12. OCR Review Mode

OCR Review Mode is the differentiator. This is where QUILL can be magical.

### 12.1 Purpose

Give the user a guided, accessible way to inspect and correct OCR output without needing to visually compare page images.

### 12.2 Layout

Use a split-pane or dialog with:

1. **Document outline tree**
   - Pages
   - Headings
   - Tables
   - Forms
   - Images and captions
   - Low-confidence text
   - Warnings

2. **Editable converted content**
   - Markdown or structured text in a normal QUILL editing surface.

3. **Context / confidence pane**
   - Read-only multiline edit field.
   - Shows source page number, block type, confidence, bounding box text if available, and nearby context.

4. **Actions pane**
   - Accept block
   - Edit block
   - Mark as needs review
   - Convert table to Markdown
   - Convert table to CSV
   - Re-run selected pages in accurate mode
   - Add correction to OCR dictionary
   - Export review report

### 12.3 Keyboard model

Suggested commands:

| Command | Action |
|---|---|
| F6 | Cycle panes |
| Shift+F6 | Cycle panes backward |
| F2 | Edit selected block |
| Ctrl+Enter | Accept current block |
| Ctrl+Shift+Enter | Accept all blocks on page |
| Alt+R | Re-run selected page or block |
| Alt+T | Open table review |
| Alt+I | Review images and captions |
| Alt+F | Review form fields and checkboxes |
| Alt+L | Jump to next low-confidence item |
| Alt+P | Announce page and block position |
| Escape | Close secondary dialogs or return to previous pane |

### 12.4 Screen reader announcements

Announcements must be helpful and not noisy.

Good examples:

> Page 3, table, 6 rows, 4 columns, confidence medium.

> Low-confidence word: “Arizona.” Current text may be incorrect.

> Image caption generated: “Bar chart showing monthly enrollment.” Review recommended.

Avoid:

- Repeating the full document content on every focus change.
- Announcing raw JSON.
- Emoji or decorative symbols.
- Long automatic speech while the user is arrowing.

### 12.5 Review report

QUILL should optionally generate a Markdown review report:

```markdown
# OCR Review Report

Source file: example.pdf
Provider: Datalab Chandra OCR Service
Mode: accurate
Pages processed: 12
Output: Markdown

## Warnings

- Page 4: 12 low-confidence words.
- Page 6: Complex table detected.
- Page 9: Image caption generated and not manually verified.

## User actions

- Page 4: Corrected 3 words.
- Page 6: Converted table to Markdown.
```

---

## 13. Architecture

### 13.1 Core components

```text
quill/
  ai_hub/
    services_tab.py
    service_registry.py
    credential_store.py
    service_models.py
  services/
    base.py
    document_conversion.py
    datalab_provider.py
    local_tesseract_provider.py        # future
    azure_document_intel_provider.py   # future
    mistral_ocr_provider.py            # future
  document_import/
    import_wizard.py
    conversion_job.py
    conversion_result.py
    ocr_review_mode.py
    markdown_postprocessor.py
    html_to_markdown.py
    table_tools.py
  security/
    privacy_prompts.py
    redaction_helpers.py               # future
  tests/
    fixtures/
      simple_scanned.pdf
      table_complex.pdf
      form_checkbox.pdf
      handwritten_note.png
```

### 13.2 Provider interfaces

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol, Optional, Mapping, Any


class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    CHUNKS = "chunks"
    TEXT = "text"


class ProcessingMode(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"


@dataclass(frozen=True)
class ServiceCapability:
    provider_id: str
    display_name: str
    supports_cloud: bool
    supports_on_prem: bool
    supported_extensions: tuple[str, ...]
    output_formats: tuple[OutputFormat, ...]
    processing_modes: tuple[ProcessingMode, ...]
    max_file_size_mb: Optional[int] = None
    max_pages_per_request: Optional[int] = None
    supports_page_range: bool = False
    supports_confidence: bool = False
    supports_bounding_boxes: bool = False
    supports_tables: bool = False
    supports_image_captions: bool = False


@dataclass
class ConversionOptions:
    output_format: OutputFormat = OutputFormat.MARKDOWN
    mode: ProcessingMode = ProcessingMode.BALANCED
    paginate: bool = True
    page_range: Optional[str] = None
    max_pages: Optional[int] = None
    extract_images: bool = True
    generate_image_captions: bool = True
    include_confidence: bool = False
    include_block_ids: bool = False
    extras: tuple[str, ...] = ()


@dataclass
class ConversionProgress:
    status: str
    percent: Optional[int] = None
    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    message: str = ""


@dataclass
class ConversionResult:
    provider_id: str
    source_path: Path
    output_format: OutputFormat
    markdown: Optional[str] = None
    html: Optional[str] = None
    json_data: Optional[Mapping[str, Any]] = None
    chunks: Optional[Mapping[str, Any]] = None
    images: Optional[Mapping[str, bytes]] = None
    metadata: Optional[Mapping[str, Any]] = None
    warnings: tuple[str, ...] = ()
    parse_quality_score: Optional[float] = None


class DocumentConversionProvider(Protocol):
    def capabilities(self) -> ServiceCapability:
        ...

    def validate_configuration(self) -> tuple[bool, str]:
        ...

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_callback,
        cancel_token,
    ) -> ConversionResult:
        ...
```

### 13.3 Datalab provider behavior

Use the SDK by default when available:

```python
from datalab_sdk import DatalabClient, ConvertOptions as DatalabConvertOptions
```

Fallback to REST if the SDK is not installed or if packaging makes direct REST more reliable.

Datalab options mapping:

```python
DatalabConvertOptions(
    output_format=options.output_format.value,
    mode=options.mode.value,
    paginate=options.paginate,
    max_pages=options.max_pages,
    page_range=options.page_range,
    disable_image_extraction=not options.extract_images,
    disable_image_captions=not options.generate_image_captions,
    word_bboxes=options.include_confidence,
    add_block_ids=options.include_block_ids,
    extras=",".join(options.extras) if options.extras else None,
)
```

### 13.4 Asynchronous job orchestration

QUILL is a wxPython app. Network calls and polling must never block the UI thread.

Use:

- Worker thread or task executor for conversion.
- `wx.CallAfter` for UI updates.
- Cancel token checked between polling attempts.
- Exponential backoff for transient failures.
- Specific handling for HTTP 429 / rate limits.
- Job log that excludes document content and secrets.

Job state model:

```text
queued
validating
uploading
submitted
processing
retrieving
postprocessing
opening
complete
cancelled
failed
```

### 13.5 Temporary files

Use:

```text
%LOCALAPPDATA%\QUILL\Temp\ocr_jobs\<job_id>\
```

Contents:

```text
source_copy.ext
result.md
result.html
result.json
images\
job_metadata.json
```

Default cleanup:

- Delete temporary source copy after successful import unless user enables “keep job files.”
- Keep converted result only in the open document until the user saves.
- Auto-delete failed job temp folders older than 7 days.
- Never store API keys in job metadata.

### 13.6 Credential storage

Do not store API keys in JSON settings.

Preferred options:

1. Python `keyring` package using Windows Credential Manager.
2. Windows DPAPI through `win32crypt` or a small credential helper.
3. Environment variable fallback: `DATALAB_API_KEY`.

Suggested key names:

```text
QUILL/services/datalab/api_key
QUILL/services/datalab/endpoint
```

Config file may store non-secret settings:

```json
{
  "services": {
    "datalab": {
      "enabled": true,
      "endpoint": "https://www.datalab.to",
      "default_mode": "balanced",
      "default_output_format": "markdown",
      "paginate": true,
      "confirm_before_upload": true
    }
  }
}
```

---

## 14. Markdown Post-Processing

Datalab will return Markdown, but QUILL should still apply a careful post-processing pass.

### 14.1 Required post-processing

1. Normalize line endings.
2. Ensure page delimiters are consistent and easy to search.
3. Convert any unsupported or problematic Unicode to accessible text when QUILL’s “screen reader friendly symbols” option is enabled.
4. Ensure tables are navigable.
5. Ensure generated image captions are clearly marked as generated.
6. Preserve links when available.
7. Add source metadata at the top only if the user opts in.

Recommended optional metadata block:

```markdown
<!--
Converted by QUILL
Provider: Datalab Chandra OCR Service
Mode: balanced
Source: filename.pdf
Pages: 12
Review recommended: yes
-->
```

### 14.2 Page delimiters

Use a consistent, screen-reader-friendly delimiter:

```markdown
<!-- Page 1 -->
```

or:

```markdown
[Page 1]
```

Default recommendation: `<!-- Page 1 -->` for Markdown cleanliness, with a QUILL command to jump page-to-page.

### 14.3 Tables

Default table behavior:

- Preserve Markdown tables when simple.
- For complex tables, preserve HTML table if Markdown would destroy structure.
- Offer a **Table Review** action.
- Offer exports:
  - Markdown table
  - HTML table
  - CSV
  - TSV

---

## 15. Privacy, Consent, and Safety Requirements

### 15.1 Required consent prompt

Before every cloud upload, unless a future enterprise admin policy explicitly changes this:

> QUILL will send this document to Datalab for OCR and document conversion. Only continue if you are allowed to upload this file to that service. Consider whether the document contains private, medical, legal, educational, financial, employment, or confidential information.

Buttons:

- **Convert**
- **Cancel**
- **Open service privacy notes**

### 15.2 Sensitive document warning

If filename or user-selected classification suggests sensitive content, add an extra warning. Do not inspect content deeply without consent.

Potential triggers:

- Filename includes: `medical`, `health`, `patient`, `tax`, `ssn`, `social security`, `passport`, `driver`, `w2`, `w-2`, `bank`, `legal`, `contract`, `student`, `iep`, `disability`, `accommodation`.
- User manually selects “Sensitive document.”

### 15.3 Logging rules

Never log:

- API keys.
- Full request payloads.
- File contents.
- OCR output.
- URLs with signed tokens.
- Webhook secrets.
- Full error bodies that may contain document content.

May log:

- Provider id.
- Non-secret endpoint host.
- Job state transitions.
- File extension.
- File size.
- Page count.
- Mode.
- Output format.
- Error category.

### 15.4 Data retention

QUILL must make local retention explicit:

- Open converted result in an unsaved document.
- Ask before saving converted files.
- Provide **Delete OCR temporary files now** command.
- Respect Datalab’s stated one-hour result deletion window by retrieving promptly.

---

## 16. Accessibility Requirements

### 16.1 AI Hub Services tab

- The services list must be keyboard navigable.
- Service status must be available textually:
  - Enabled
  - Not configured
  - Needs API key
  - Connection failed
  - Ready
- Password/API key field must expose an accessible name and help text.
- “Test Connection” results must be placed in a focusable status field and announced.

### 16.2 Import wizard

- All steps must have clear headings.
- Focus must move to the first actionable control on each step.
- Progress updates must be concise.
- Cancel must remain reachable by keyboard while processing.
- Errors must focus a readable details field.

### 16.3 OCR Review Mode

- Use normal edit controls for readable text whenever possible.
- Avoid custom-drawn controls unless accessible objects are implemented.
- Tables must have row/column navigation support.
- Low-confidence items must be discoverable by keyboard.
- All generated captions must be identified as generated.

### 16.4 Screen reader testing matrix

Minimum manual test matrix:

| Screen reader | Browser/UI surface | Required |
|---|---|---|
| NVDA current stable | QUILL wxPython UI | Yes |
| JAWS current stable | QUILL wxPython UI | Yes |
| Narrator Windows 11 | QUILL wxPython UI | Yes |
| VoiceOver macOS | Future if cross-platform | Later |

---

## 17. Error Handling

### 17.1 Common errors

| Error | User-facing message |
|---|---|
| No API key | “Datalab is not configured. Add an API key in AI Hub, Services.” |
| Invalid API key | “Datalab rejected the API key. Check or replace the key.” |
| Offline | “QUILL cannot reach the service. Check your internet connection.” |
| Unsupported file | “This service does not support that file type.” |
| File too large | “This file is larger than the service limit. Try a smaller file or process a page range.” |
| Too many pages | “This document has more pages than the service allows in one request. Use a page range.” |
| 429/rate limit | “The service is busy or your account is rate-limited. QUILL will wait and retry.” |
| Payment/credits issue | “The service reported a billing or credit issue. Check your Datalab account.” |
| Cancelled | “Conversion cancelled. No result was imported.” |
| Bad result | “The service returned an incomplete result. Try accurate mode or a smaller page range.” |

### 17.2 Error details

Each error dialog should include:

- Friendly summary.
- Technical details button.
- Copy details button.
- Open service settings button where relevant.
- Retry button where relevant.

---

## 18. Cost and Usage UX

### 18.1 Principles

- QUILL should not pretend to know exact billing unless the provider returns it.
- QUILL should explain that OCR service pricing is provider-controlled and may change.
- QUILL should link to the provider’s pricing page.
- QUILL should warn before using expensive modes or add-ons.

### 18.2 Estimated usage prompt

Before conversion:

```text
Estimated pages: 42
Provider: Datalab Chandra OCR Service
Mode: Balanced
Output: Markdown
Cost: See Datalab pricing. Your account may include free credits or usage allowance.
```

If Datalab returns `cost_breakdown`, show it after conversion in the job summary.

### 18.3 Usage history

Optional v1.1 feature:

```text
AI Hub → Services → Usage
  Datalab
    Documents processed this month: 8
    Pages submitted: 316
    Last conversion: 2026-06-29
```

No content should be stored in usage history.

---

## 19. Feature Flags

Add feature flags:

```json
{
  "features": {
    "ai_hub_services_tab": true,
    "datalab_document_conversion": true,
    "ocr_review_mode": false,
    "service_usage_history": false,
    "local_tesseract_fallback": false
  }
}
```

---

## 20. Implementation Plan

### Phase 0: Spike and verification

Deliverables:

1. Verify Datalab SDK packaging in QUILL’s Python environment.
2. Build a throwaway script that converts:
   - simple scanned PDF
   - complex table PDF
   - image with text
   - checkbox form
   - DOCX
3. Compare Markdown, HTML, and JSON outputs.
4. Confirm how to retrieve images.
5. Confirm whether `output_format="markdown,html"` is supported in current SDK/API or whether QUILL must run separate conversions.
6. Confirm billing/cost response fields.
7. Confirm error response shapes.
8. Confirm on-prem endpoint compatibility assumptions.
9. Document sample results in `docs/research/datalab_chandra_spike.md`.

Exit criteria:

- One successful conversion via SDK.
- One successful conversion via REST fallback.
- One handled failure for invalid API key.
- One handled 429/rate-limit simulation or mock.

### Phase 1: Services tab foundation

Deliverables:

1. `ServiceRegistry`
2. `CredentialStore`
3. `ServiceDescriptor`
4. `AIHubServicesPanel`
5. Datalab service settings UI
6. Test connection action
7. Settings persistence
8. Unit tests for settings without leaking secrets

Exit criteria:

- User can enable Datalab, enter API key, save settings, close and reopen AI Hub, and test configuration.
- API key is not present in config files or logs.

### Phase 2: Datalab provider adapter

Deliverables:

1. `DatalabDocumentConversionProvider`
2. SDK implementation
3. REST fallback
4. Progress callback support
5. Cancel support
6. Retry/backoff support
7. Result normalization to `ConversionResult`
8. Unit tests with mocked API responses
9. Integration test guarded by `DATALAB_API_KEY`

Exit criteria:

- Provider converts a PDF to Markdown.
- Provider returns warnings and metadata.
- Provider handles cancellation and common errors.

### Phase 3: Import wizard

Deliverables:

1. `ImportWithOcrDialog`
2. Simple mode
3. Advanced mode
4. Consent prompt
5. Progress dialog
6. Save/open result in QUILL
7. Page delimiter support
8. Recent import settings

Exit criteria:

- User can choose a file and open converted Markdown in QUILL.
- UI remains responsive.
- Screen reader announces status.
- Cancel works.

### Phase 4: OCR Review Mode v1

Deliverables:

1. OCR review document outline
2. Low-confidence navigation when confidence data exists
3. Table review entry points
4. Image caption review
5. Review report generation
6. Re-run selected page range in accurate mode

Exit criteria:

- User can review warnings and accept/edit blocks by keyboard.
- User can generate a review report.
- JAWS/NVDA/Narrator testing passes basic flows.

### Phase 5: Provider expansion

Add provider adapters based on demand:

1. Mistral OCR
2. Azure Document Intelligence
3. Local Tesseract
4. Google Document AI
5. AWS Textract
6. Datalab on-prem profile templates

Exit criteria:

- Services tab supports multiple providers without UI redesign.
- Import wizard can select provider based on capability.

---

## 21. Test Plan

### 21.1 Unit tests

- Service registry loads descriptors.
- Credentials are saved and retrieved through mock secure store.
- Datalab options map correctly.
- Unsupported file types are rejected.
- Page range validation.
- Error mapping.
- Markdown post-processing.
- Sensitive filename warning triggers.

### 21.2 Integration tests

Use opt-in environment variable:

```bash
set QUILL_RUN_DATALAB_TESTS=1
set DATALAB_API_KEY=...
```

Tests:

- Convert sample PDF to Markdown.
- Convert sample image to Markdown.
- Convert sample table PDF to HTML/JSON.
- Invalid API key returns friendly error.
- Cancel during polling.

### 21.3 Accessibility tests

Manual scripts:

1. Configure Datalab with NVDA.
2. Configure Datalab with JAWS.
3. Import scanned PDF with keyboard only.
4. Read progress messages.
5. Review generated Markdown.
6. Use OCR Review Mode.
7. Correct low-confidence text.
8. Export review report.

### 21.4 Privacy tests

- Confirm no API key in config.
- Confirm no API key in logs.
- Confirm source file content is not logged.
- Confirm temporary files are cleaned up.
- Confirm cloud consent prompt appears every time in v1.

---

## 22. Acceptance Criteria

### 22.1 MVP acceptance criteria

1. AI Hub contains a Services tab.
3. Datalab Chandra OCR Service can be enabled and configured.
4. API key is stored securely.
5. User can import a supported file via File → Import with OCR / Convert Document.
6. User can also discover the feature from Tools → OCR and Document Conversion.
7. QUILL explicitly asks for consent before cloud upload.
8. Conversion runs without freezing the UI.
9. Progress is accessible.
10. Result opens as an editable Markdown document.
11. Tables, headings, lists, forms, image captions, and page delimiters are preserved when returned by the provider.
12. Errors are understandable and actionable.
13. Basic NVDA, JAWS, and Narrator tests pass.
14. No document content or secrets are written to logs.

### 22.2 “Magical” acceptance criteria

1. A blind user can convert a scanned PDF without needing sighted help.
2. The default output is immediately readable and editable.
3. QUILL guides the user to complex tables, forms, images, and uncertain OCR areas.
4. The user can re-run hard pages in accurate mode.
5. The user can export a clean Markdown document and an OCR review report.
6. The same Services architecture can support a second OCR provider without rewriting the import UI.

---

## 23. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Vendor pricing changes | Do not hard-code prices; link to provider pricing; show provider-returned cost if available. |
| Cloud privacy concern | Explicit consent; BYOK; on-prem endpoint support; local fallback later. |
| Long-running jobs | Async worker; progress dialog; cancellation; retry/backoff. |
| Bad OCR output | OCR Review Mode; re-run page range; allow accurate mode; preserve original source reference. |
| Complex table loss | Preserve HTML/JSON when Markdown cannot represent table accurately; add Table Review. |
| API instability | SDK plus REST fallback; provider abstraction; robust error handling. |
| Accessibility regressions | Manual SR test scripts; avoid custom controls; use standard wx controls. |
| Large documents hit limits | Page range segmentation; warn at file selection; future batch splitting. |
| Secret leakage | Secure credential store; log redaction; automated tests. |

---

## 24. Open Questions

1. Should QUILL name the service **Datalab Chandra OCR Service** or **Datalab Document Conversion** in the UI? Recommendation: user-facing name should be “Datalab Chandra OCR Service,” with technical description mentioning Datalab Convert API.
2. Should OCR Review Mode be part of MVP or behind a beta flag? Recommendation: ship initial review warnings in MVP; full Review Mode behind a beta flag.
3. Should QUILL support multiple output formats in one request if Datalab allows comma-separated formats in the current API? Verify in Phase 0.
4. Should a QUILL-hosted relay service ever exist for users who cannot manage API keys? Recommendation: not for MVP; revisit with strong privacy, funding, and abuse controls.
5. Should institutions be able to preconfigure service settings through an admin config file? Recommendation: yes in v1.1.
6. Should QUILL support redaction before upload? Recommendation: future feature; very difficult to make reliable for scanned documents without already doing OCR.

---

## 25. Recommended Implementation Prompt for Coding Agent

Use this prompt with Claude Code, Codex, or another coding agent:

```text
You are implementing QUILL's AI Hub Services tab and the first document-conversion provider: Datalab Chandra OCR Service.

Read the PRD in docs/prd/ai-hub-services-datalab-chandra-ocr.md. Implement this in phases and keep a running implementation log.

Core requirements:
1. Ship OCR as a supported QUILL tool with stable File and Tools menu access, Help documentation, and release-note coverage.
2. Add an accessible AI Hub → Services tab that is rich, friendly, customer-facing, and includes provider descriptions, benefits, supported file types, privacy notes, pricing/account notes, setup steps, diagnostics, and external website/documentation/pricing/security buttons.
2. Add a provider registry and provider interface for document conversion services.
3. Add secure credential storage for service API keys; never store secrets in JSON config or logs.
4. Implement Datalab Chandra OCR Service using datalab-python-sdk where possible and a REST fallback where needed.
5. Add File → Import with OCR / Convert Document.
6. Add a simple import flow with safe defaults: Balanced mode, Markdown output, page delimiters on, image extraction/captioning on.
7. Add advanced options mapped to Datalab Convert API parameters.
8. Show a required cloud upload consent prompt before every upload.
9. Run conversion asynchronously so the wxPython UI never freezes.
10. Open the converted result as a new editable Markdown document.
11. Add robust error handling for missing key, invalid key, offline, unsupported file, file too large, too many pages, rate limits, billing/credits, cancellation, and incomplete result.
12. Add tests and mocks. Integration tests must be opt-in and require DATALAB_API_KEY.

Accessibility requirements:
- Keyboard-only support for every control.
- Standard wx controls wherever possible.
- Meaningful accessible names, descriptions, and status messages.
- Progress updates must be announced politely and must not spam screen readers.
- No emoji or decorative Unicode in status messages.

Security requirements:
- Do not log API keys, document content, OCR output, signed URLs, or full sensitive payloads.
- Store only non-secret service settings in config.
- Temporary files must be cleaned up.
- Consent is mandatory for v1.

Start with the foundation and do not overbuild provider-specific UI into the core architecture. The goal is Datalab first, but Azure, Mistral, AWS, Google, and local providers should be possible later through adapters.
```

---

## 26. Suggested File/Issue Breakdown

### Epic: AI Hub Services Foundation

- Issue: Add ServiceDescriptor and ServiceRegistry.
- Issue: Add secure CredentialStore.
- Issue: Add AI Hub Services tab.
- Issue: Add service settings persistence.
- Issue: Add service diagnostics panel.

### Epic: Datalab Chandra OCR Service

- Issue: Add Datalab provider adapter.
- Issue: Add SDK implementation.
- Issue: Add REST fallback.
- Issue: Add option mapping.
- Issue: Add mock response tests.
- Issue: Add integration test harness.

### Epic: Import with OCR

- Issue: Add File → Import with OCR / Convert Document.
- Issue: Add import wizard simple mode.
- Issue: Add advanced options.
- Issue: Add consent prompt.
- Issue: Add progress and cancellation.
- Issue: Open result in new Markdown document.

### Epic: Accessible OCR Review

- Issue: Add conversion warnings panel.
- Issue: Add low-confidence navigation.
- Issue: Add table review mode.
- Issue: Add image caption review.
- Issue: Add OCR review report export.

### Epic: Documentation

- Issue: Add user help page.
- Issue: Add privacy help page.
- Issue: Add admin/on-prem configuration page.
- Issue: Add troubleshooting page.
- Issue: Add developer provider-adapter guide.

---

## 27. User Documentation Draft

### Import with OCR / Convert Document

Use this feature when a PDF, image, or other document is hard to read, has no text, or has tables and layout that do not work well with your screen reader.

1. Open the **File** menu.
2. Choose **Import with OCR / Convert Document**.
3. Pick your file.
4. Choose how QUILL should open the result. **Editable Markdown** is recommended.
5. Review the cloud upload notice.
6. Choose **Convert**.

QUILL will send the document to the selected service, retrieve the converted result, and open it as a new document. Review the result before relying on it, especially for legal, medical, financial, educational, or other sensitive documents.

### Choosing a mode

- **Fast**: Best for simple, clean documents.
- **Balanced**: Recommended for most documents.
- **Accurate**: Best for scanned pages, complex tables, dense layouts, forms, and handwriting. It may take longer and may cost more.

### Privacy note

QUILL will not send a document to a cloud service unless you choose to continue after the upload notice. Do not upload documents unless you are allowed to send them to the selected service.

---

## 28. Final Recommendation

Implement this as a **supported OCR tool powered by a Services-first architecture**, not as a hidden connector or one-off experimental command.

The first release should make QUILL’s supported OCR tool feel simple and safe, with Datalab Chandra OCR Service as the first backend:

- Configure once in **AI Hub → Services**.
- Import from **File → Import with OCR / Convert Document**.
- Default to **Balanced + Markdown + page delimiters**.
- Require explicit upload consent.
- Open the result directly in QUILL.
- Build the provider interface so alternatives can be added cleanly.

This will give QUILL a powerful, practical path for turning inaccessible documents into editable, navigable, screen-reader-friendly content while preserving user choice, privacy, and future flexibility.

---

## Appendix Z. AI menu discoverability + the extensible AI Hub Services framework

*(Added during planning integration — ties this PRD to the AI menu, the verified
on-demand acquisition path, and the broader "services" direction.)*

### Z.1 Tight AI Hub **and** AI menu integration

The configuration home is **AI Hub → Services** (per §9). For discoverability, the
top-level **AI menu** also surfaces the supported OCR tool directly, so users who
live in the menus never have to know where the Services tab is:

- **AI → Import with OCR / Convert Document…** — the primary action (mirrors
  **File → Import with OCR**; same handler).
- **AI → Services…** — opens the AI Hub on the Services tab.

Both honor QUILL's invariants: the dialog contract (`_show_modal_dialog`),
cancelable spoken progress (`AIProgressDialog`), Safe Mode gating, and the
network-egress audit (GATE-9) for every provider call. Upload is consent-gated
(a document leaves the machine only on an explicit action).

### Z.2 The AI Hub Services framework is the extensible home for *all* document-intelligence services

This PRD's "Services tab + provider interface" is deliberately a **framework**, not
an OCR-only feature. Every future document-intelligence service plugs into the same
tab, the same provider interface (§13.2), the same credential storage, the same
consent/audit/Safe-Mode rules, and the same accessible card UX. Planned tenants:

- **OCR / document conversion:** Datalab Chandra (v1), then Mistral OCR, Azure
  Document Intelligence, AWS Textract, Google Document AI, and local engines.
- **Scribe for Documents (Pneuma Solutions):** the partner document-conversion
  service specced in [`scribe.md`](scribe.md) is a natural **Services-tab tenant** —
  same "configure once, convert, open result in QUILL" shape, just with an OAuth
  connection instead of an API key. Its OAuth flow reuses QUILL's existing
  authorization-code pattern (see `scribe.md` §2.1).
- A single **service descriptor** (id, friendly name, category, capabilities,
  config schema, optional credential, optional **on-demand component**, menu
  placement) lets a new service appear in the Services tab + AI menu with no
  bespoke UI.

### Z.3 Local engines reuse the verified on-demand acquisition path

For **local** OCR engines (Tesseract / Marker / local Chandra), QUILL must not bloat
the installer. They are fetched on demand through the same **pinned, SHA-256-verified
release-asset** mechanism shipped for the speech engine and Kokoro
(`quill/core/release_assets.py`; AI-Optimization PRD §10.2.4): a service that needs a
local binary/model declares it as a release asset, and QUILL downloads + verifies +
unpacks it with cancelable, accessible progress, blocked in Safe Mode — and offers a
**re-download/replace** when one is already present, with **newer-version awareness**
on the roadmap (a `version` field already exists on the asset model).

### Z.4 Net

OCR ships first and real (Datalab Chandra), but it lands inside a **services
framework** that the AI menu and AI Hub present uniformly, that local engines and
partner services (Scribe) join without new plumbing, and that inherits QUILL's
privacy, consent, accessibility, and verified-acquisition guarantees. That is the
magical, future-proof shape: one accessible home for document intelligence, many
services over time.
