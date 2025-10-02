# 🔐 Security Guide for Pet Chip Reader

## ⚠️ IMPORTANT SECURITY NOTICE

**NEVER commit `.env` files with real credentials to version control!**

GitLab/GitHub will scan for exposed secrets and warn you if they detect:
- API keys (OpenAI, Twilio, etc.)
- SMTP passwords
- Authentication tokens
- Private keys

## 🛡️ Secure Configuration Steps

### 1. Set Up Production Configuration

```bash
# Copy example to working file
cp rfid_cam/.env.example rfid_cam/.env

# Edit with your real credentials
nano rfid_cam/.env
```

### 2. Verify .env is Ignored

```bash
# Check .gitignore contains:
cat .gitignore | grep -E "\.env|production"

# Should show:
# .env
# rfid_cam/.env
# rfid_cam/.env.production
# *.env.production
# *.env.local
```

### 3. Check Git Status

```bash
# .env files should NEVER appear here:
git status

# If .env appears, remove it:
git rm --cached rfid_cam/.env
```

## 🔑 Credential Sources

### OpenAI API Key
- Get from: https://platform.openai.com/api-keys
- Format: `sk-proj-...`
- Used for: Animal identification in photos

### Gmail App Password
- Enable 2FA first: https://myaccount.google.com/security
- Create App Password: https://support.google.com/accounts/answer/185833
- Format: 16 characters like `abcd efgh ijkl mnop`
- Used for: Email notifications

### Twilio Credentials (Optional)
- Get from: https://www.twilio.com/console
- Account SID: `ACxxxxx...`
- Auth Token: `xxxxx...`
- Phone number: `+1234567890`
- Used for: SMS notifications

## 🚨 If Credentials Are Exposed

### If GitLab/GitHub Warns You:

1. **Immediate Actions:**
   ```bash
   # Remove from git history (if committed)
   git filter-branch --tree-filter 'rm -f rfid_cam/.env' -- --all
   git push --force
   ```

2. **Regenerate ALL Exposed Credentials:**
   - OpenAI: Create new API key, delete old one
   - Gmail: Generate new App Password
   - Twilio: Rotate Auth Token

3. **Update Production System:**
   ```bash
   # Update production .env file
   sudo systemctl stop rfid_cam
   nano rfid_cam/.env
   sudo systemctl start rfid_cam
   ```

## ✅ Safe Practices

- ✅ Use `.env.example` for templates (safe to commit)
- ✅ Keep real `.env` files local only
- ✅ Use environment variables in production
- ✅ Rotate credentials regularly
- ✅ Use App Passwords, not main passwords

- ❌ Never commit `.env` files
- ❌ Never hardcode secrets in source code  
- ❌ Never share credentials in chat/email
- ❌ Never use production credentials for testing

## 🔄 Emergency Recovery

If you accidentally commit secrets:

```bash
# 1. Stop the breach
git rm --cached rfid_cam/.env
git commit -m "Remove exposed .env file"

# 2. Clean history
git filter-branch --tree-filter 'rm -f rfid_cam/.env' -- --all
git push --force

# 3. Regenerate ALL exposed credentials
# 4. Update production systems with new credentials
```

## 📞 Support

If you need help with security issues:
- GitHub: https://docs.github.com/en/code-security/secret-scanning
- GitLab: https://docs.gitlab.com/ee/user/application_security/secret_detection/