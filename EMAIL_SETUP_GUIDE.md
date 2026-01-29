# 📧 EMAIL NOTIFICATIONS SETUP GUIDE

## 🎯 What You Need To Provide

I've created the email system! Now I need these details from you:

### 1. Email Provider
Which email service do you use?
- [ ] Gmail (most common)
- [ ] Outlook/Hotmail
- [ ] Yahoo
- [ ] Custom SMTP server

### 2. Email Addresses
- **FROM email** (surveillance system sends from): ________________
- **TO email** (where you receive alerts): ________________

### 3. App Password (IMPORTANT!)
For security, modern email providers require "App Passwords" instead of your regular password.

---

## 📝 HOW TO GET APP PASSWORD

### For Gmail (Recommended):

**Step 1: Enable 2-Factor Authentication**
1. Go to: https://myaccount.google.com/security
2. Find "2-Step Verification"
3. Turn it ON (if not already)

**Step 2: Create App Password**
1. Go to: https://myaccount.google.com/apppasswords
2. Or: Google Account → Security → 2-Step Verification → App passwords
3. Select:
   - App: **Mail**
   - Device: **Other (Custom name)**
   - Name it: **SentinTinel Surveillance**
4. Click **Generate**
5. **Copy the 16-character password** (looks like: `abcd efgh ijkl mnop`)
6. **Save it** - you'll need it!

### For Outlook/Hotmail:

**Step 1: Enable App Passwords**
1. Go to: https://account.microsoft.com/security
2. Click "Advanced security options"
3. Under "App passwords", click "Create new app password"
4. Copy the generated password

### For Yahoo:

**Step 1: Generate App Password**
1. Go to: https://login.yahoo.com/account/security
2. Click "Generate app password"
3. Select "Other App"
4. Name it: "SentinTinel"
5. Copy the generated password

---

## 🔧 CONFIGURATION DETAILS NEEDED

Please provide these details:

```
1. Email Provider: [Gmail/Outlook/Yahoo/Other]

2. FROM Email Address: [your-surveillance@email.com]

3. TO Email Address: [where-you-want-alerts@email.com]

4. App Password: [16-character password from above]

5. Notification Preferences:
   - Send email for CRITICAL alerts (95%+ confidence)? [Yes/No]
   - Send email for 2-minute summaries? [Yes/No]
   - Include images in emails? [Yes/No]
```

---

## 📊 SMTP SETTINGS (AUTO-CONFIGURED)

Based on your provider, I'll use these settings:

### Gmail:
```
SMTP Server: smtp.gmail.com
Port: 587
Security: TLS
```

### Outlook:
```
SMTP Server: smtp-mail.outlook.com
Port: 587
Security: TLS
```

### Yahoo:
```
SMTP Server: smtp.mail.yahoo.com
Port: 587
Security: TLS
```

---

## 🎨 EMAIL FEATURES

### Critical Alert Email:
```
Subject: 🚨 CRITICAL: Person Left Camera Frame

Body:
- Alert message (human-like, as you requested)
- Camera ID
- Confidence percentage
- Timestamp
- Attached image (before/after for activity detection)
```

### 2-Minute Summary Email:
```
Subject: 📊 Activity Summary (2-min)

Body:
- Time period covered
- Number of events detected
- Most significant event description
- Peak confidence level
- Top 5 events list
- Image of most significant event
```

---

## ✅ WHAT GETS EMAILED (No Noise!)

### ✓ WILL Email:
- ✅ Critical alerts (95%+ confidence)
- ✅ EMERGENCY activity detections (person leaving, etc.)
- ✅ Dangerous keywords detected (weapon, fire, etc.)
- ✅ 2-minute summaries (when significant events occurred)

### ✗ WON'T Email:
- ❌ Low confidence detections (<60%)
- ❌ Regular scene narrations
- ❌ Generic analysis updates
- ❌ Minor significance events

---

## 🚀 QUICK SETUP (Once You Provide Details)

After you give me the information, I'll:

1. **Add to .env file:**
```bash
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENT=where-you-want-alerts@email.com
```

2. **Update config.py** to include email settings

3. **Integrate with main.py** to send emails on:
   - Critical alerts
   - 2-minute summaries

4. **Test it!**

---

## 🧪 TEST EMAIL

Once configured, I'll send a test email to verify it works!

---

## 📝 REPLY WITH THIS FORMAT

To make it easy, just copy and fill this out:

```
Email Provider: Gmail

FROM Email: sentintinel.surveillance@gmail.com

TO Email: myemail@gmail.com

App Password: abcd efgh ijkl mnop

Preferences:
- Critical alerts via email: Yes
- 2-minute summaries via email: Yes
- Include images: Yes
```

---

## 🔒 SECURITY NOTES

**Why App Password?**
- More secure than using your real password
- Can be revoked without changing main password
- Specific to this app only

**Your password is safe:**
- Stored only in .env file (never in code)
- Not synced to git (.env is in .gitignore)
- Only accessible on your local machine

---

## 💡 RECOMMENDATIONS

### For Best Results:
1. **Use Gmail** - Most reliable, well-tested
2. **Create dedicated email** - Optional but cleaner
   - Example: `sentintinel.alerts@gmail.com`
3. **Enable images** - Visual evidence is helpful
4. **Test with low-stakes alert first** - Before relying on it

---

## ❓ HAVE QUESTIONS?

Common questions:

**Q: Can I use my regular Gmail password?**
A: No, Gmail requires App Password for security.

**Q: Can I send to multiple email addresses?**
A: Yes! Provide them as comma-separated: `email1@gmail.com,email2@gmail.com`

**Q: Will this work on my phone?**
A: Yes! Standard email, works on all devices.

**Q: How fast are emails delivered?**
A: Usually within 5-10 seconds of the alert.

---

## 🎯 NEXT STEPS

**Please provide:**
1. Email provider
2. FROM email
3. TO email
4. App password
5. Preferences

Then I'll:
1. Configure the system
2. Test it
3. Show you how it works!

**Ready? Share your email details!** 📧

