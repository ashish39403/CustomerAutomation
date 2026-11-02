---
title: Knowledge Base Manifest
document_type: manifest
approved_category: governance
version: 1
status: active
last_updated: 2026-11-02
---

# Knowledge Base Manifest

This manifest lists every file in the Harbor & Pine internal knowledge base. It describes each file's purpose, approved category, and suggested metadata for chunking, embedding, Qdrant indexing, RAG retrieval, AI classification, and grounded reply drafting.

Company: Harbor & Pine (fictional home and outdoor seller on Amazon)
All Harbor & Pine orders are sold through Amazon. Harbor & Pine does not operate a direct storefront.

## Suggested Metadata Schema

Each knowledge document should be indexed with the following metadata fields:

| Field | Description | Example |
|---|---|---|
| document_type | Type of document | product_guide, troubleshooting_guide, assembly_guide, parts_and_damage_guide, policy_guide, faq, manifest |
| approved_category | Topical category | paddle_boards, shelving, amazon_orders, returns, escalation, general, governance |
| version | Document version | 1 |
| active | Whether the document is active | true |
| source | Source file name | paddle-board-sizing-guide.md |

## File Inventory

| # | File | Purpose | Approved Category | Document Type |
|---|---|---|---|---|
| 1 | paddle-board-sizing-guide.md | Rider-weight size guidance for 10'6", 11', and 12'6" paddle boards | paddle_boards | product_guide |
| 2 | paddle-board-setup-care-and-troubleshooting.md | Inflation/setup steps, PSI guidance, leak troubleshooting, cleaning, storage, warranty-style limitations | paddle_boards | troubleshooting_guide |
| 3 | paddle-board-missing-parts-and-damage.md | Missing pump/fin/repair-kit handling and damage-photo requirements | paddle_boards | parts_and_damage_guide |
| 4 | shelving-product-guide.md | Shelving variant and finish reference table | shelving | product_guide |
| 5 | shelving-assembly-and-troubleshooting.md | Assembly guidance, panel-number identification, basic troubleshooting | shelving | assembly_guide |
| 6 | shelving-missing-parts-damage-and-wrong-finish.md | Cracked panel, missing hardware, and wrong finish workflows; safety guidance | shelving | parts_and_damage_guide |
| 7 | amazon-order-shipping-and-delivery.md | Order lookup, delivery tracking boundaries, Amazon vs. Harbor & Pine responsibilities | amazon_orders | policy_guide |
| 8 | returns-refunds-and-replacements.md | Return/refund/replacement boundaries, evidence required, $150 threshold | returns | policy_guide |
| 9 | customer-support-escalation-policy.md | Mandatory human escalation triggers; automation vs. human communication | escalation | policy_guide |
| 10 | faq.md | 20 example customer questions and expected source files | general | faq |
| 11 | KNOWLEDGE_MANIFEST.md | File inventory, purpose, category, and suggested metadata | governance | manifest |

## Consistent Policies Across All Documents

- Orders are sold through Amazon; Harbor & Pine does not operate a direct storefront.
- No real customer details, real order numbers, or real product SKUs are used.
- Every document is Version 1, Status: active, Last updated: 2026-11-02.
- Harbor & Pine never promises automatic refunds, replacements, discounts, or Amazon actions.
- Automation may communicate product information, instructions, required evidence, and boundaries. A human support agent is required for all mandatory escalation triggers.

## Mandatory Human Escalation Triggers

- Refund or replacement request above $150
- Chargeback, payment dispute, or Amazon A-to-z Guarantee claim
- Legal threat, safety incident, injury, or serious complaint
- Suspected fraud or repeated abuse
- Personal-data request
- Any policy exception
- Paddle board safety concern beyond ordinary setup or troubleshooting
- Repeated defect after one completed troubleshooting attempt
- Shelving structural failure or risk of injury

## 20 Example Customer Questions and Expected Source File(s)

| # | Customer Question | Expected Source File(s) |
|---|---|---|
| 1 | What size paddle board should I get based on my weight? | paddle-board-sizing-guide.md |
| 2 | How do I inflate my paddle board and what PSI should I use? | paddle-board-setup-care-and-troubleshooting.md |
| 3 | My paddle board is losing air. How do I find the leak? | paddle-board-setup-care-and-troubleshooting.md |
| 4 | My paddle board pump is missing. What do I do? | paddle-board-missing-parts-and-damage.md |
| 5 | My paddle board arrived with a tear. What photos do I need to send? | paddle-board-missing-parts-and-damage.md |
| 6 | How do I clean and store my paddle board? | paddle-board-setup-care-and-troubleshooting.md |
| 7 | What shelving variants and finishes does Harbor & Pine offer? | shelving-product-guide.md |
| 8 | How do I identify the panel numbers on my shelving unit? | shelving-assembly-and-troubleshooting.md |
| 9 | My shelving panel is cracked. What is the workflow? | shelving-missing-parts-damage-and-wrong-finish.md |
| 10 | I am missing screws for my shelving unit. What do I do? | shelving-missing-parts-damage-and-wrong-finish.md |
| 11 | I received the wrong finish on my shelving unit. What do I do? | shelving-missing-parts-damage-and-wrong-finish.md |
| 12 | Can I use my shelving unit if a panel is cracked? | shelving-missing-parts-damage-and-wrong-finish.md, shelving-assembly-and-troubleshooting.md |
| 13 | How do I look up my Amazon order? | amazon-order-shipping-and-delivery.md |
| 14 | Who handles shipping and delivery, Amazon or Harbor & Pine? | amazon-order-shipping-and-delivery.md |
| 15 | My package shows delivered but I never received it. What do I do? | amazon-order-shipping-and-delivery.md |
| 16 | How do I request a refund or replacement? | returns-refunds-and-replacements.md |
| 17 | Will I automatically get a refund if my product is damaged? | returns-refunds-and-replacements.md, customer-support-escalation-policy.md |
| 18 | When does a request need to go to a human agent? | customer-support-escalation-policy.md |
| 19 | My request is over $150. Can automation approve a replacement? | customer-support-escalation-policy.md, returns-refunds-and-replacements.md |
| 20 | Does Harbor & Pine have its own website or storefront? | amazon-order-shipping-and-delivery.md, all product guides |

## Indexing Notes

- Chunk each file by section heading so RAG retrieval returns targeted passages.
- Preserve the frontmatter metadata on every chunk derived from a document.
- Use the `document_type` and `approved_category` fields for classification and filtering.
- Use `active: true` to surface only current documents; `version` to track future updates.
