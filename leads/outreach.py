"""Follow-up email draft for the CertRig hazmat course. Fill the placeholders with your real
details; nothing below (price, dates, URL) is known to the code. Check the legal notes in the
README before sending: job applicants did not ask for marketing, so the first message should
be honest about why they're hearing from you and how to opt out."""

TEMPLATE = """Subject: {first_name}, a hazmat endorsement could open more doors

Hi {first_name},

Thanks for reaching out{about_job}. I'm {sender_name} with {company}.

A lot of the drivers we talk to find that a hazmat endorsement is what gets them into the
higher-paying loads. We run the CertRig hazmat course to help with exactly that:
{course_url}

If you'd like details on dates and cost, just reply to this email or call {phone}.
If you'd rather not hear from us about training, reply "stop" and I'll take you off the list.

{sender_name}
{company}
{phone}
"""


def draft(lead, sender_name="[your name]", company="[company]", phone="[phone]",
          course_url="[course URL]"):
    first = (lead.get("name") or "there").split()[0]
    job = lead.get("job_title")
    return TEMPLATE.format(first_name=first, sender_name=sender_name, company=company,
                           phone=phone, course_url=course_url,
                           about_job=f" about the {job} position" if job else "")
