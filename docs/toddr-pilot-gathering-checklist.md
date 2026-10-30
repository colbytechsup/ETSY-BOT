# Pilot 1 gathering checklist (step by step)

Business: Coastal Children's Learning Center Preschool, 2245 Orange Ave, Costa Mesa, CA 92627.
Google profile name as shown: "Coastal Childrens Learning Center Preschool".

Do these in order. Each step says what to do, what to send me, and why. "Send me" means paste
the text or describe the screenshot in chat, or drop the screenshot into the repo folder
`docs/pilot-screenshots/` (create it) and push, or tell me where you put it. Phone screenshots
are fine.

## Step 1. Day-0 baseline (15 minutes, do today, before anything is sent)

From your paste, as of 2026-10-30:

| Item | Value | Source |
|---|---|---|
| Google rating | 4.7 | your paste |
| Google review count | 16 | your paste |
| Reviews in the last 12 months | 3 (Gladis Medina ~1 month, Sheena Stewart ~7 months, De Anne Shea ~7 months, Trent Bryson ~7 months rating only) | your paste, approximate |
| Reviews with no text (rating only) | 5 (Trent Bryson, Trang PT Nguyen, Lucian Chiriac, Andrew Stclair, plus one unclear) | your paste, approximate |
| Oldest review | ~14 years | your paste |
| Facebook followers | 310+ | your paste |
| Yelp listing | exists, 42 photos | your paste (Yelp prohibits asking for reviews; leave it alone) |

What to do:
1. On your phone, search Google for the school, tap the review count, sort by **Newest**, and
   screenshot the top of the list so the date is visible. Save as `baseline-google-2026-10-30.png`.
2. Search each competitor Google suggested and write down rating and review count:
   - Nobis Preschool
   - Heritage Montessori School of Newport Beach - Costa Mesa
   - Kiddie Academy of Costa Mesa
   - Gaowa Montessori School
   Send me the four numbers. That is the "losing to larger chains" line for the case study.
3. Screenshot the school's Facebook page header (follower count visible) and Instagram profile
   (follower count visible). If the school has no Instagram, say so.

Why: the case study is only credible with a dated "before" that we can show.

## Step 2. Something is already posting to the school's Google profile. Find out what.

Your paste shows a new Google Business Profile post almost every day since at least Oct 9
("Ride, roll, and draw", "Where friendships take shape", etc.), and owner replies dated "9 months
ago" on reviews that are 6 to 14 years old, which looks like a bulk reply tool was run around
February 2026.

Ask your mom (or whoever runs the profile):
- Is Toddr.ai already connected to this Google profile? Or is it another tool, or a person?
- Who wrote the daily posts?
- Who replied to the old reviews 9 months ago?

Send me the answer. Why: if Toddr.ai is already running here, the pilot is partly live and we
should be measuring it, not starting over. If it is another tool, we need to disconnect it first
so results are not mixed.

Also note for later: the reply to Trang PT Nguyen reads "Thank you so much for review!" (missing
"your"). If that was an AI reply, that is a quality bug to log.

## Step 3. The Toddr.ai app itself (30 minutes)

You said customers "download the app and login". I need to know exactly what that is.

1. Tell me: App Store or Google Play? The exact app name as listed? Is there also a website login
   (an address like app.toddr.ai or dashboard.toddr.ai)? Who built the app (Hesper IT Labs?).
2. Log in and screenshot **every screen you can reach**, including settings pages. Name them
   `app-01-login.png`, `app-02-home.png`, and so on. Especially:
   - the home / dashboard
   - the "add customer" screen and any import option
   - the message templates (and paste me the exact default text of the first request and the
     reminder, word for word)
   - the integrations / connected accounts screen (Google, Facebook, Instagram)
   - any settings about timing (when messages send, how many reminders)
   - billing / plan screen
   - the account or "about" screen with the app version number
3. Tell me whose login this is (yours or your mom's) and whether there is more than one account.

Why: I cannot see the product, so your screenshots are my only view of it. From these I can tell
you which tests apply and spot problems before you text any parents.

## Step 4. Send one request to yourself (10 minutes). Do not send to parents yet.

1. In the app, add yourself as a customer with your own cell number and email.
2. Trigger a review request to yourself.
3. Screenshot the text message exactly as it arrives. I need: the sender (phone number or
   short code), the full message text, and the time it arrived versus when you sent it.
4. Long-press the link in the text, choose "Copy link", and paste me the full address.
5. Screenshot the email version too, including the "from" address.
6. Tap the link and screenshot **every screen** until it ends. If it asks "how was your
   experience", answer negatively first, screenshot where it sends you, then redo it answering
   positively. Both paths, every screen.
7. Reply STOP to the text. Screenshot what comes back, if anything.
8. Do not click the link on a second test record and wait. Tell me when (and if) the reminder
   arrives and what it says.

Why: this is tests 5, 6, 8 and 10 from the pilot script, done safely on yourself first. Step 6
is the one that settles the review-gating question with evidence instead of description.

## Step 5. Consent and privacy (ask your mom, 10 minutes)

1. Does the enrollment paperwork say the school may contact parents by text and email? Take a
   photo of that paragraph. If there is no such line, we add a one-line opt-in before any texts
   go out (I will draft it).
2. Who at the school is comfortable being the "owner" contact in the app, and which email should
   get every notification?
3. Pick 10 friendly parents for batch 1. Names and numbers stay with you; I only need to know
   the count and that they were picked.

## Step 6. Social accounts (10 minutes)

1. Instagram: open the school's Instagram, go to Settings, Account type. It must be a Business
   or Creator account for any app to post to it. Tell me which it is.
2. Facebook: confirm who is an Admin on the school's Page (Page settings, Page access). The
   person who connects Toddr.ai must be an Admin.
3. Which Facebook account was used to connect the page in Toddr.ai, if it is already connected?

## Step 7. Let me see the website (2 minutes)

In this Claude session's title bar, open the cloud environment menu, choose Edit, and under
Network access add `toddr.ai` (and `app.toddr.ai` if that exists) to Allowed domains. Steps:
https://code.claude.com/docs/en/cloud-environments#network-access
Then tell me, and I will audit the live site, FAQ, privacy policy, and whatever the review link
from step 4 points to.

## Step 8. Ask Hesper IT Labs (or whoever built the app) for access

Copy and send this:

> Hi, we are preparing Toddr.ai for launch and running a structured QA and load test. Could you
> provide: (1) read access to the application source repository on GitHub for our technical
> reviewer, (2) a staging environment with a test account that does not send real messages,
> (3) the names of the providers used for SMS, email, AI, hosting, and payments, and (4) whether
> the SMS sending number is registered for A2P 10DLC and whether the Meta app has passed App
> Review for posting to Pages and Instagram. Thanks.

Send me whatever they reply. Why: without the code and a staging environment, stress testing
and the security checks cannot be done honestly, and the 10DLC and Meta App Review answers
decide whether texts and posts will work at scale at all.

## Order of operations

Today: steps 1, 2, 3, 7. Tomorrow: steps 4, 5, 6. This week: step 8.
Nothing goes to parents until step 4 is clean and the gating decision is made.
