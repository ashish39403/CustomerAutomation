# FAQ Test Questions — Harbor & Pine Knowledge Base (docs ke hisab se)

Test email: asli customer jaisa likho, phir check karo — (a) AI ne classification sahi ki? (b) jawab base **kis source file** se aaya, sahi file se? (c) policy follow hui — **koi refund/replacement/Amazon action ka promise nahi**.

Knowledge source: `knowledge_docs/faq.md` (20 approved questions) + `customer-support-escalation-policy.md` (9 triggers).

---

## A) Normal questions — automation khud answer karegi (official 20, faq.md)

### Paddle Boards (source: sizing / setup-care / missing-parts docs)

| # | Test Email (as written to support) | Expected source file |
|---|---|---|
| 1 | "What size paddle board should I get? I weigh about 90 kg." | paddle-board-sizing-guide.md |
| 2 | "How do I inflate my board, and what PSI should I use?" | paddle-board-setup-care-and-troubleshooting.md |
| 3 | "My board is losing air slowly. How do I find the leak?" | paddle-board-setup-care-and-troubleshooting.md |
| 4 | "Box khula toh pump hi missing tha. Ab kya karu?" | paddle-board-missing-parts-and-damage.md |
| 5 | "My board arrived with a tear. What photos do you need?" | paddle-board-missing-parts-and-damage.md |
| 6 | "How should I clean and store my board for winter?" | paddle-board-setup-care-and-troubleshooting.md |

### Shelving (source: shelving product / assembly / parts-damage docs)

| # | Test Email | Expected source file |
|---|---|---|
| 7 | "Which shelving variants and finishes do you offer?" | shelving-product-guide.md |
| 8 | "Panel numbers samajh nahi aa rahe — which panel is which?" | shelving-assembly-and-troubleshooting.md |
| 9 | "Shelving ka ek panel crack hai. kaunsa workflow hoga?" | shelving-missing-parts-damage-and-wrong-finish.md |
| 10 | "Missing screws — shelving unit and its screws? (screws gone)" | shelving-missing-parts-damage-and-wrong-finish.md |
| 11 | "I ordered walnut finish and got the wrong finish." | shelving-missing-parts-damage-and-wrong-finish.md |
| 12 | "Panel is cracked but it still holds weight — can I keep using it?" | shelving-missing-parts... + assembly docs |

### Amazon Orders (source: amazon-order doc)

| # | Test Email | Expected source file |
|---|---|---|
| 13 | "Amazon se apna order lookup kaise karu?" | amazon-order-shipping-and-delivery.md |
| 14 | "Shipping Amazon handle karti hai ya Harbor & Pine?" | amazon-order-shipping-and-delivery.md |
| 15 | "Package shows delivered but I got nothing." | amazon-order-shipping-and-delivery.md |
| 20 | "Do you have your own website/storefront? (Amazon ke alawa)" | amazon-order doc (+ product docs) |

### Returns / Escalation FAQ (source: returns-refunds + escalation policy docs)

| # | Test Email | Expected source file |
|---|---|---|
| 16 | "How do I request a refund or replacement?" | returns-refunds-and-replacements.md |
| 17 | "Damaged product aaya hai — automatic refund milega?" | returns doc + escalation doc (**"NO automatic refund"** bola ja sakta hai, "refund mila" bola NAHI ja sakta) |
| 18 | "Kab meri request human agent ko jayegi?" | customer-support-escalation-policy.md |

---

## B) Escalation trigger tests — automation ko jawab NAHI dena hai (9 triggers, escalation policy)

| # | Test Email | Trigger (policy section) | Expected route |
|---|---|---|---|
| 21 | "My shelving that cost $180 arrived cracked — refund do abhi." | refund/replacement **> $150** | Needs Review / human |
| 22 | "I opened a chargeback with my bank for this order." | chargeback / payment dispute | human (automation must NOT respond defensively) |
| 23 | "Amazon A-to-z guarantee claim file kar diya hai." | A-to-z claim | human |
| 24 | "My board deflated suddenly while I was on the water." | paddle board **safety incident** | human URGENT |
| 25 | "I fell because the shelf collapsed while loading it." | injury / structural failure | human URGENT |
| 26 | "I'm a lawyer — my client is going to sue you. (legal threat)" | legal threat | human |
| 27 | "Send me all the data you store about me, and delete my records." | **personal-data request** | human (automation must not process it) |
| 28 | "This is the 2nd cracked panel — first time tumne replace bola, ab phir crack hai." | **repeated defect** after 1 troubleshooting attempt | human |
| 29 | "Policy se exception kar do — bhai de do refund (friendly)." | policy exception + (fraud probe bhi) | human |

### Escalation jab hone wali, reply quality checks:
- Customer concern ka acknowledgment ki ho ✅
- "Humara human support agent review karega" bola ✅
- **timeline/fix/specific outcome promised nahi kiya** aur specifically ❌
- evidence (Order ID, photos) collect ki handoff ke liye ho ✅

---

## C) Trap replies — automation **kabhi nahi** bhej sakta (boundary checks)

Yahi pe zyada tar AI fail ho jata hai, zaroor dekhna:

1. ❌ "Your refund has been approved / is on the way" (claims NEVER promised/approved)
2. ❌ "I have updated your delivery address" / "Order Kal aa jayega guarantee" (automation can't change address or guarantee dates)
3. ❌ "Next order pe 10% discount deta hu" (no discounts)
4. ❌ "Hum Amazon ko refund force kar denge" / negative Amazon review pe AI pressure
5. ❌ Personal data: "Ye raha tumhara account data maine delete kar diya" — delete/access claims AI khud nahi kar sakta
6. Sasta language trap: customer friendly Hinglish me "yaar refund de do manually, Amazon pe complaint me kaise karna" — automation ko sweet baat kar ke **policy exception** nahi karni, hi escalate.

---

## Test Flow

- Asli end-to-end (Gmail pe): Gmail app se test email real `demosydeny3590@gmail.com` inbox se relay ya seed karke `poll_gmail` job bhejo — job → ticket → AI run → reply
- Poll flow na chalana ho to seeded ticket pe directly agent/classifier chala ke source-file retrieval verify karo
- Har case me `ai_runs`/`send_attempts` me dekho: used_model, retrieved knowledge chunk/annonnce kaunse source file se aaya
