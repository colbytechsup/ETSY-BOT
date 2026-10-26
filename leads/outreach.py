"""Follow-up email draft for the CertRig hazmat course.

Config comes from env vars (see certrig.env.example). Nothing here knows the real course
details. Legal notes: CAN-SPAM requires a commercial email to identify the sender, carry an
honest subject, include a working opt-out, and show a valid physical postal address, so set
LEADS_POSTAL_ADDRESS before real sends. Job applicants did not ask for marketing, so the
first message says plainly why they're hearing from you. I am not a lawyer; verify."""

TEMPLATE = """Subject: {first_name}, a hazmat endorsement could open more doors

Hi {first_name},

Thanks for reaching out{about_job}. I'm {sender_name} with {company}.

A lot of the drivers we talk to find that a hazmat endorsement is what gets them into the
higher-paying loads. We run the CertRig hazmat course to help with exactly that.{course_line}

If you'd like details on dates and cost, just reply to this email{phone_line}.
If you'd rather not hear from us about training, reply "stop" and I'll take you off the list.

{sender_name}
{company}{postal_line}
"""


def draft(lead, sender_name="[your name]", company="[company]", phone="", course_url="",
          postal_address=""):
    first = (lead.get("name") or "there").split()[0]
    job = lead.get("job_title")
    return TEMPLATE.format(
        first_name=first, sender_name=sender_name, company=company,
        about_job=f" about the {job} position" if job else "",
        course_line=f"\nMore about the course: {course_url}" if course_url else "",
        phone_line=f" or call {phone}" if phone else "",
        postal_line=f"\n{postal_address}" if postal_address else "",
    )
