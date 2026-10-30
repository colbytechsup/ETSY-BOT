# Toddr.ai Pilot 1: the preschool

Purpose: first real-world run of the product on a business we own, to (a) confirm each feature
works, (b) find bugs, (c) produce a before/after case study with real numbers, and (d) settle
the review-gating question with evidence.

## Day-0 baseline (recorded 2026-10-30 from a Google search paste)

Coastal Children's Learning Center Preschool, Costa Mesa CA: 4.7 stars, 16 Google reviews,
about 3 reviews in the last 12 months, 5 rating-only reviews, 310+ Facebook followers.
Competitors, from Todd's screenshots taken 2026-10-30 (Google unless noted):

| Business | Google rating | Google reviews | Yelp | Note |
|---|---|---|---|---|
| **Coastal Children's Learning Center** | 4.7 | 16 | not checked | ~3 reviews in last 12 months |
| Nobis Preschool | 4.4 | 19 | | newest review 2 months ago |
| Heritage Montessori (Costa Mesa) | not visible | not visible | 4.5 (47) | Google shows "Posting is currently turned off" on its reviews |
| Kiddie Academy of Costa Mesa (national franchise) | 4.6 | 11 | | newest visible review ~1 year ago |
| Gaowa Montessori School | no Google listing found | | ~27 (approx.) | Yelp only |

What this says: Coastal is **not** behind on Google. It has the highest rating in the set and
the second-highest count, and the one true chain (Kiddie Academy) has only 11. The gap is on
Yelp, where Heritage and Gaowa are strong, and Yelp prohibits soliciting reviews, so that gap
cannot be closed with Toddr.ai. The honest pilot story is therefore "from mid-pack to the clear
number one in Costa Mesa preschool search", which needs roughly 20 to 30 new Google reviews.
With 39 licensed seats (state facility record shows capacity 39) and parents who are already
positive, that is reachable in 60 to 90 days if the request flow works.

The "Posting is currently turned off" notice on Heritage's profile means Google has restricted
new reviews on that business. I am not certain of the reason in their case; Google does this
for suspected policy problems and sometimes for other reasons. It is a live local example of
why the gating decision matters.

## Before day 0

- [ ] **Baseline screenshot** of the preschool's Google Business Profile: review count, star rating,
      date. Also note the top 3 competing chains' counts. This is the "before" in the case study.
- [ ] **Consent.** Parents will receive texts or emails from the school. Confirm the school has a
      contact consent on file (enrollment forms usually include one; check). Send from the
      school's name, include "Reply STOP to opt out". US texting rules (TCPA) apply even to a
      preschool; I am not a lawyer, verify if in doubt.
- [ ] **Decide gating on or off** for this pilot (gameplan section 9). Recommendation: off, both
      links to everyone.
- [ ] **Child privacy rule.** Nothing with a child's full name, face, or classroom goes into an
      auto-generated social post or video. This must be tested, not assumed (test 9 below).
- [ ] **Small first batch.** 10 parents you know are friendly, not the whole roster. Expand after
      the first batch comes back clean.
- [ ] Pick one person (Todd) to be the "owner" account and one email to receive every
      notification the product sends, so nothing goes unseen.

## Test log

Keep one row per test in `toddr-pilot-test-log.csv` (template in this folder). Columns: test id,
date, what you did, expected, actual, pass/fail, screenshot filename, notes.

## Tests, in the order to run them

**Setup**
1. Sign up the preschool from scratch. Time it. Note every field that was confusing or unclear.
2. Connect the Google Business Profile. Does it ask for the right Google account? Does it show the
   correct location? What permission scopes does it ask for (screenshot the consent screen)?
3. Connect the school's Facebook Page and Instagram. Same: screenshot the permission screen.
   If Instagram will not connect, note whether the account is a Business/Creator account; personal
   accounts cannot be posted to by apps, as I understand Meta's rules.
4. Add 10 parents. Note the method (manual, CSV, something else) and how long it takes.
   Include one bad phone number and one bad email on purpose.

**The request flow (this is the core)**
5. Trigger the first batch. For each parent record: did the text arrive, how long after, what did
   it say, sender name or number, did the link work on an iPhone and an Android.
6. Click the link as a parent. Record every screen. Specifically: is there a "how was your
   experience" pre-screen? If yes, what happens on a negative answer? Where does "somewhere else"
   go? Is the Google link visible on the negative path at all? Screenshot each path.
7. Leave one real positive review from a willing parent. Time from clicking to it appearing on
   Google. Time from appearing on Google to Toddr.ai noticing it.
8. Have one parent submit a negative pre-screen answer (or a 3-star review if gating is off).
   Does the owner get notified? How fast? Is the message useful?
9. **Child privacy test.** Have a friendly parent write a positive review that includes a child's
   first and last name and a teacher's name. Does the generated social post or video reproduce
   the child's name? If yes, that is a blocker for the preschool market.
10. Do not click the link on two records. Confirm the follow-up reminder arrives, when, and that
    it stops after a reasonable number. Reply STOP to one and confirm the reminders stop.
11. Enter the same parent twice. Confirm they get one message, not two.

**The publishing flow**
12. Approve a review for social posting (or let it auto-post, whichever the product does).
    Check Facebook and Instagram. Screenshot the post. Note: image quality, text overflow, logo,
    whether it links anywhere, whether it posted twice.
13. Post to Google Business Profile. Confirm what was posted is a GBP *Update*, not something that
    could be mistaken for a review. Screenshot.
14. AI reply to the positive review. Read it as the parent would. Does it sound like the school or
    like a robot? Does it mention anything that is not in the review (made up details)? Can the
    owner edit before it posts?
15. Video generation from the best review. Time to render, does it play on a phone, is the
    branding right, does it say anything the review did not.

**Dashboard and account**
16. Compare dashboard counts (sent, opened, reviews, posts) to what actually happened in tests 5
    to 15. Any mismatch is a bug.
17. Log out, log back in, forgot-password flow.
18. Open the dashboard on a phone.
19. Cancel the account (or whatever the cancel path is), then confirm no further messages go out
    to parents. Reactivate.

**Light stress**
20. Add the remaining parents (the full roster) in one go. Note import time, any failures, and
    whether sends are spread out or all at once.
21. While that batch is sending, pull the Facebook connection (revoke the app in Facebook
    settings). Does the product notice and tell the owner, or fail silently?

## What "done" looks like for the pilot

- Every test above has a pass/fail and a screenshot.
- A list of bugs, ranked: blocker (cannot launch), major (fix before marketing), minor.
- The before/after numbers for the preschool after 30 days, with screenshots.
- A written decision on gating.
- One real parent testimonial (with permission) to replace the AI ones on the website.
