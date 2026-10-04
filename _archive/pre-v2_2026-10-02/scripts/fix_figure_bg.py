from PIL import Image

# Open the image
img = Image.open('Figure.png')

# Convert to RGB if it has transparency
if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
    # Create a white background
    bg = Image.new('RGB', img.size, (255, 255, 255))
    # If image has alpha channel, use it as mask
    if img.mode == 'RGBA':
        bg.paste(img, mask=img.split()[3])
    else:
        bg.paste(img)
    bg.save('Figure.png')
    print('Converted to white background')
else:
    # Just convert to RGB
    img.convert('RGB').save('Figure.png')
    print('Converted to RGB with white background')
