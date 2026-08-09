from collections import Counter
from PIL import Image

path='/tmp/qss-safe-nav-2.png'
im=Image.open(path).convert('RGB')
print('SIZE', im.size)
small=im.resize((160,100))
pixels=list(small.getdata())
for color,count in Counter(pixels).most_common(20):
    print('COLOR', color, count)
print('BRIGHTNESS_GRID')
w,h=im.size
for gy in range(10):
    row=[]
    for gx in range(16):
        x0=gx*w//16; x1=(gx+1)*w//16
        y0=gy*h//10; y1=(gy+1)*h//10
        crop=im.crop((x0,y0,x1,y1)).resize((1,1))
        r,g,b=crop.getpixel((0,0))
        lum=round((0.2126*r+0.7152*g+0.0722*b)/255*9)
        row.append(str(lum))
    print(''.join(row))
# Count bright and dark pixels by broad region.
for name,box in {
    'full':(0,0,w,h),
    'sidebar':(0,0,w//4,h),
    'content':(w//4,0,w,h),
    'content_top':(w//4,0,w,h//2),
    'content_bottom':(w//4,h//2,w,h),
}.items():
    c=im.crop(box).resize((200,120))
    vals=[(r+g+b)/3 for r,g,b in c.getdata()]
    print(name,'mean',round(sum(vals)/len(vals),1),'bright%',round(sum(v>220 for v in vals)/len(vals)*100,1),'dark%',round(sum(v<45 for v in vals)/len(vals)*100,1))
