# PixelGuard User Guide

## Getting Started

### What is PixelGuard?

PixelGuard is an invisible image watermarking system that embeds tracking IDs into images. The watermarks are:
- **Imperceptible**: Invisible to the human eye
- **Robust**: Survive social media transformations (JPEG, resize, crop, blur)
- **Secure**: Difficult to detect or remove
- **Trackable**: Prove image ownership instantly

### Quick Start

1. **Visit the Application**
   - Go to http://localhost:3000
   - Or visit https://pixelguard.com

2. **Choose an Action**
   - **Encode**: Protect an image with a tracking ID
   - **Track**: Check if an image is protected and retrieve owner information

## Encoding Images

### Step 1: Upload Image

1. Click **"Encode"** in the navigation menu
2. Drag and drop your image or click to browse
3. Supported formats: JPG, PNG, BMP, GIF
4. Maximum file size: 50MB

### Step 2: Enter Metadata

1. **Owner Name** (required): Your name or organization name
2. **Email Address** (required): Contact email for ownership verification
3. **Location** (optional): Where the image was taken/created
4. **Description** (optional): Details about the image

### Step 3: Encode

1. Click **"Encode Image"** button
2. Wait for processing (~800ms)
3. You'll see the results:
   - **Tracking ID**: Unique identifier for your image
   - **PSNR**: Imperceptibility score (>40 dB is excellent)
   - **SSIM**: Similarity to original (>0.98 is very similar)

### Step 4: Download

1. Click **"Download Encoded Image"** to get your protected image
2. Use this image anywhere (social media, websites, etc.)
3. The watermark survives transformations

### Quality Metrics Explained

- **PSNR (Peak Signal-to-Noise Ratio)**
  - Measures imperceptibility
  - Scale: 0-100 dB
  - Higher is better (>40 dB = imperceptible)
  
- **SSIM (Structural Similarity Index)**
  - Measures perceptual similarity
  - Scale: -1 to 1
  - Higher is better (>0.98 = almost identical)

## Tracking Images

### Find Owner Information

1. Click **"Track"** in the navigation menu
2. Upload any image you want to check
3. The image can be:
   - Your original protected image
   - A copy from social media
   - A screenshot or cropped version
   - JPEG compressed version

### Interpret Results

If a tracking ID is found, you'll see:

- **Tracking ID**: The unique identifier
- **Owner Name**: Person/organization that protected it
- **Email**: Contact information
- **Location**: Where the image originates from (if provided)
- **Confidence**: How certain we are (0-100%)

### Confidence Score

- **90-100%**: Very reliable, definitely protected
- **80-89%**: Reliable, likely protected
- **70-79%**: Moderate reliability, possibly protected
- **<70%**: Low reliability, extraction uncertain

## Understanding Robustness

### What Distortions Are Tested?

PixelGuard watermarks survive:

1. **JPEG Compression** (Quality 50)
   - Common on social media
   - Removes some pixel information

2. **Resizing** (70% to 130%)
   - Scaling up or down
   - Instagram, Twitter often resize

3. **Cropping** (80% retained)
   - Cutting parts of image
   - Composition changes

4. **Gaussian Blur** (σ=1-2)
   - Intentional blurring
   - Anti-forensics technique

5. **Screenshot**
   - Taking screenshot of image
   - Re-encoding

### Test Robustness

1. On the Encode page, after successful encoding
2. You'll see test results for different distortions
3. Each shows success rate and confidence

## Best Practices

### Encoding Best Practices

1. **Use High-Quality Original**
   - Start with the best quality image
   - Minimum 256×256 pixels
   - Recommended: 512×512 or larger

2. **Complete Metadata**
   - Fill in all information
   - Use real email address
   - Add descriptive location

3. **Keep Original Safe**
   - Save the encoded image
   - Keep tracking ID somewhere
   - Document metadata

### Tracking Best Practices

1. **Act Quickly**
   - Track unauthorized use immediately
   - Create evidence trail
   - Document timestamps

2. **Verify Ownership**
   - Check email in results
   - Confirm metadata matches
   - Look at confidence score

3. **Save Evidence**
   - Screenshot tracking results
   - Document where found
   - Save image file

## Common Questions

### Q: Will the watermark show on my image?
**A:** No, it's invisible to human eyes. Your image looks identical to the original.

### Q: Can someone remove the watermark?
**A:** It's very difficult. The watermark is integrated into pixel values and survives common editing. Removing it would likely damage image quality.

### Q: Does it work on all file formats?
**A:** PixelGuard works on JPG, PNG, BMP, and GIF. Some formats like WebP may have reduced robustness.

### Q: How accurate is the tracking?
**A:** 95-99% accuracy after typical social media transformations. Heavily edited images may have lower accuracy.

### Q: What if confidence is below 70%?
**A:** The image may be heavily distorted or not contain a valid watermark. Try re-uploading or checking a different version.

### Q: How long does encoding take?
**A:** Typical encoding takes ~800ms (less than 1 second). Speed depends on image size and GPU availability.

### Q: Is my data private?
**A:** Yes. Images are processed and deleted immediately. Only metadata is stored for tracking purposes.

### Q: Can I use PixelGuard commercially?
**A:** Yes, see License section. Contact support for enterprise licensing.

## Troubleshooting

### Image Won't Upload

- Check file size (max 50MB)
- Verify file format (JPG, PNG, BMP, GIF)
- Ensure file isn't corrupted
- Try different browser if issue persists

### Encoding Fails

- Verify image is supported format
- Check internet connection
- Try smaller image file
- Clear browser cache and retry

### Tracking Returns No Results

- Image may not contain watermark
- Image heavily distorted
- Check confidence score (may be low)
- Try original version of image

### Poor Quality Metrics

- This usually indicates heavy distortion
- Try with less compressed version
- Larger original images work better
- Some formats have inherent limitations

## Support

### Getting Help

- **FAQ**: See Common Questions above
- **Email**: support@pixelguard.com
- **Documentation**: https://docs.pixelguard.com
- **GitHub**: https://github.com/pixelguard

### Report Issues

- Check existing issues on GitHub
- Provide reproduction steps
- Include image sample (if possible)
- Specify browser and operating system

### Feature Requests

- Submit via GitHub Issues
- Describe use case
- Suggest implementation approach
- Vote on existing feature requests

## Advanced Usage

### Batch Processing

For processing multiple images:

1. Use the API directly
2. See API documentation
3. Integrate with your workflow

### API Integration

```javascript
// Encode using API
const formData = new FormData();
formData.append('file', imageFile);
formData.append('owner_name', 'John Doe');
formData.append('owner_email', 'john@example.com');

const response = await fetch('https://api.pixelguard.com/api/v1/encode/', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('Tracking ID:', result.tracking_id);
```

### Rate Limits

- 10 encode requests per minute per IP
- 20 decode requests per minute per IP
- Contact support for higher limits

## Privacy Policy

PixelGuard respects your privacy:

- Images deleted after processing
- Metadata encrypted in database
- No tracking/analytics on content
- No sharing with third parties
- GDPR compliant

## Terms of Service

By using PixelGuard, you agree to:

- Use only for legitimate purposes
- Not to circumvent watermarks
- Respect intellectual property rights
- Comply with applicable laws

See full terms at https://pixelguard.com/terms
