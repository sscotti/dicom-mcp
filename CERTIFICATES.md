# Development Certificates

This repository includes self-signed SSL/TLS certificates for local development and testing.

## Certificate Files

- `cert.pem` - Public certificate (CN=localhost, valid for 3 years)
- `key.pem` - Private key (for DICOM TLS)
- `cert-key-combined.pem` - Combined certificate and key (for HTTPS)

## Security Notes

**These certificates are for development only:**
- Self-signed with CN=localhost
- Only valid for `localhost`, `*.localhost`, `127.0.0.1`, and `::1`
- Cannot be used to impersonate real domains
- Not trusted by browsers/systems by default

**Safe to commit because:**
- Low security risk (localhost-only)
- Convenient for team development
- Anyone cloning gets working localhost certs

**Usage:**
- Used by Orthanc for HTTPS web interface
- Used by Orthanc for DICOM TLS connections
- Required for testing secure connections locally

## Regenerating Certificates

If you need to regenerate these certificates:

```bash
# Generate new 3-year certificate for localhost
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 1095 -nodes \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1,IP:::1"

# Create combined file for HTTPS
cat cert.pem key.pem > cert-key-combined.pem

# Set proper permissions
chmod 600 key.pem
chmod 644 cert.pem cert-key-combined.pem
```

## Production

**Never use these certificates in production!** Use properly signed certificates from a Certificate Authority (CA) for production deployments.

