# Chapter 18: Taking payments with your forms

A form can take money: a registration fee, a membership renewal, an order
for T-shirts, a donation where the giver picks the amount. You write the
payment into the form in QUILL, publish it to your WordPress site, and the
QUILL Accessible Forms plugin (QAF) on the site takes the payment through
Stripe, PayPal, or both.

QUILL never touches the money and never sees a card number or a secret key.
Its job is to describe what the form charges, to check that the site is ready
before it publishes, and to show you afterwards who paid. Everything that
moves money happens on the site, between the person paying and Stripe or
PayPal.

This chapter goes through the whole process in order: what you need, test
mode, adding the payment field, choosing providers, publishing, what the
person paying hears, receipts, refunds, reporting, going live, and what to do
when something goes wrong.

## What you need before you start

- **A form.** Any form you have written in QUILL, saved as a `.qaf` file.
  Chapter 17 and the
  [WordPress and Forms manual](../wordpress-and-forms/wordpress-forms-guide.html)
  cover writing one.
- **Form Payments turned on.** It is an advanced feature, off in the Essential
  profile. If **Tools > Forms** has no **Form Payments Setup...**, turn on Form
  Payments in **Profiles and Features...**. It needs Forms and WordPress on as
  well.
- **A WordPress site connected to QUILL,** with the QAF plugin installed. The
  plugin has to be a version that supports payments: one that answers QUILL's
  payment check, which the plugin calls payment contract version 1. You find
  out with Verify Payment Setup, below; an older plugin says so plainly.
- **A Stripe account, a PayPal business account, or both.** Each has a test
  side (Stripe's test mode, PayPal's sandbox) that you use first.
- **The site's payment keys set up in WordPress.** Whoever runs the site
  enters them under **QAF Forms > Payments** in wp-admin, presses Check
  Connection and Create Webhook for each provider, and leaves the site in test
  mode. The plugin's own guide, *Taking payments: a guide for site owners*,
  walks through it. QUILL never asks for these keys and has nowhere to put
  them.

If you run the site yourself, do the WordPress part first. It takes about ten
minutes per provider.

## Test mode, twice

There are two test mode switches, and they have to agree.

- **The site's mode,** set in wp-admin under QAF Forms > Payments. A new site
  starts in test mode.
- **The form's mode,** the **Test mode** check box in Form Payments Setup. A
  new payment form starts with it checked.

In test mode no real money moves. Stripe takes only its test card numbers and
PayPal only its sandbox accounts. Keep both switches on test until you have
tried every path, including a declined card and a refund.

If the two disagree, nothing is charged by mistake: QUILL will not publish a
test form to a live site or a live form to a test site, and the site itself
refuses to take payment for a form in the other mode.

## Adding a payment field

Open the form and choose **Tools > Forms > Insert Payment Field...**. A form
has one payment field at most; if it already has one, QUILL says so and you
edit that field's source instead.

The dialog has four boxes:

- **Label:** what the person paying hears for the field, such as
  "Registration fee" or "Your gift".
- **Amount:** where the amount comes from, in one of three ways described
  below.
- **Donation minimum** and **Donation maximum:** only for a donation. Leave
  them empty for other amounts.

Press **Insert**. The field goes at the end of the last page, and the form
gets payment settings with Stripe in test mode, in US dollars, if it had none.
You can change those next, in Form Payments Setup. The whole change is one
step, so Undo takes it back. Cancel changes nothing.

### A fixed amount

Type the amount as a plain number in the main unit of the currency: `25` for
25 dollars, `19.99` for 19 dollars 99. No currency sign, no thousands
separator.

On the page, the field says "Amount due: 25.00 USD." There is nothing for the
person paying to type.

### A donation, with a smallest and largest gift

Type `donation` in Amount. If you want limits, put them in Donation minimum
and Donation maximum, again as plain numbers: `5` and `500`. Leave either one
empty for no limit on that side.

On the page, the field becomes a box labelled with your label and the
currency ("Your gift, in USD"), and the limits are read with it: "Give from
5.00 USD to 500.00 USD." The site checks the amount again when the form is
sent, so a gift below the minimum is refused with "The smallest gift this
form takes is 5.00 USD."

Inserting a donation also sets the form's payment mode to Donation.

### An amount from a total field

For an order form, the amount is usually the order total. Type `#` and the
total field's id, such as `#order_total`. To save you remembering ids, the
Amount box's help lists every field in the form that can be used: totals,
prices, calculations, number fields and currency fields, as "#order_total
(Order total)". Press F1 on the Amount box to hear the list.

Whatever the page shows while someone fills in the form, the site works the
total out again from the form itself when the form is sent: the product they
chose and its price, how many (from a quantity field linked to the product),
any coupon code, and the total field's own shipping and tax settings; or the
total's calculation, if it has one. A price or total typed into the page by
someone trying their luck is ignored. If the amount names a number or
currency field, the person paying types the amount there themselves, and the
site reads it exactly, like a donation.

Here is a small order form, as it looks in the document:

```
product #shirt "T-shirt"
  + "s" | "Small" @price 15
  + "l" | "Large" @price 17.5

quantity #how_many "How many?"
  @min 1
  @max 10
  @linked_product "shirt"

total #order_total "Order total"

payment #pay "Payment"
  @amount "#order_total"
```

### Amounts the site will refuse

QUILL checks these before it publishes, and Check This Form lists them too:

- An amount of zero or less, or one that is not a number, `donation` or `#`
  followed by an id.
- `#` naming a field that is not there, or one that is not an amount field
  (a text box, say).
- More decimal places than the currency has: `10.005` dollars, or `2000.5`
  yen. The site refuses these rather than round someone's price, so QUILL
  says "This currency takes at most 2 decimal places."
- A donation minimum larger than the maximum, or limits on an amount that is
  not a donation.

## Choosing providers and the other settings

Choose **Tools > Forms > Form Payments Setup...**. These settings belong to
this form; another form can use different ones.

- **Providers:** Stripe; Stripe, then PayPal; PayPal; or PayPal, then Stripe.
  With two, the person paying chooses, and the first is chosen for them to
  start with.
- **Currency:** three letters, such as `usd`, `eur`, `gbp` or `cad`. The
  site must take that currency through every provider you chose. PayPal takes
  fewer currencies than Stripe; Indian rupees, for example, work through
  Stripe only.
- **Mode:** Payment, for a fixed or calculated amount, or Donation.
- **Capture:** Automatic takes the money when the person pays. Manual only
  authorizes it, so you can check the order first and take the money later in
  the Stripe or PayPal dashboard.
- **Test mode:** checked while you test. Unchecking it and pressing Save in
  Form asks "Save live payment mode in this form?", and you have to say Use
  Live Mode.
- **Statement descriptor:** optional. The text on the payer's card statement,
  5 to 22 plain letters, digits and spaces, with at least one letter, such as
  `BITS CONFERENCE`. Leave it empty to use the account's own.

Press **Save in Form**. Like everything else in a form, this changes only the
document until you publish.

## Checking the site: Verify Payment Setup

Choose **Tools > Forms > Verify Payment Setup...**, pick the site if QUILL
asks, and confirm with **Read Setup**. QUILL asks the site, over your
ordinary WordPress connection, what it is ready for. It shows a short report:

```
Test mode
stripe: configured, webhook ready
paypal: not configured, webhook not ready
```

- **Test mode** or **Live mode** is the site's mode.
- **configured** means the site checked its keys with the provider for that
  mode. Keys typed in but never checked do not count.
- **webhook ready** means the provider can tell the site when a payment
  succeeds, fails or is refunded, and the site has verified that.

Nothing is charged and nothing is changed by this check.

## Publishing, and what each refusal means

Choose **Tools > Forms > Publish Form...** as for any form. For a paid form
the confirmation says what kind of payments it will take: "Payment mode:
test payments only, USD, stripe" or "LIVE payments: real money". Before it
sends anything, QUILL reads the site's payment setup again and refuses if
the site is not ready. Publishing a form as Live means people can see it; it
has nothing to do with test or live payments.

When QUILL refuses, it says why. Here is what each message means and what
to do:

- **"Update the site's QAF plugin to a version supporting payments."** The
  site answered with the plugin's old name (BITS Accessible Forms). Update
  the plugin.
- **"The site's QAF plugin does not support payments yet. Update the
  plugin."** The plugin is QAF, but a version from before payments. Update
  it.
- **"The site did not return a supported payment settings contract."** The
  site answered, but not in a way QUILL recognises. This usually means a
  newer or older contract than QUILL knows; update QUILL or the plugin so
  they match.
- **"The form and site must use the same payment test/live mode."** Either
  check Test mode in Form Payments Setup, or ask the site owner to switch the
  site's mode.
- **"Configure stripe and verify its webhook in WordPress before
  publishing."** (or paypal) A provider this form uses is not ready on the
  site. In wp-admin, under QAF Forms > Payments, use Check Connection and
  Create Webhook for it, or remove it from Providers in Form Payments Setup.
- **"Set up this form's payments before publishing it."** The form has a
  payment field but no payment settings. Use Form Payments Setup.
- **"The form's payment settings are not valid."** QUILL's checks passed but
  the site's did not, and the rest of the message says which rule. The most
  common is a currency one of your providers does not take.
- **A message about permission or signing in.** Your WordPress account on
  that site cannot read payment settings. Only administrators, or users the
  site owner has given the payment-management permission, can.
- **"Publish Form is off in Safe Mode..."** Safe Mode stops everything that
  reaches a site. Writing and checking the form still work.

## Trying it on the site: Test on Site

Put the form on a page with **Insert Form Into Page...**, publish the page,
then choose **Tools > Forms > Test on Site** with the form in front of you.
For a paid form QUILL asks first, then reads the form as published. If the
published form is not in test mode, it refuses with "The published form is
not in payment test mode", and opens nothing: your own document saying test
mode is not good enough, because the site's copy is what takes money.

When it opens the page, QUILL tells you what to pay with: "To pay in test
mode, use Stripe's test card 4242 4242 4242 4242 with any future date and any
three-digit code, or a PayPal sandbox buyer account. Never a real card."

A few more Stripe test cards are worth trying: `4000 0000 0000 0002` is
declined, and `4000 0025 0000 3155` asks for an extra bank check. Stripe
lists the rest in [its testing guide](https://docs.stripe.com/testing). For
PayPal, sign in with a sandbox personal account from the PayPal Developer
Dashboard, never your own account.

## What the person paying hears and does

This is the published form with NVDA or JAWS, in browse mode, from the top.
The wording is the plugin's own.

1. **The questions.** They fill in the form as usual. The payment field
   reads as its label followed by what it costs: "Registration fee. Amount
   due: 25.00 USD. You pay by card (through Stripe) or PayPal after you send
   the form." In test mode it adds "Test mode: no real money is taken. Use a
   test card from the provider, never a real one."
2. **A donation.** The field is an edit box, "Your gift, in USD, required",
   with the hint "Give from 5.00 USD to 500.00 USD." read with it. They type
   the amount: `20`, or `20.50`.
3. **Sending.** They press the Submit button. If something needs fixing, the
   problem is announced and focus goes to the first field at fault, with its
   message read as the field's description: "The smallest gift this form takes
   is 5.00 USD."
4. **The answers are saved.** The site says "Your answers are saved. To
   finish, pay 25.00 USD below." Nothing has been charged yet.
5. **The payment panel.** Focus moves to a new heading, "Pay 25.00 USD", so
   the screen reader announces it straight away. Below it: "Your answers are
   saved. Your payment is not taken until you finish here."
6. **Choosing how to pay.** With two providers there is a group of radio
   buttons, "How do you want to pay?", with "Card, through Stripe" and
   "PayPal". The first is already chosen. Arrow keys change it.
7. **Paying by card.** "Loading the payment form." and then "The payment form
   is ready." are announced. Tab moves into the card group, which is Stripe's
   own fields: card number, expiry date, security code, and sometimes country
   and postcode. Each has a label and reads its own errors. After the last
   field comes the button "Pay 25.00 USD". Pressing it announces "Sending
   your payment. Please wait."
8. **An extra bank check.** Some cards ask the bank to confirm, the step
   called 3-D Secure. It opens as a dialog on the same page, or as the bank's
   own page; when they come back, the panel says "Welcome back. Checking your
   payment."
9. **Paying with PayPal.** "The PayPal button is ready. It opens PayPal in a
   new window." They press the PayPal button, sign in and approve in the
   PayPal window, and are brought back. The panel says "Checking your payment
   with the site." Approving in PayPal is not payment on its own; the site
   takes the payment and then reports the result.
10. **The result.** Success is "Payment complete. Thank you.", with focus back
    on the panel's heading, and a link "View your receipt" when Stripe has
    one. A manual-capture form says "Payment authorized. You will be charged
    when the site owner confirms."
11. **When it fails.** An alert says what happened, in words: "The payment did
    not go through. You can try again. Your card was declined." A "Try again"
    button follows. It is the same entry; trying again does not send the form
    a second time.
12. **When PayPal is closed early.** "PayPal was closed before the payment
    finished. You can try again."
13. **When the result is not known yet.** Some payments take a moment. The
    panel says "Your payment is not complete yet." and offers a "Check payment
    again" button rather than a second payment.

Two more things they might hear:

- **"Your answers were already saved."** They sent the same form twice, by a
  double press or a slow connection. The first entry stands and nothing is
  charged twice.
- **"This form cannot take payment right now, so your answers were not
  sent."** The site is not ready for this form's payments: the wrong mode,
  or a provider not set up. Nothing was saved. This is the message to report
  to the site owner.

Everything works from the keyboard. Nothing is shown by colour alone. The
card fields and the PayPal button are Stripe's and PayPal's own, which both
companies build for screen readers, but they are not QUILL's, so try them
with your own screen reader before you go live.

## Receipts

- **Stripe** makes a receipt for each card payment. The person paying gets a
  "View your receipt" link at the end, and Stripe emails a receipt too if
  receipts are turned on in the Stripe Dashboard. The receipt address also
  appears in the response in QUILL, as "Payment receipt url".
- **PayPal** emails its own receipt to the person paying. There is no
  receipt link in the response.
- QUILL shows a receipt address as text and never opens it by itself.

If the form sends its own confirmation email, it goes when the answers are
saved, before payment. Word it so it does not promise that payment has been
received.

## Seeing who paid: Responses

Choose **Tools > Forms > Responses...**. Each response in the list ends with
its payment, in words: "Response 41, 3 November, 2:10 PM, Jane Smith, Event
registration, Payment: paid, 25.00, USD, Stripe".

The payment can be:

- **waiting for payment:** the answers came in, but nothing has been paid.
- **authorized, not yet captured:** a manual-capture payment you have not
  taken yet.
- **paid**
- **payment failed:** declined, or given up. The person may still try again.
- **cancelled:** stopped, or an authorization that was voided or ran out.
- **partly refunded** and **refunded**

A response with no payment at all means the site has no payment record for
it, which is not the same as paid.

- **Read** gives the whole response one line at a time, with the payment's
  provider, status, amount, currency, receipt address and transaction ID at
  the end.
- **Refresh Payment Status** asks the site again, after confirming which site.
  It reads what the site knows; it never takes, captures or refunds money.
- **Export to CSV...** and **Export to Word...** include the payment details.
  In CSV the status stays as the plugin's own code (`partially_refunded`,
  for instance), which sorts and filters well in a spreadsheet.

The site's own report, under QAF Forms > Payments in wp-admin, lists recent
payments with totals per currency: taken, refunded, kept, and authorized but
not yet captured.

## Refunds

Refunds are made in the Stripe or PayPal dashboard, not in QUILL and not in
wp-admin. The provider tells the site, the response becomes **partly
refunded** or **refunded**, and Refresh Payment Status shows it. A partial
refund is never shown as a full one, and a refunded payment never goes back
to paid.

## Manual capture

With Capture set to Manual, a payment stops at **authorized, not yet
captured**. Take the money in the Stripe or PayPal dashboard when you are
ready, and the response becomes paid. If you void it, or the authorization
runs out, it becomes cancelled. How long an authorization lasts depends on
the provider and the card: about a week for most cards through Stripe, and
PayPal sets its own limits. Do not leave one waiting for long.

## Moving from test to live

When every test has worked, including a decline and a refund:

1. The site owner adds the live keys under QAF Forms > Payments, uses Check
   Connection and Create Webhook for live, and switches the site to Live,
   which needs its own confirming check box.
2. In QUILL, open the form, choose Form Payments Setup, uncheck Test mode,
   press Save in Form and confirm Use Live Mode.
3. Run Verify Payment Setup. It should say Live mode, and configured and
   webhook ready for each provider the form uses.
4. Publish the form again. The confirmation says "LIVE payments: real money".
5. Test on Site now refuses this form, on purpose. To check the live form,
   open its page in your browser yourself, and make one small real payment
   you then refund.

Any of your forms still in test mode stop taking payment once the site is
live. Switch them too, or take them down.

## Troubleshooting

- **There is no Form Payments Setup in Tools > Forms.** Turn on Form Payments
  in Profiles and Features. The commands are dimmed until a form is open.
- **"Turn on Form Payments in Features before using this command."** The
  same: the feature is off.
- **"Fix the form's source errors with Check This Form first."** The form has
  mistakes elsewhere; payment commands wait until it reads cleanly.
- **"Payment field was not inserted"** or **"Payment setup was not saved"**,
  followed by a reason. Nothing changed; fix what the reason says and try
  again.
- **Publishing is refused.** See the list under "Publishing, and what each
  refusal means".
- **Test on Site says the published form is not in test mode.** Your document
  may say test mode, but the site's copy does not. Publish again.
- **People can send the form, but every payment stays "waiting for payment".**
  The provider cannot reach the site's webhook. Ask the site owner to check
  the Readiness table in QAF Forms > Payments and run Create Webhook again.
- **A response has no payment at all.** It was sent before the form took
  payment, or its payment field was hidden by a condition, so nothing was
  owed.
- **The amount is not what the page showed.** The site's working wins. Check
  the products' prices and the quantity field's link to its product
  (`@linked_product`), and any calculation on the total.

## Privacy and safety

- QUILL never stores, sends or asks for a payment key, and has no setting for
  one. The plugin keeps them on the site, and its screens never show a secret
  again once saved.
- Card numbers go from the person's browser straight to Stripe or PayPal.
  They never reach the site or QUILL.
- Every network step in QUILL asks first and names the site: Verify Payment
  Setup, Publish Form, Test on Site and Refresh Payment Status. Safe Mode
  turns all of them off.
- Responses are personal data, payments included. Exports go where you put
  them, and nowhere else.

---

- Previous: [Chapter 17: Forms](quill-guide-17-forms.html)
- Next: [A last word](quill-guide-a-last-word.html)
- [Contents](../userguide.html)
